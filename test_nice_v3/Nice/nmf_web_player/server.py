from __future__ import annotations

import atexit
import base64
import io
import json
import mimetypes
import subprocess
import sys
import tempfile
import threading
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
SUPPORTED_ENGINES = {"dotnet"}

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
            queue_ms = elapsed_ms(queue_started)
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
        return elapsed_ms(started)

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


SAVE_MGR_WORKER = SaveMgrWorker(SAVE_MGR_WORKER_EXE)
atexit.register(SAVE_MGR_WORKER.close)


def elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def add_timing(timings: list[dict[str, str]], key: str, label: str, started: float) -> None:
    timings.append(
        {
            "key": key,
            "label": label,
            "ms": f"{elapsed_ms(started):.1f}",
        }
    )


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
        "playerSaveBridge": str(TOOLS / "try_nice_player_wave_convert.ps1"),
        "dotnetReady": SAVE_MGR_WORKER_EXE.exists() or (TOOLS / "try_nice_player_wave_convert.ps1").exists(),
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


def wav_peak(wav_bytes: bytes, max_samples: int | None = None) -> int:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        return 0

    peak = 0
    usable = len(frames) - (len(frames) % 2)
    total_samples = usable // 2
    if max_samples is None or total_samples <= max_samples:
        step_bytes = 2
    else:
        step_bytes = max(1, total_samples // max_samples) * 2
    for offset in range(0, usable, step_bytes):
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


def convert_nmf(source: bytes, source_name: str, engine: str, debug: bool = False) -> tuple[bytes, dict[str, str]]:
    engine = normalize_engine(engine)
    server_started = time.perf_counter()
    timings: list[dict[str, str]] = []

    step_started = time.perf_counter()
    status = nice_status()
    add_timing(timings, "runtime_check", "Check NICE runtime", step_started)
    if not status["ok"]:
        missing = ", ".join(status["missing"]) or str(POWERSHELL_32)
        raise RuntimeError(f"NICE Player runtime is not ready: {missing}")
    if engine == "dotnet" and not status["dotnetReady"]:
        raise RuntimeError(f".NET SaveMgr bridge is not ready: {status['playerSaveBridge']}")

    safe_name = Path(source_name or "recording.nmf").name
    step_started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="nice_web_") as temp_dir:
        add_timing(timings, "temp_folder", "Create temp folder", step_started)
        temp = Path(temp_dir)
        input_nmf = temp / safe_name
        output_wav = temp / (input_nmf.stem + ".wav")

        step_started = time.perf_counter()
        input_nmf.write_bytes(source)
        add_timing(timings, "write_nmf", "Write uploaded NMF to temp", step_started)

        timeline_text = "skipped"
        if debug:
            step_started = time.perf_counter()
            timeline = read_timeline(input_nmf, 8000)
            add_timing(timings, "scan_timeline", "Scan NMF timeline packets", step_started)
            timeline_text = "preserved" if timeline else "payload"

        if SAVE_MGR_WORKER_EXE.exists():
            worker_result = SAVE_MGR_WORKER.convert(input_nmf, output_wav)
            timings.append(
                {
                    "key": "queue_wait",
                    "label": "Wait for NICE converter queue",
                    "ms": f"{float(worker_result['queue_ms']):.1f}",
                }
            )
            if float(worker_result["start_ms"]) > 0:
                timings.append(
                    {
                        "key": "worker_start",
                        "label": "Start x86 .NET SaveMgr worker",
                        "ms": f"{float(worker_result['start_ms']):.1f}",
                    }
                )
            convert_ms = float(worker_result["worker_ms"])
            converter_label = ".NET SaveMgr worker conversion"
            engine_label = "dotnet_save_mgr_worker"
        else:
            convert_started = time.perf_counter()
            convert_file(input_nmf, output_wav, preserve_timeline=True, engine=engine)
            convert_ms = elapsed_ms(convert_started)
            converter_label = ".NET SaveMgr PowerShell fallback"
            engine_label = "dotnet_save_mgr_powershell"
        timings.append(
            {
                "key": "savemgr_convert",
                "label": converter_label,
                "ms": f"{convert_ms:.1f}",
            }
        )

        step_started = time.perf_counter()
        wav_bytes = output_wav.read_bytes()
        add_timing(timings, "read_wav", "Read generated WAV", step_started)

        step_started = time.perf_counter()
        peak = wav_peak(wav_bytes, max_samples=None if debug else 12000)
        add_timing(timings, "peak_scan", "Scan WAV peak" if debug else "Sample WAV peak", step_started)
        if peak <= 16 and not debug:
            step_started = time.perf_counter()
            peak = wav_peak(wav_bytes)
            add_timing(timings, "peak_full_fallback", "Full WAV peak fallback", step_started)
        if peak <= 16:
            raise RuntimeError(
                "NICE Player SaveMgr produced a near-silent WAV. "
                "The file may be invalid or unsupported by the installed NICE runtime."
            )

        step_started = time.perf_counter()
        metadata = wav_metadata(wav_bytes, safe_name, len(source), timeline_text)
        add_timing(timings, "wav_metadata", "Read WAV metadata", step_started)
        metadata["peak"] = str(peak)
        metadata["engine"] = engine_label
        metadata["convert_ms"] = f"{convert_ms:.1f}"
        metadata["cache_status"] = "fresh"
        metadata["server_ms"] = f"{(time.perf_counter() - server_started) * 1000:.1f}"
        timings.append(
            {
                "key": "server_total",
                "label": "Server convert_nmf total",
                "ms": metadata["server_ms"],
            }
        )
        metadata["debug_timings"] = json.dumps(timings, separators=(",", ":"))

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
            debug = query.get("debug", ["0"])[0].strip().lower() in {"1", "true", "yes", "on"}
            length = int(self.headers.get("Content-Length", "0"))
            read_started = time.perf_counter()
            source = self.rfile.read(length)
            request_read_ms = elapsed_ms(read_started)
            if not source:
                raise RuntimeError("empty upload")
            if not source_name.lower().endswith(".nmf"):
                raise RuntimeError("only .nmf files are supported")
            wav, metadata = convert_nmf(source, source_name, engine, debug=debug)
            timings = json.loads(metadata.get("debug_timings", "[]"))
            timings.insert(
                0,
                {
                    "key": "request_read",
                    "label": "Read upload body",
                    "ms": f"{request_read_ms:.1f}",
                },
            )
            metadata["debug_timings"] = json.dumps(timings, separators=(",", ":"))
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6797
    server = ThreadingHTTPServer(("127.0.0.1", port), NmfPlayerHandler)
    print(f"NICE NMF browser player: http://127.0.0.1:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
