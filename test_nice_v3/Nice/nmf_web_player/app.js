const fileInput = document.querySelector("#fileInput");
const folderInput = document.querySelector("#folderInput");
const chooseFiles = document.querySelector("#chooseFiles");
const chooseFolder = document.querySelector("#chooseFolder");
const dropZone = document.querySelector("#dropZone");
const filterInput = document.querySelector("#filterInput");
const trackList = document.querySelector("#trackList");
const fileCount = document.querySelector("#fileCount");
const serverStatus = document.querySelector("#serverStatus");
const runtimeText = document.querySelector("#runtimeText");
const runtimePath = document.querySelector("#runtimePath");
const runtimeFiles = document.querySelector("#runtimeFiles");
const converterModeInputs = Array.from(document.querySelectorAll('input[name="converterMode"]'));
const trackName = document.querySelector("#trackName");
const trackMeta = document.querySelector("#trackMeta");
const audio = document.querySelector("#audio");
const canvas = document.querySelector("#waveCanvas");
const waveShell = document.querySelector("#waveShell");
const seek = document.querySelector("#seek");
const currentTime = document.querySelector("#currentTime");
const durationText = document.querySelector("#duration");
const playBtn = document.querySelector("#playBtn");
const prevBtn = document.querySelector("#prevBtn");
const nextBtn = document.querySelector("#nextBtn");
const stopBtn = document.querySelector("#stopBtn");
const downloadBtn = document.querySelector("#downloadBtn");
const rateValue = document.querySelector("#rateValue");
const channelsValue = document.querySelector("#channelsValue");
const durationValue = document.querySelector("#durationValue");
const convertTimeValue = document.querySelector("#convertTimeValue");
const serverTimeValue = document.querySelector("#serverTimeValue");
const engineValue = document.querySelector("#engineValue");
const timelineValue = document.querySelector("#timelineValue");
const processTitle = document.querySelector("#processTitle");
const processDetail = document.querySelector("#processDetail");
const processBar = document.querySelector("#processBar");
const timingSummary = document.querySelector("#timingSummary");
const timingEngine = document.querySelector("#timingEngine");
const timingConvert = document.querySelector("#timingConvert");
const timingServer = document.querySelector("#timingServer");
const timingBrowser = document.querySelector("#timingBrowser");
const timingDetailToggle = document.querySelector("#timingDetailToggle");
const timingModal = document.querySelector("#timingModal");
const timingModalClose = document.querySelector("#timingModalClose");
const timingDetailTotal = document.querySelector("#timingDetailTotal");
const timingDetailList = document.querySelector("#timingDetailList");
const pageParams = new URLSearchParams(window.location.search);
const timelineDebugEnabled = ["1", "true", "yes", "on"].includes(
  (pageParams.get("debug") || "").trim().toLowerCase(),
);

let tracks = [];
let activeIndex = -1;
let objectUrl = "";
let currentBlob = null;
let converting = false;
let currentPeaks = null;
let progressRafId = 0;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${rest}`;
}

function formatMs(milliseconds) {
  const value = Number(milliseconds);
  if (!Number.isFinite(value) || value < 0) return "-";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(2)} sec`;
}

function formatConvertMeta(meta) {
  if (!meta) return "-";
  const elapsed = formatMs(meta.convertMs);
  return meta.cacheStatus === "hit" ? `cache (${elapsed})` : elapsed;
}

function addBrowserTiming(timings, key, label, started) {
  timings.push({
    source: "browser",
    key,
    label,
    ms: performance.now() - started,
  });
}

function normalizeTimingRows(rows = [], source = "server") {
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) => ({
      source: row.source || source,
      key: row.key || "",
      label: row.label || row.key || "step",
      ms: Number(row.ms),
    }))
    .filter((row) => Number.isFinite(row.ms));
}

function parseTimingHeader(value) {
  if (!value) return [];
  try {
    return normalizeTimingRows(JSON.parse(value), "server");
  } catch {
    return [];
  }
}

