from __future__ import annotations

import io
import json
import mimetypes
import sys
import tempfile
import time
import urllib.parse
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
TOOLS = PROJECT_ROOT / "tools"
NICE_BASE = Path(r"C:\Program Files (x86)\NICE Systems\NICE Player Release 6")
POWERSHELL_32 = Path(r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe")
REQUIRED_NICE_FILES = [
    "ERS.Common.dll",
    "NiceApplications.Playback.Utils.dll",
    "NiceApplications.Playback.MediaServices.Logic.dll",
    "NiceApplications.Playback.PlayMgr.dll",
    "NiceApplications.Playback.FileTypes.dll",
    "NiceApplications.Playback.PlayList.Logic.dll",
    "NiceApplications.Playback.Streaming.Common.dll",
    "NiceApplications.Playback.InternalCommon.dll",
    "Nice.Storage.CommonProjects.NMFClasses.dll",
    "G72xCodersDll.dll",
    "ACACVT32.DLL",
]
SUPPORTED_ENGINES = {"dotnet"}

sys.path.insert(0, str(TOOLS))

from nice_nmf_to_wav import convert_file, read_timeline  # noqa: E402


def nice_status() -> dict[str, object]:
    required = [
        {
            "name": name,
            "path": str(NICE_BASE / name),
            "exists": (NICE_BASE / name).exists(),
        }
        for name in REQUIRED_NICE_FILES
    ]
    missing = [item["path"] for item in required if not item["exists"]]
    if not POWERSHELL_32.exists():
        missing.append(str(POWERSHELL_32))
    return {
        "ok": not missing,
        "niceBase": str(NICE_BASE),
        "powershell32": str(POWERSHELL_32),
        "playerSaveBridge": str(TOOLS / "try_nice_player_wave_convert.ps1"),
        "dotnetReady": (TOOLS / "try_nice_player_wave_convert.ps1").exists(),
        "supportedEngines": sorted(SUPPORTED_ENGINES),
        "requiredFiles": required,
        "missing": missing,
    }


def wav_metadata(wav_bytes: bytes, source_name: str, source_size: int, timeline_text: str) -> dict[str, str]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()

    return {
        "source_name": source_name,
        "source_size": str(source_size),
        "sample_rate": str(sample_rate),
        "channels": str(channels),
        "bits": str(sample_width * 8),
        "frames": str(frames),
        "duration": f"{frames / sample_rate:.3f}" if sample_rate else "0",
        "timeline": timeline_text,
    }


def wav_peak(wav_bytes: bytes) -> int:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        return 0

    peak = 0
    usable = len(frames) - (len(frames) % 2)
    for offset in range(0, usable, 2):
        sample = int.from_bytes(frames[offset : offset + 2], "little", signed=True)
        peak = max(peak, abs(sample))
    return peak


def normalize_engine(engine: str) -> str:
    normalized = (engine or "powershell").strip().lower()
    if normalized in {".net", "net"}:
        normalized = "dotnet"
    if normalized not in SUPPORTED_ENGINES:
        raise RuntimeError(f"unsupported converter mode: {engine}")
    return normalized


def convert_nmf(source: bytes, source_name: str, engine: str) -> tuple[bytes, dict[str, str]]:
    engine = normalize_engine(engine)
    server_started = time.perf_counter()
    status = nice_status()
    if not status["ok"]:
        missing = ", ".join(status["missing"]) or str(POWERSHELL_32)
        raise RuntimeError(f"NICE Player runtime is not ready: {missing}")
    if engine == "dotnet" and not status["dotnetReady"]:
        raise RuntimeError(f".NET SaveMgr bridge is not ready: {status['playerSaveBridge']}")

    safe_name = Path(source_name or "recording.nmf").name
    with tempfile.TemporaryDirectory(prefix="nice_web_") as temp_dir:
        temp = Path(temp_dir)
        input_nmf = temp / safe_name
        output_wav = temp / (input_nmf.stem + ".wav")
        input_nmf.write_bytes(source)

        timeline = read_timeline(input_nmf, 8000)
        timeline_text = "preserved" if timeline else "payload"
        convert_started = time.perf_counter()
        convert_file(input_nmf, output_wav, preserve_timeline=True, engine=engine)
        convert_ms = (time.perf_counter() - convert_started) * 1000

        wav_bytes = output_wav.read_bytes()
        peak = wav_peak(wav_bytes)
        if peak <= 16:
            raise RuntimeError(
                "NICE Player SaveMgr produced a near-silent WAV. "
                "The file may be invalid or unsupported by the installed NICE runtime."
            )
        metadata = wav_metadata(wav_bytes, safe_name, len(source), timeline_text)
        metadata["peak"] = str(peak)
        metadata["engine"] = "dotnet_save_mgr" if engine == "dotnet" else engine
        metadata["convert_ms"] = f"{convert_ms:.1f}"
        metadata["cache_status"] = "fresh"
        metadata["server_ms"] = f"{(time.perf_counter() - server_started) * 1000:.1f}"

    return wav_bytes, metadata


class NmfPlayerHandler(SimpleHTTPRequestHandler):
    server_version = "NiceNmfBrowserPlayer/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/index.html"
        if self.path == "/api/health":
            body = json.dumps(nice_status()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/convert":
            self.send_error(404, "Not found")
            return

        try:
            query = urllib.parse.parse_qs(parsed.query)
            source_name = query.get("name", ["recording.nmf"])[0]
            engine = query.get("engine", ["dotnet"])[0]
            length = int(self.headers.get("Content-Length", "0"))
            source = self.rfile.read(length)
            if not source:
                raise RuntimeError("empty upload")
            if not source_name.lower().endswith(".nmf"):
                raise RuntimeError("only .nmf files are supported")
            wav, metadata = convert_nmf(source, source_name, engine)
        except Exception as exc:
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.send_header("Cache-Control", "no-store")
        for key, value in metadata.items():
            self.send_header("X-NMF-" + key.replace("_", "-"), value)
        self.end_headers()
        self.wfile.write(wav)


def main() -> None:
    mimetypes.add_type("text/javascript", ".js")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7797
    server = ThreadingHTTPServer(("127.0.0.1", port), NmfPlayerHandler)
    print(f"NICE NMF browser player: http://127.0.0.1:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
