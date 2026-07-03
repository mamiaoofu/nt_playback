#!/usr/bin/env python3
"""Convert NICE .nmf files to playable PCM WAV using the installed NICE libraries.

This uses the Player's SaveMgr/WaveController flow (.NET C# executable wrapper)
which matches the NICE Player "Save WAV" output for normal playback.
It prioritizes using NiceSaveMgrWorker.exe for fast C# conversion.
"""

from __future__ import annotations

import argparse
import datetime as dt
import struct
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAVE_MGR_WORKER = ROOT / "tools" / "NiceSaveMgrWorker.exe"
DOTNET_CONVERTER = ROOT / "tools" / "NiceNmfConverter.exe"
POWERSHELL_32 = Path(r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe")
PS_PLAYER_SAVE_CONVERTER = ROOT / "tools" / "try_nice_player_wave_convert.ps1"
OLE_DATE_BASE = dt.datetime(1899, 12, 30)


@dataclass(frozen=True)
class PacketHeader:
    offset: int
    packet_type: int
    packet_subtype: int
    stream_id: int
    start: dt.datetime
    end: dt.datetime
    packet_size: int
    parameters_size: int


@dataclass(frozen=True)
class Timeline:
    leading_frames: int
    total_frames: int


def read_ole_datetime(data: bytes, offset: int) -> dt.datetime | None:
    value = struct.unpack_from("<d", data, offset)[0]
    if not 20000 < value < 80000:
        return None
    return OLE_DATE_BASE + dt.timedelta(days=value)


def scan_packet_headers(data: bytes) -> list[PacketHeader]:
    headers: list[PacketHeader] = []
    for offset in range(0, max(0, len(data) - 28)):
        start = read_ole_datetime(data, offset + 4)
        end = read_ole_datetime(data, offset + 12)
        if start is None or end is None:
            continue

        duration = (end - start).total_seconds()
        packet_type = data[offset]
        packet_subtype = struct.unpack_from("<h", data, offset + 1)[0]
        stream_id = data[offset + 3]
        packet_size = struct.unpack_from("<I", data, offset + 20)[0]
        parameters_size = struct.unpack_from("<I", data, offset + 24)[0]

        if (
            0 <= duration <= 120
            and 1 <= packet_type <= 10
            and -10 <= packet_subtype <= 100
            and stream_id < 32
            and packet_size < len(data)
            and parameters_size < 10000
        ):
            headers.append(
                PacketHeader(
                    offset=offset,
                    packet_type=packet_type,
                    packet_subtype=packet_subtype,
                    stream_id=stream_id,
                    start=start,
                    end=end,
                    packet_size=packet_size,
                    parameters_size=parameters_size,
                )
            )
    return headers


def read_timeline(input_nmf: Path, sample_rate: int) -> Timeline | None:
    data = input_nmf.read_bytes()
    headers = scan_packet_headers(data)
    item_headers = [h for h in headers if h.packet_type == 1]
    voice_data = [h for h in headers if h.packet_type == 4 and h.packet_subtype == 0]
    if not item_headers or not voice_data:
        return None

    item_start = min(h.start for h in item_headers)
    target_end = max(h.end for h in voice_data)

    next_packet_starts = [h.start for h in voice_data if h.start >= item_start]
    payload_start = min(next_packet_starts) if next_packet_starts else item_start

    leading_seconds = max(0.0, (payload_start - item_start).total_seconds())
    total_seconds = max(0.0, (target_end - item_start).total_seconds())
    return Timeline(
        leading_frames=round(leading_seconds * sample_rate),
        total_frames=round(total_seconds * sample_rate),
    )


def normalize_wav_file(wav_path: Path) -> None:
    """Normalize the WAV file in-place to increase volume without clipping."""
    try:
        with wave.open(str(wav_path), "rb") as wav:
            params = wav.getparams()
            frames = wav.readframes(params.nframes)
            
        if params.sampwidth != 2:
            return  # Only support 16-bit PCM for simple normalization
            
        # Unpack samples
        n_samples = params.nframes * params.nchannels
        samples = list(struct.unpack(f"<{n_samples}h", frames))
        
        if not samples:
            return

        # Find peak
        max_val = max(abs(s) for s in samples)
        
        # Calculate normalization factor (target peak is 28000, ~85% of full scale)
        target_peak = 28000
        if max_val > 100 and max_val < target_peak:
            factor = target_peak / max_val
            # Limit the boost to 6.0x to avoid excessive background hiss
            if factor > 6.0:
                factor = 6.0
                
            # Apply factor
            scaled_samples = []
            for s in samples:
                scaled = int(s * factor)
                if scaled > 32767:
                    scaled = 32767
                elif scaled < -32768:
                    scaled = -32768
                scaled_samples.append(scaled)
                
            # Repack and write back
            packed = struct.pack(f"<{n_samples}h", *scaled_samples)
            with wave.open(str(wav_path), "wb") as wav:
                wav.setparams(params)
                wav.writeframes(packed)
    except Exception as e:
        print(f"Warning: Failed to normalize WAV file: {e}")


def extract_wav_with_player_save(input_nmf: Path, output_wav: Path) -> None:
    if SAVE_MGR_WORKER.exists():
        command = [str(SAVE_MGR_WORKER), str(input_nmf), str(output_wav)]
    elif DOTNET_CONVERTER.exists():
        command = [str(DOTNET_CONVERTER), str(input_nmf), str(output_wav), "PLAYER_WAV"]
    else:
        if not POWERSHELL_32.exists():
            raise RuntimeError("32-bit Windows PowerShell was not found")
        if not PS_PLAYER_SAVE_CONVERTER.exists():
            raise RuntimeError(f"missing helper script: {PS_PLAYER_SAVE_CONVERTER}")

        command = [
            str(POWERSHELL_32),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS_PLAYER_SAVE_CONVERTER),
            "-InputNmf",
            str(input_nmf),
            "-OutputFile",
            str(output_wav),
        ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    if not output_wav.exists() or output_wav.stat().st_size == 0:
        raise RuntimeError("NICE Player SaveMgr produced an empty WAV")


def convert_file(
    input_nmf: Path,
    output_wav: Path,
    sample_rate: int = 8000,
    preserve_timeline: bool = True,
    engine: str = "dotnet",
) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    
    extract_wav_with_player_save(input_nmf, output_wav)

    # Apply volume normalization in-place
    normalize_wav_file(output_wav)


def iter_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.rglob("*.nmf"))
    return [path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert NICE .nmf files to PCM WAV.")
    parser.add_argument("input", type=Path, help="input .nmf file or folder")
    parser.add_argument("output", type=Path, help="output .wav file or folder")
    args = parser.parse_args()

    inputs = iter_inputs(args.input)
    if not inputs:
        raise SystemExit("no .nmf files found")

    if len(inputs) == 1 and not args.output.exists() and args.output.suffix.lower() == ".wav":
        pairs = [(inputs[0], args.output)]
    elif len(inputs) == 1 and args.output.suffix.lower() == ".wav":
        pairs = [(inputs[0], args.output)]
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        root = args.input if args.input.is_dir() else args.input.parent
        pairs = [
            (src, args.output / src.relative_to(root).with_suffix(".wav"))
            for src in inputs
        ]

    for index, (src, dst) in enumerate(pairs, start=1):
        print(f"[{index}/{len(pairs)}] {src.name} -> {dst}")
        convert_file(src, dst)


if __name__ == "__main__":
    main()