function formatTimingLabel(row) {
  const prefix = row.source === "browser" ? "Browser" : "Server";
  return `${prefix}: ${row.label}`;
}

function renderTimingDetail(meta = null) {
  const rows = [
    ...normalizeTimingRows(meta?.serverTimings || [], "server"),
    ...normalizeTimingRows(meta?.browserTimings || [], "browser"),
  ];
  timingDetailToggle.hidden = !meta || rows.length === 0;
  timingDetailTotal.textContent = meta ? `Total ${formatMs(meta.browserMs)}` : "-";
  timingDetailList.replaceChildren();

  if (!meta || rows.length === 0) {
    timingModal.hidden = true;
    return;
  }

  const maxMs = Math.max(...rows.map((row) => row.ms), 1);
  for (const row of rows) {
    const item = document.createElement("div");
    item.className = `timing-detail-item ${row.source}`;

    const label = document.createElement("span");
    label.className = "timing-detail-label";
    label.textContent = formatTimingLabel(row);

    const bar = document.createElement("span");
    bar.className = "timing-detail-bar";
    const fill = document.createElement("span");
    fill.style.width = `${Math.max(2, (row.ms / maxMs) * 100)}%`;
    bar.append(fill);

    const value = document.createElement("strong");
    value.textContent = formatMs(row.ms);

    item.append(label, bar, value);
    timingDetailList.append(item);
  }
}

function getConverterMode() {
  return converterModeInputs.find((input) => input.checked)?.value || "dotnet";
}

function formatEngine(engine) {
  if (engine === "dotnet_save_mgr_worker") return ".NET SaveMgr Worker";
  if (engine === "dotnet_save_mgr_powershell") return ".NET SaveMgr PS";
  return engine === "dotnet" || engine === "dotnet_save_mgr" ? ".NET SaveMgr" : "PowerShell";
}

function setStatus(text, state = "") {
  serverStatus.textContent = text;
  serverStatus.className = `status-pill ${state}`.trim();
}

function setProcess(title, detail, percent = 0, busy = false) {
  processTitle.textContent = title;
  processDetail.textContent = detail;
  processBar.classList.toggle("indeterminate", busy);
  if (!busy) {
    processBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  }
}

function setTimingSummary(meta = null) {
  timingSummary.hidden = !meta;
  if (!meta) {
    timingEngine.textContent = "-";
    timingConvert.textContent = "-";
    timingServer.textContent = "-";
    timingBrowser.textContent = "-";
    return;
  }
  timingEngine.textContent = formatEngine(meta.engine);
  timingConvert.textContent = formatConvertMeta(meta);
  timingServer.textContent = formatMs(meta.serverMs);
  timingBrowser.textContent = formatMs(meta.browserMs);
}

function renderRuntimeFiles(files = []) {
  runtimeFiles.replaceChildren();
  for (const file of files) {
    const item = document.createElement("li");
    item.className = file.exists ? "" : "missing";
    item.textContent = file.exists ? file.name : `ไม่พบ ${file.name}`;
    item.title = file.path || file.name;
    runtimeFiles.append(item);
  }
}

function setControlsEnabled(enabled) {
  playBtn.disabled = !enabled;
  prevBtn.disabled = !enabled;
  nextBtn.disabled = !enabled;
  stopBtn.disabled = !enabled;
}

function clearPlaybackSurface() {
  audio.pause();
  audio.removeAttribute("src");
  audio.load();
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = "";
  currentBlob = null;
  currentTime.textContent = "0:00";
  durationText.textContent = "0:00";
  seek.value = "0";
  downloadBtn.disabled = true;
  currentPeaks = null;
  drawEmptyWave();
}

