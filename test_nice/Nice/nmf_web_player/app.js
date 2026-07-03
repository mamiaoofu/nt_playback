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
const playhead = document.querySelector("#playhead");
const seek = document.querySelector("#seek");
const currentTime = document.querySelector("#currentTime");
const durationText = document.querySelector("#duration");
const playBtn = document.querySelector("#playBtn");
const playIcon = document.querySelector("#playIcon");
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

let tracks = [];
let activeIndex = -1;
let objectUrl = "";
let currentBlob = null;
let converting = false;

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

function getConverterMode() {
  return converterModeInputs.find((input) => input.checked)?.value || "powershell";
}

function formatEngine(engine) {
  return engine === "dotnet" ? ".NET" : "PowerShell";
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
    item.textContent = `${file.exists ? "พบ" : "ไม่พบ"} ${file.name}`;
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
  playhead.style.left = "0%";
  playIcon.textContent = "Play";
  downloadBtn.disabled = true;
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
    runtimePath.textContent = data.niceBase || "NICE Player runtime not found";
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
  converting = true;
  setControlsEnabled(false);
  track.status = "loading";
    renderTracks();
    setStatus("converting", "busy");
  setTimingSummary(null);
  setProcess("กำลังอ่านไฟล์", track.file.name, 20);

  try {
    const engine = getConverterMode();
    const body = await track.file.arrayBuffer();
    setProcess("กำลังส่งเข้า server", `${formatBytes(track.file.size)} -> NICE converter`, 35);

    const pendingTimer = window.setTimeout(() => {
      setProcess("กำลังแปลงด้วย NICE runtime", "ขั้นตอนนี้ใช้ DLL จาก NICE Player บนเครื่อง server", 55, true);
    }, 250);

    let response;
    try {
      response = await fetch(`/api/convert?name=${encodeURIComponent(track.file.name)}&engine=${encodeURIComponent(engine)}`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body,
      });
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
    track.blob = await response.blob();
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

  drawWaveform(await track.blob.arrayBuffer());
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
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#081112";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(198, 138, 36, 0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height / 2);
  ctx.lineTo(width, height / 2);
  ctx.stroke();
}

function drawWaveform(buffer) {
  const { samples, channels } = parsePcmSamples(buffer);
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#081112";
  ctx.fillRect(0, 0, width, height);

  const mid = height / 2;
  const usable = height * 0.78;
  ctx.strokeStyle = "rgba(232, 237, 240, 0.13)";
  ctx.lineWidth = 1;
  for (let y = 1; y < 4; y += 1) {
    const lineY = height * (y / 4);
    ctx.beginPath();
    ctx.moveTo(0, lineY);
    ctx.lineTo(width, lineY);
    ctx.stroke();
  }

  ctx.strokeStyle = "#c68a24";
  ctx.lineWidth = 2;
  ctx.beginPath();
  const frames = Math.floor(samples.length / channels);
  const step = Math.max(1, Math.floor(frames / width));
  for (let x = 0; x < width; x += 1) {
    let min = 1;
    let max = -1;
    const frameStart = x * step;
    for (let i = 0; i < step && frameStart + i < frames; i += 1) {
      const sample = samples[(frameStart + i) * channels] / 32768;
      if (sample < min) min = sample;
      if (sample > max) max = sample;
    }
    ctx.moveTo(x, mid + min * usable * 0.5);
    ctx.lineTo(x, mid + max * usable * 0.5);
  }
  ctx.stroke();
}

function updateProgress() {
  const duration = audio.duration || 0;
  const current = audio.currentTime || 0;
  const ratio = duration ? current / duration : 0;
  seek.value = String(Math.round(ratio * 1000));
  playhead.style.left = `${Math.min(100, Math.max(0, ratio * 100))}%`;
  currentTime.textContent = formatTime(current);
  durationText.textContent = formatTime(duration);
}

chooseFiles.addEventListener("click", () => fileInput.click());
chooseFolder.addEventListener("click", () => folderInput.click());
fileInput.addEventListener("change", (event) => ingestFiles(event.target.files));
folderInput.addEventListener("change", (event) => ingestFiles(event.target.files));
filterInput.addEventListener("input", renderTracks);

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
  playIcon.textContent = "Pause";
});
audio.addEventListener("pause", () => {
  playIcon.textContent = "Play";
});
audio.addEventListener("ended", () => {
  if (activeIndex >= 0 && activeIndex + 1 < tracks.length) playTrack(activeIndex + 1);
});

drawEmptyWave();
checkHealth();
