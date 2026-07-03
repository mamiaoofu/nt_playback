#!/usr/bin/env python3
"""Convert NICE .nmf files to playable PCM WAV using the installed NICE libraries.

The NICE Player install exposes a .NET converter:
  NiceApplications.Playback.MediaServices.Logic.MediaFileConverter.NmfToVox

That converter can extract/re-encode voice media to PCM_A_LAW. This script then
decodes A-law bytes to standard 16-bit PCM WAV so the output is playable without
the NICE Player. The .NET engine uses the Player SaveMgr/WaveController flow
instead, which matches the NICE Player "Save WAV" output for normal playback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PS_CONVERTER = ROOT / "tools" / "try_nice_nmf_convert.ps1"
PS_PLAYER_SAVE_CONVERTER = ROOT / "tools" / "try_nice_player_wave_convert.ps1"
DOTNET_CONVERTER = ROOT / "tools" / "NiceNmfConverter.exe"
SAVE_MGR_WORKER = ROOT / "tools" / "NiceSaveMgrWorker.exe"
POWERSHELL_32 = Path(r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe")
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


@dataclass(frozen=True)
class ExtractedPcm:
    pcm: bytes
    codec: str
    media_duration_seconds: float | None = None


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


def decode_alaw_byte(value: int) -> int:
    value ^= 0x55
    sample = (value & 0x0F) << 4
    segment = (value & 0x70) >> 4

    if segment == 0:
        sample += 8
    elif segment == 1:
        sample += 0x108
    else:
        sample += 0x108
        sample <<= segment - 1

    return sample if (value & 0x80) else -sample


def alaw_to_pcm16_bytes(data: bytes) -> bytes:
    out = bytearray(len(data) * 2)
    pos = 0
    for byte in data:
        sample = decode_alaw_byte(byte)
        out[pos : pos + 2] = int(sample).to_bytes(2, "little", signed=True)
        pos += 2
    return bytes(out)


def pcm16_peak(data: bytes) -> int:
    peak = 0
    usable = len(data) - (len(data) % 2)
    for offset in range(0, usable, 2):
        sample = int.from_bytes(data[offset : offset + 2], "little", signed=True)
        peak = max(peak, abs(sample))
    return peak


def parse_converter_duration(output: str) -> float | None:
    for line in output.splitlines():
        if "MediaDurationSeconds" not in line:
            continue
        _, _, value = line.partition("=")
        if not value:
            _, _, value = line.partition(":")
        try:
            return float(value.strip())
        except ValueError:
            continue
    return None


def extract_alaw_with_nice(input_nmf: Path, raw_output: Path, engine: str = "powershell") -> float | None:
    engine = engine.strip().lower()
    if engine in {"dotnet", ".net", "net"}:
        if not DOTNET_CONVERTER.exists():
            raise RuntimeError(f"missing .NET helper: {DOTNET_CONVERTER}")
        command = [
            str(DOTNET_CONVERTER),
            str(input_nmf),
            str(raw_output),
            "PCM_A_LAW",
        ]
    elif engine == "powershell":
        if not POWERSHELL_32.exists():
            raise RuntimeError("32-bit Windows PowerShell was not found")
        if not PS_CONVERTER.exists():
            raise RuntimeError(f"missing helper script: {PS_CONVERTER}")
        command = [
            str(POWERSHELL_32),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS_CONVERTER),
            "-InputNmf",
            str(input_nmf),
            "-OutputFile",
            str(raw_output),
            "-Compression",
            "PCM_A_LAW",
        ]
    else:
        raise RuntimeError(f"unsupported NICE converter engine: {engine}")

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    if not raw_output.exists() or raw_output.stat().st_size == 0:
        raise RuntimeError("NICE converter produced an empty audio stream")
    return parse_converter_duration(completed.stdout)


def extract_wav_with_player_save(input_nmf: Path, output_wav: Path) -> None:
    if SAVE_MGR_WORKER.exists():
        command = [str(SAVE_MGR_WORKER), str(input_nmf), str(output_wav)]
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


def extract_pcm_with_nice(input_nmf: Path, temp: Path, engine: str = "powershell") -> ExtractedPcm:
    raw_alaw = temp / (input_nmf.stem + ".alaw")
    media_duration = extract_alaw_with_nice(input_nmf, raw_alaw, engine=engine)
    alaw_pcm = alaw_to_pcm16_bytes(raw_alaw.read_bytes())

    # Do not fallback to NmfToVox(G729) here. That API produced non-repeatable
    # G729 payloads for some NICE files, so it is not reliable enough for the
    # browser player. Files that decode to near-silence through PCM_A_LAW need
    # the Player's Save/WaveController path instead.
    return ExtractedPcm(alaw_pcm, "PCM_A_LAW", media_duration)


def apply_timeline_padding(
    input_nmf: Path,
    pcm: bytes,
    sample_rate: int,
    preserve_timeline: bool,
    media_duration_seconds: float | None = None,
) -> bytes:
    if not preserve_timeline:
        return pcm

    if media_duration_seconds is not None and media_duration_seconds > 0:
        total_frames = round(media_duration_seconds * sample_rate)
        current_frames = len(pcm) // 2
        if current_frames > total_frames:
            return pcm[: total_frames * 2]
        return pcm + (b"\x00\x00" * (total_frames - current_frames))

    timeline = read_timeline(input_nmf, sample_rate)
    if timeline is None:
        return pcm

    current_frames = len(pcm) // 2
    leading = b"\x00\x00" * timeline.leading_frames
    desired_payload_frames = max(0, timeline.total_frames - timeline.leading_frames)

    if current_frames > desired_payload_frames:
        pcm = pcm[: desired_payload_frames * 2]
        current_frames = desired_payload_frames

    trailing_frames = max(0, desired_payload_frames - current_frames)
    trailing = b"\x00\x00" * trailing_frames
    return leading + pcm + trailing


def convert_file(
    input_nmf: Path,
    output_wav: Path,
    sample_rate: int = 8000,
    preserve_timeline: bool = True,
    engine: str = "dotnet",
) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    normalized_engine = engine.strip().lower()
    if normalized_engine in {"dotnet", ".net", "net", "player", "player_save", "save_mgr"}:
        extract_wav_with_player_save(input_nmf, output_wav)
        return

    with tempfile.TemporaryDirectory(prefix="nice_nmf_") as temp:
        extracted = extract_pcm_with_nice(input_nmf, Path(temp), engine=engine)
        pcm = apply_timeline_padding(
            input_nmf,
            extracted.pcm,
            sample_rate,
            preserve_timeline,
            media_duration_seconds=extracted.media_duration_seconds,
        )

    with wave.open(str(output_wav), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


def iter_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.rglob("*.nmf"))
    return [path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert NICE .nmf files to PCM WAV.")
    parser.add_argument("input", type=Path, help="input .nmf file or folder")
    parser.add_argument("output", type=Path, help="output .wav file or folder")
    parser.add_argument("--sample-rate", type=int, default=8000)
    parser.add_argument(
        "--raw-payload",
        action="store_true",
        help="do not add timeline silence from the NMF packet timestamps",
    )
    parser.add_argument(
        "--engine",
        choices=("dotnet",),
        default="dotnet",
        help="NICE DLL bridge to use",
    )
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
        convert_file(
            src,
            dst,
            sample_rate=args.sample_rate,
            preserve_timeline=not args.raw_payload,
            engine=args.engine,
        )


if __name__ == "__main__":
    main()