function clearConvertedTracks() {
  for (const track of tracks) {
    track.blob = null;
    track.meta = null;
    if (track.status === "ready") track.status = "queued";
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const data = await response.json();
    if (data.ok) {
      setStatus("ready");
      runtimeText.textContent = "พร้อมใช้งาน";
    } else {
      setStatus("missing", "error");
      runtimeText.textContent = "ยังไม่พร้อม";
    }
    runtimePath.textContent = data.saveMgrWorkerReady
      ? data.saveMgrWorker
      : data.niceBase || "NICE Player runtime not found";
    renderRuntimeFiles(data.requiredFiles || []);
  } catch (error) {
    setStatus("offline", "error");
    runtimeText.textContent = "server offline";
    runtimePath.textContent = error.message;
    renderRuntimeFiles([]);
  }
}

function ingestFiles(fileList) {
  const incoming = Array.from(fileList)
    .filter((file) => file.name.toLowerCase().endsWith(".nmf"))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

  tracks = incoming.map((file, index) => ({
    id: `${file.name}-${file.size}-${file.lastModified}-${index}`,
    file,
    status: "queued",
    meta: null,
    blob: null,
    error: "",
  }));
  activeIndex = -1;
  resetPlayer();
  renderTracks();
  setStatus(tracks.length ? "ready" : "empty");
  setProcess(
    tracks.length ? `นำเข้าแล้ว ${tracks.length} ไฟล์` : "ยังไม่มีไฟล์ .nmf",
    tracks.length ? "คลิกชื่อไฟล์ในรายการเพื่อเริ่มแปลงเป็น WAV และเล่นเสียง" : "เลือกไฟล์หรือโฟลเดอร์ .nmf",
    tracks.length ? 10 : 0,
  );
}

function resetPlayer() {
  clearPlaybackSurface();
  clearConvertedTracks();
  trackName.textContent = "เลือกไฟล์ .nmf เพื่อเริ่มทดสอบ";
  trackMeta.textContent = "ยังไม่ได้เลือกไฟล์";
  rateValue.textContent = "-";
  channelsValue.textContent = "-";
  durationValue.textContent = "-";
  convertTimeValue.textContent = "-";
  serverTimeValue.textContent = "-";
  engineValue.textContent = "-";
  timelineValue.textContent = "-";
  setTimingSummary(null);
  renderTimingDetail(null);
  setProcess("พร้อมรับไฟล์ .nmf", "นำเข้าไฟล์แล้วคลิกชื่อไฟล์เพื่อแปลงและเล่น", 0);
}

function renderTracks() {
  const query = filterInput.value.trim().toLowerCase();
  const visible = tracks
    .map((track, index) => ({ track, index }))
    .filter(({ track }) => track.file.name.toLowerCase().includes(query));

  fileCount.textContent = `${visible.length} files`;
  trackList.replaceChildren();

  for (const { track, index } of visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `track ${index === activeIndex ? "active" : ""}`;
    button.setAttribute("role", "listitem");
    button.addEventListener("click", () => playTrack(index));

    const text = document.createElement("div");
    const name = document.createElement("div");
    name.className = "track-name";
    name.textContent = track.file.name;
    const sub = document.createElement("div");
    sub.className = "track-sub";
    sub.textContent = formatBytes(track.file.size);
    text.append(name, sub);

    const badge = document.createElement("span");
    badge.className = `badge ${track.status === "ready" ? "ready" : ""} ${
      track.status === "error" ? "error" : ""
    }`;
    badge.textContent =
      track.status === "ready"
        ? "WAV"
        : track.status === "loading"
          ? "..."
          : track.status === "error"
            ? "ERR"
            : "NMF";

    button.append(text, badge);
    trackList.append(button);
  }
}

