import subprocess
import os
import json
import logging
import tempfile
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class AudioTranscoder:
    """
    Utility class for detecting audio codecs and transcoding legacy telephony formats
    to browser-compatible PCM WAV.
    """

    @staticmethod
    def get_audio_info(file_path: str) -> dict:
        """
        Get audio information using ffprobe.
        """
        try:
            cmd = [
                'ffprobe', 
                '-v', 'quiet', 
                '-print_format', 'json', 
                '-show_streams', 
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"ffprobe failed for {file_path}: {e}")
            return {}

    @staticmethod
    def is_browser_compatible(file_path: str) -> bool:
        """
        Check if the file is browser-compatible based on codec.
        Standard compatible codecs: pcm_s16le (WAV), mp3, opus, aac, flac, vorbis.
        Incompatible telephony codecs: g711 (pcm_alaw, pcm_mulaw), g729, etc.
        """
        info = AudioTranscoder.get_audio_info(file_path)
        streams = info.get('streams', [])
        if not streams:
            return False
        
        codec_name = streams[0].get('codec_name', '').lower()
        # Common browser supported codecs
        compatible_codecs = ['mp3', 'aac', 'opus', 'flac', 'vorbis', 'pcm_s16le']
        
        return codec_name in compatible_codecs

    @staticmethod
    def transcode_to_wav(source_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Transcodes any audio file to a temporary PCM WAV file.
        Supports .nmf via NICE Player DLL conversion flow.
        Returns (temp_file_path, error_message).
        """
        try:
            # Check if file has .nmf extension
            if source_path.lower().endswith('.nmf'):
                fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='transcoded_nmf_')
                os.close(fd)

                if os.name == 'nt':
                    # Windows Host: run conversion locally via subprocess
                    from pathlib import Path
                    from .tools.nice_nmf_to_wav import convert_file

                    try:
                        logger.info(f"Windows host detected. Converting NMF locally using dotnet engine: {source_path} -> {temp_path}")
                        convert_file(
                            input_nmf=Path(source_path),
                            output_wav=Path(temp_path),
                            sample_rate=8000,
                            preserve_timeline=True,
                            engine="dotnet"
                        )
                    except Exception as e_dotnet:
                        logger.warning(f"Local dotnet NMF conversion failed: {e_dotnet}. Trying powershell fallback...")
                        convert_file(
                            input_nmf=Path(source_path),
                            output_wav=Path(temp_path),
                            sample_rate=8000,
                            preserve_timeline=True,
                            engine="powershell"
                        )
                    return temp_path, None
                else:
                    # Non-Windows (Docker Linux): call host HTTP API
                    import requests
                    
                    converter_url = "http://host.docker.internal:10797/api/convert"
                    file_name = os.path.basename(source_path)
                    
                    logger.info(f"Linux/Docker environment detected. Requesting NMF conversion from host API: {converter_url}")
                    try:
                        # Read NMF bytes
                        with open(source_path, 'rb') as f:
                            nmf_bytes = f.read()
                            
                        # Post to host converter
                        params = {
                            'name': file_name,
                            'engine': 'dotnet'
                        }
                        headers = {
                            'Content-Type': 'application/octet-stream'
                        }
                        
                        response = requests.post(
                            converter_url,
                            params=params,
                            headers=headers,
                            data=nmf_bytes,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            with open(temp_path, 'wb') as out_f:
                                out_f.write(response.content)
                            logger.info(f"NMF conversion via host HTTP API succeeded: {temp_path}")
                            return temp_path, None
                        else:
                            try:
                                err_json = response.json()
                                err_msg = err_json.get('error', response.text)
                            except Exception:
                                err_msg = response.text
                            
                            raise RuntimeError(f"Host NMF converter API returned status {response.status_code}: {err_msg}")
                            
                    except requests.exceptions.ConnectionError:
                        raise RuntimeError(
                            f"Could not connect to host NMF converter at {converter_url}. "
                            "Please ensure 'Nice/start_nmf_player.bat' is running on the Windows host."
                        )
                    except Exception as e:
                        raise RuntimeError(f"NMF HTTP conversion failed: {str(e)}")

            # Create a temporary file that persists after closing
            fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='transcoded_')
            os.close(fd) # Close the file descriptor, we'll use the path

            # FFmpeg command:
            # -i source: input file
            # -acodec pcm_s16le: output as standard 16-bit PCM (WAV)
            # -ar 8000: set sample rate to 8kHz (standard for telephony) or keep original? 
            # Browser handles 8kHz fine.
            # -y: overwrite output
            cmd = [
                'ffmpeg', 
                '-i', source_path,
                '-acodec', 'pcm_s16le',
                '-y',
                temp_path
            ]
            
            # If standard transcode fails, try forcing format for raw-ish WAVs
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Initial transcoding failed, trying fallback: {e.stderr}")
                # Fallback: maybe it's raw mulaw/alaw without proper header
                # We'll try to let ffmpeg guess or try specific telephony settings
                cmd_fallback = [
                    'ffmpeg',
                    '-i', source_path,
                    '-ar', '8000',
                    '-ac', '1',
                    '-acodec', 'pcm_s16le',
                    '-y',
                    temp_path
                ]
                subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)

            return temp_path, None
        except Exception as e:
            error_msg = f"Transcoding failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def cleanup(file_path: str):
        """
        Safely remove a temporary file.
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Cleanup failed for {file_path}: {e}")
