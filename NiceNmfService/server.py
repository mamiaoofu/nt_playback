from __future__ import annotations

import atexit
import base64
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.parse
import wave
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"
NICE_BASE = Path(r"C:\Program Files (x86)\NICE Systems\NICE Player Release 6")
POWERSHELL_32 = Path(r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe")
SAVE_MGR_WORKER_EXE = TOOLS / "NiceSaveMgrWorker.exe"
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
SUPPORTED_ENGINES = {"powershell", "dotnet"}

# Inject tools path
sys.path.insert(0, str(TOOLS))

from nice_nmf_to_wav import convert_file, read_timeline  # noqa: E402


class SaveMgrWorker:
    def __init__(self, executable: Path):
        self.executable = executable
        self.lock = threading.Lock()
        self.process: subprocess.Popen[str] | None = None

    def close(self) -> None:
        with self.lock:
            self._stop_locked()

    def convert(self, input_nmf: Path, output_wav: Path) -> dict[str, float | str]:
        queue_started = time.perf_counter()
        with self.lock:
            queue_ms = (time.perf_counter() - queue_started) * 1000
            for attempt in range(2):
                try:
                    start_ms = self._start_locked()
                    result = self._send_convert_locked(input_nmf, output_wav)
                    result["queue_ms"] = queue_ms
                    result["start_ms"] = start_ms
                    return result
                except RuntimeError:
                    self._stop_locked()
                    if attempt:
                        raise
        raise RuntimeError("NICE SaveMgr worker failed")

    def _start_locked(self) -> float:
        if self.process is not None and self.process.poll() is None:
            return 0.0
        if not self.executable.exists():
            raise RuntimeError(f"missing .NET SaveMgr worker: {self.executable}")

        started = time.perf_counter()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            [str(self.executable), "--worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=creationflags,
        )
        assert self.process.stdout is not None
        ready = self.process.stdout.readline().strip()
        if ready != "READY":
            self._stop_locked()
            raise RuntimeError("NICE SaveMgr worker did not start correctly")
        return (time.perf_counter() - started) * 1000

    def _send_convert_locked(self, input_nmf: Path, output_wav: Path) -> dict[str, float | str]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("NICE SaveMgr worker is not running")

        line = "CONVERT\t{}\t{}\n".format(encode_worker_text(str(input_nmf)), encode_worker_text(str(output_wav)))
        self.process.stdin.write(line)
        self.process.stdin.flush()
        response = self.process.stdout.readline()
        if not response:
            raise RuntimeError("NICE SaveMgr worker stopped unexpectedly")

        parts = response.rstrip("\r\n").split("\t")
        if len(parts) != 3:
            raise RuntimeError(f"invalid NICE SaveMgr worker response: {response.strip()}")
        status, elapsed_text, payload = parts
        worker_ms = float(elapsed_text)
        message = decode_worker_text(payload)
        if status == "OK":
            return {"worker_ms": worker_ms, "message": message}
        raise RuntimeError(message)

    def _stop_locked(self) -> None:
        if self.process is None:
            return
        process = self.process
        self.process = None
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def encode_worker_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def decode_worker_text(value: str) -> str:
    return base64.b64decode(value.encode("ascii")).decode("utf-8")


# Instantiate the global background worker and register close on exit
SAVE_MGR_WORKER = SaveMgrWorker(SAVE_MGR_WORKER_EXE)
atexit.register(SAVE_MGR_WORKER.close)


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
    if not SAVE_MGR_WORKER_EXE.exists() and not POWERSHELL_32.exists():
        missing.append(str(POWERSHELL_32))
    return {
        "ok": not missing,
        "niceBase": str(NICE_BASE),
        "powershell32": str(POWERSHELL_32),
        "saveMgrWorker": str(SAVE_MGR_WORKER_EXE),
        "saveMgrWorkerReady": SAVE_MGR_WORKER_EXE.exists(),
        "dotnetReady": SAVE_MGR_WORKER_EXE.exists() or (TOOLS / "NiceNmfConverter.exe").exists(),
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
    
    safe_name = Path(source_name or "recording.nmf").name
    with tempfile.TemporaryDirectory(prefix="nice_web_") as temp_dir:
        temp = Path(temp_dir)
        input_nmf = temp / safe_name
        output_wav = temp / (input_nmf.stem + ".wav")
        input_nmf.write_bytes(source)

        timeline = read_timeline(input_nmf, 8000)
        timeline_text = "preserved" if timeline else "payload"
        
        convert_started = time.perf_counter()
        if SAVE_MGR_WORKER_EXE.exists():
            worker_result = SAVE_MGR_WORKER.convert(input_nmf, output_wav)
            convert_ms = float(worker_result["worker_ms"])
            engine_label = "dotnet_save_mgr_worker"
        else:
            convert_file(input_nmf, output_wav, preserve_timeline=True, engine=engine)
            convert_ms = (time.perf_counter() - convert_started) * 1000
            engine_label = "dotnet_save_mgr_fallback"
            
        wav_bytes = output_wav.read_bytes()
        metadata = wav_metadata(wav_bytes, safe_name, len(source), timeline_text)
        metadata["engine"] = engine_label
        metadata["convert_ms"] = f"{convert_ms:.1f}"
        metadata["cache_status"] = "fresh"
        metadata["server_ms"] = f"{(time.perf_counter() - server_started) * 1000:.1f}"

    return wav_bytes, metadata


class NmfApiHandler(BaseHTTPRequestHandler):
    server_version = "NiceNmfApiConverter/1.0"

    def do_GET(self) -> None:
        if self.path == "/":
            body = json.dumps({
                "status": "ok",
                "service": "NICE NMF API Converter",
                "message": "NMF conversion service is running. POST your NMF files to /api/convert"
            }, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/health":
            body = json.dumps(nice_status(), indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Return 404 for other paths
        self.send_error(404, "Not found")

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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10797
    server = ThreadingHTTPServer(("0.0.0.0", port), NmfApiHandler)
    print(f"NICE NMF API Converter running on port {port}...")
    server.serve_forever()


if __name__ == "__main__":
    main()