async function convertTrack(track) {
  const browserStarted = performance.now();
  const browserTimings = [];
  converting = true;
  setControlsEnabled(false);
  track.status = "loading";
    renderTracks();
    setStatus("converting", "busy");
  setTimingSummary(null);
  renderTimingDetail(null);
  setProcess("กำลังอ่านไฟล์", track.file.name, 20);

  try {
    const engine = getConverterMode();
    let stepStarted = performance.now();
    const body = await track.file.arrayBuffer();
    addBrowserTiming(browserTimings, "read_input_file", "Read selected NMF file", stepStarted);
    setProcess("กำลังส่งเข้า server", `${formatBytes(track.file.size)} -> NICE converter`, 35);

    const pendingTimer = window.setTimeout(() => {
      setProcess("กำลังแปลงด้วย NICE runtime", "ขั้นตอนนี้ใช้ DLL จาก NICE Player บนเครื่อง server", 55, true);
    }, 250);

    let response;
    try {
      stepStarted = performance.now();
      const convertParams = new URLSearchParams({
        name: track.file.name,
        engine,
      });
      if (timelineDebugEnabled) {
        convertParams.set("debug", "1");
      }
      response = await fetch(`/api/convert?${convertParams.toString()}`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body,
      });
      addBrowserTiming(browserTimings, "fetch_wait_headers", "Upload and wait for response headers", stepStarted);
    } finally {
      window.clearTimeout(pendingTimer);
    }

    if (!response.ok) {
      let message = "convert failed";
      try {
        const data = await response.json();
        message = data.error || message;
      } catch {
        message = await response.text();
      }
      throw new Error(message);
    }

    setProcess("กำลังเตรียม WAV", "รับผลลัพธ์จาก server แล้วสร้าง audio สำหรับ browser", 82);
    const serverTimings = parseTimingHeader(
      response.headers.get("X-NMF-debug-timings") || response.headers.get("x-nmf-debug-timings") || "",
    );
    stepStarted = performance.now();
    track.blob = await response.blob();
    addBrowserTiming(browserTimings, "read_wav_blob", "Read WAV response blob", stepStarted);
    const browserMs = performance.now() - browserStarted;
    const convertMs = Number(response.headers.get("X-NMF-convert-ms") || response.headers.get("x-nmf-convert-ms") || "");
    const serverMs = Number(response.headers.get("X-NMF-server-ms") || response.headers.get("x-nmf-server-ms") || "");
    track.meta = {
      sampleRate: response.headers.get("X-NMF-sample-rate") || "",
      channels: response.headers.get("X-NMF-channels") || "",
      bits: response.headers.get("X-NMF-bits") || "",
      duration: Number(response.headers.get("X-NMF-duration") || "0"),
      timeline: response.headers.get("X-NMF-timeline") || "",
      convertMs: Number.isFinite(convertMs) ? convertMs : browserMs,
      serverMs: Number.isFinite(serverMs) ? serverMs : browserMs,
      browserMs,
      cacheStatus: response.headers.get("X-NMF-cache-status") || response.headers.get("x-nmf-cache-status") || "fresh",
      engine: response.headers.get("X-NMF-engine") || response.headers.get("x-nmf-engine") || engine,
      serverTimings,
      browserTimings,
    };
    track.status = "ready";
    setStatus("ready");
    const timingDetail =
      `${formatEngine(track.meta.engine)} ${formatMs(track.meta.convertMs)} | server ${formatMs(track.meta.serverMs)} | browser ${formatMs(track.meta.browserMs)}`;
    setProcess(
      "แปลงสำเร็จ",
      timingDetail,
      100,
    );
    setTimingSummary(track.meta);
    renderTimingDetail(track.meta);
    renderTracks();
    return track;
  } finally {
    converting = false;
    setControlsEnabled(true);
  }
}

async function playTrack(index) {
  if (converting || index < 0 || index >= tracks.length) return;
  activeIndex = index;
  const track = tracks[index];
  clearPlaybackSurface();
  clearConvertedTracks();
  trackName.textContent = track.file.name;
  trackMeta.textContent = `${formatBytes(track.file.size)} -> รอแปลงเป็น WAV`;
  rateValue.textContent = "-";
  channelsValue.textContent = "-";
  durationValue.textContent = "-";
  convertTimeValue.textContent = "-";
  serverTimeValue.textContent = "-";
  engineValue.textContent = "-";
  timelineValue.textContent = "-";
  setTimingSummary(null);
  renderTimingDetail(null);
  renderTracks();

  try {
    await convertTrack(track);
  } catch (error) {
    track.status = "error";
    track.error = error.message;
    setStatus("error", "error");
    setProcess("แปลงไม่สำเร็จ", error.message, 100);
    trackMeta.textContent = error.message;
    renderTracks();
    return;
  }

  if (objectUrl) URL.revokeObjectURL(objectUrl);
  currentBlob = track.blob;
  objectUrl = URL.createObjectURL(track.blob);
  audio.src = objectUrl;

  trackName.textContent = track.file.name;
  trackMeta.textContent = `${formatBytes(track.file.size)} -> PCM WAV`;
  rateValue.textContent = track.meta.sampleRate ? `${track.meta.sampleRate} Hz` : "-";
  channelsValue.textContent = track.meta.channels || "-";
  durationValue.textContent = formatTime(track.meta.duration);
  convertTimeValue.textContent = formatConvertMeta(track.meta);
  serverTimeValue.textContent = formatMs(track.meta.serverMs);
  engineValue.textContent = formatEngine(track.meta.engine);
  timelineValue.textContent = track.meta.timeline || "-";
  durationText.textContent = formatTime(track.meta.duration);
  downloadBtn.disabled = false;

  const waveReadStarted = performance.now();
  const waveBuffer = await track.blob.arrayBuffer();
  track.meta.browserTimings.push({
    source: "browser",
    key: "wav_arraybuffer",
    label: "Copy WAV blob to ArrayBuffer",
    ms: performance.now() - waveReadStarted,
  });
  const waveRenderStarted = performance.now();
  drawWaveform(waveBuffer);
  track.meta.browserTimings.push({
    source: "browser",
    key: "render_waveform",
    label: "Parse PCM and render waveform",
    ms: performance.now() - waveRenderStarted,
  });
  renderTimingDetail(track.meta);
  await audio.play().catch(() => {});
}

function parsePcmSamples(buffer) {
  const view = new DataView(buffer);
  let offset = 12;
  let channels = 1;
  let bits = 16;
  let dataOffset = -1;
  let dataSize = 0;

  while (offset + 8 <= view.byteLength) {
    const id = String.fromCharCode(
      view.getUint8(offset),
      view.getUint8(offset + 1),
      view.getUint8(offset + 2),
      view.getUint8(offset + 3),
    );
    const size = view.getUint32(offset + 4, true);
    const start = offset + 8;

    if (id === "fmt ") {
      channels = view.getUint16(start + 2, true);
      bits = view.getUint16(start + 14, true);
    } else if (id === "data") {
      dataOffset = start;
      dataSize = size;
      break;
    }
    offset = start + size + (size % 2);
  }

  if (dataOffset < 0 || bits !== 16) return { samples: new Int16Array(), channels };
  return {
    samples: new Int16Array(buffer, dataOffset, Math.floor(dataSize / 2)),
    channels,
  };
}

function drawEmptyWave() {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  waveShell.classList.remove("has-audio");
}

function drawWaveform(buffer) {
  const { samples, channels } = parsePcmSamples(buffer);

  if (!samples.length) {
    currentPeaks = null;
    drawEmptyWave();
    return;
  }

  const frames = Math.floor(samples.length / channels);
  const bars = Math.min(150, Math.max(72, Math.floor(canvas.width / 13)));
  const step = Math.max(1, Math.floor(frames / bars));
  const peaks = new Array(bars).fill(0);

  for (let i = 0; i < bars; i += 1) {
    let peak = 0;
    const frameStart = i * step;
    for (let j = 0; j < step && frameStart + j < frames; j += 1) {
      const sample = Math.abs(samples[(frameStart + j) * channels] / 32768);
      if (sample > peak) peak = sample;
    }
    peaks[i] = Math.min(1, Math.pow(peak, 0.55) * 1.45);
  }

  currentPeaks = peaks;
  waveShell.classList.add("has-audio");
  renderWave(0);
}

function renderWave(ratio) {
  if (!currentPeaks) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const bars = currentPeaks.length;
  const center = height * 0.5;
  const usable = height * 0.62;
  const left = width * 0.04;
  const right = width * 0.96;
  const gap = (right - left) / bars;
  const progress = Math.min(1, Math.max(0, ratio));

  ctx.clearRect(0, 0, width, height);
  ctx.lineCap = "round";
  for (let i = 0; i < bars; i += 1) {
    const h = Math.max(14, currentPeaks[i] * usable);
    const x = left + i * gap;
    ctx.strokeStyle = (i + 0.5) / bars <= progress ? "#4657ee" : "#dce6fb";
    ctx.lineWidth = Math.max(6, gap * 0.42);
    ctx.beginPath();
    ctx.moveTo(x, center - h / 2);
    ctx.lineTo(x, center + h / 2);
    ctx.stroke();
  }

  const px = left + progress * (right - left);
  ctx.lineCap = "butt";
  ctx.strokeStyle = "rgba(70, 87, 238, 0.85)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(px, height * 0.06);
  ctx.lineTo(px, height * 0.94);
  ctx.stroke();
}

function updateProgress() {
  const duration = audio.duration || 0;
  const current = audio.currentTime || 0;
  const ratio = duration ? current / duration : 0;
  seek.value = String(Math.round(ratio * 1000));
  currentTime.textContent = formatTime(current);
  durationText.textContent = formatTime(duration);
  renderWave(ratio);
}

function progressLoop() {
  updateProgress();
  progressRafId = requestAnimationFrame(progressLoop);
}

chooseFiles.addEventListener("click", () => fileInput.click());
chooseFolder.addEventListener("click", () => folderInput.click());
fileInput.addEventListener("change", (event) => ingestFiles(event.target.files));
folderInput.addEventListener("change", (event) => ingestFiles(event.target.files));
filterInput.addEventListener("input", renderTracks);

timingDetailToggle.addEventListener("click", () => {
  timingModal.hidden = false;
});

timingModalClose.addEventListener("click", () => {
  timingModal.hidden = true;
});

timingModal.addEventListener("click", (event) => {
  if (event.target.closest(".timing-modal-card")) return;
  timingModal.hidden = true;
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !timingModal.hidden) timingModal.hidden = true;
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragging");
});

dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  ingestFiles(event.dataTransfer.files);
});

playBtn.addEventListener("click", async () => {
  if (converting) return;
  if (activeIndex < 0 && tracks.length) {
    await playTrack(0);
    return;
  }
  if (audio.paused) {
    await audio.play().catch(() => {});
  } else {
    audio.pause();
  }
});

prevBtn.addEventListener("click", () => {
  if (converting) return;
  if (!tracks.length) return;
  playTrack(activeIndex <= 0 ? tracks.length - 1 : activeIndex - 1);
});

nextBtn.addEventListener("click", () => {
  if (converting) return;
  if (!tracks.length) return;
  playTrack((activeIndex + 1) % tracks.length);
});

stopBtn.addEventListener("click", () => {
  if (converting) return;
  audio.pause();
  audio.currentTime = 0;
});

seek.addEventListener("input", () => {
  if (!audio.duration) return;
  audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
});

downloadBtn.addEventListener("click", () => {
  if (!currentBlob || activeIndex < 0) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(currentBlob);
  a.download = tracks[activeIndex].file.name.replace(/\.nmf$/i, ".wav");
  a.click();
  URL.revokeObjectURL(a.href);
});

audio.addEventListener("timeupdate", updateProgress);
audio.addEventListener("loadedmetadata", updateProgress);
audio.addEventListener("play", () => {
  playBtn.classList.add("is-paused");
  cancelAnimationFrame(progressRafId);
  progressRafId = requestAnimationFrame(progressLoop);
});
audio.addEventListener("pause", () => {
  playBtn.classList.remove("is-paused");
  cancelAnimationFrame(progressRafId);
  updateProgress();
});
audio.addEventListener("ended", () => {
  if (activeIndex >= 0 && activeIndex + 1 < tracks.length) playTrack(activeIndex + 1);
});

drawEmptyWave();
checkHealth();
