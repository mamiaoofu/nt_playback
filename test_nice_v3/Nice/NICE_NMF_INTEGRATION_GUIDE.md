# NICE NMF Integration Guide

อัปเดต: 2026-07-03

เอกสารนี้อธิบายระบบแปลงไฟล์เสียง NICE `.nmf` เป็น PCM WAV สำหรับเล่นบน browser โดยไม่ต้องเปิด NICE Player GUI ฝั่งผู้ใช้ ระบบปัจจุบันใช้ flow เดียวกับเมนู Save WAV ของ NICE Player ผ่าน `.NET SaveMgr / WaveController` และเพิ่ม `NiceSaveMgrWorker.exe` เพื่อให้ประมวลผลเร็วขึ้นกว่า bridge PowerShell แบบเดิม

## สรุปสั้น

- Input: ไฟล์ NICE `.nmf`
- Output: PCM WAV, 8000 Hz, mono, 16-bit โดยปกติ
- Runtime ที่ต้องมีบนเครื่อง server: `C:\Program Files (x86)\NICE Systems\NICE Player Release 6`
- Engine หลัก: `NiceSaveMgrWorker.exe` แบบ x86 .NET Framework
- Flow แปลงเสียงหลัก: `LocalPlaylist` -> `WaveController` -> WAV
- Browser upload `.nmf` เข้า server เมื่อกดเล่น แล้ว server แปลงเป็น WAV ส่งกลับ browser
- Production mode ไม่ scan timeline packet แล้วเพื่อความเร็ว
- Debug mode เปิดด้วย `?debug=1` เพื่อดูรายละเอียด timing และ timeline `payload/preserved`

## โครงสร้างไฟล์ในโปรเจค

```text
Nice/
  start_nmf_player.bat
  NICE_NMF_INTEGRATION_GUIDE.md
  NICE_NMF_INTEGRATION_GUIDE.html

  nmf_web_player/
    index.html
    styles.css
    app.js
    server.py

  tools/
    NiceSaveMgrWorker.cs
    NiceSaveMgrWorker.exe
    nice_nmf_to_wav.py
    try_nice_player_wave_convert.ps1
    try_nice_nmf_convert.ps1
    NiceNmfConverter.cs

  NMF/
    *.nmf

  Manual NMF/
    *.wav

  NMF Converted/
    *.wav
```

## บทบาทของแต่ละ folder

`Nice/nmf_web_player`
เป็น web player หลัก แยกออกจาก Synway ชัดเจน มี frontend, CSS และ Python HTTP server สำหรับรับไฟล์ `.nmf` แล้วแปลงเป็น WAV

`Nice/tools`
เก็บ converter และ helper ที่เกี่ยวกับ NICE runtime ทั้งหมด ไฟล์สำคัญที่สุดใน production คือ `NiceSaveMgrWorker.exe`

`Nice/NMF`
เก็บไฟล์ `.nmf` ตัวอย่างสำหรับทดสอบผ่านเว็บหรือ command line

`Nice/Manual NMF`
เก็บ WAV ที่ save ด้วยมือจาก NICE Player GUI ใช้เป็น reference เพื่อเทียบว่า output จากระบบใหม่ตรงกับ NICE Player จริง

`Nice/NMF Converted`
เก็บ WAV ที่แปลงจากระบบหรือการทดสอบ batch

`__pycache__`
ไฟล์ cache ของ Python ไม่จำเป็นต้องนำไป deploy

## Runtime ที่ต้องติดตั้ง

ต้องมี NICE Player Release 6 บนเครื่องที่รัน server:

```text
C:\Program Files (x86)\NICE Systems\NICE Player Release 6
```

DLL ที่ระบบตรวจผ่าน `/api/health`:

```text
ERS.Common.dll
NiceApplications.Playback.Utils.dll
NiceApplications.Playback.MediaServices.Logic.dll
NiceApplications.Playback.PlayMgr.dll
NiceApplications.Playback.FileTypes.dll
NiceApplications.Playback.PlayList.Logic.dll
NiceApplications.Playback.Streaming.Common.dll
NiceApplications.Playback.InternalCommon.dll
Nice.Storage.CommonProjects.NMFClasses.dll
G72xCodersDll.dll
ACACVT32.DLL
```

คำแนะนำ: ควรติดตั้งหรือ copy runtime มาทั้ง folder ไม่ควร copy เฉพาะ DLL บางตัว เพราะ DLL หลักอาจ resolve dependency อื่นจาก folder เดียวกัน

## Flow การแปลงเสียง

Flow ที่ตรงกับเมนู Save WAV ของ NICE Player:

```text
LocalPlaylist.Load(input.nmf, true, false)
-> เลือก item แรกจาก playlist
-> ตั้ง item.OutputFileName = output.wav
-> WaveController.Init(item, -1, SaveMediaType.AllTypes)
-> WaveController.Save(null)
-> ได้ output WAV
```

จุดสำคัญ:

- `LocalPlaylist.Load(input, true, false)` ต้องใช้ค่าเดียวกับ SaveMgr ของ NICE Player
- `WaveController.Init(item, -1, SaveMediaType.AllTypes)` ทำให้ export ครอบคลุม media ที่ควรได้จาก player
- output จาก flow นี้เคยเทียบกับ manual save จาก NICE Player แล้วตรงแบบ byte-level สำหรับชุดทดสอบ 7/7 ไฟล์

## สถาปัตยกรรมปัจจุบัน

```text
Browser
  -> POST /api/convert?name=<file.nmf>&engine=dotnet
  -> server.py
  -> เขียน .nmf ลง temp folder
  -> ส่งงานเข้า SaveMgrWorker queue
  -> NiceSaveMgrWorker.exe โหลด NICE DLL แบบ x86
  -> LocalPlaylist + WaveController สร้าง WAV
  -> server.py อ่าน WAV + metadata
  -> ส่ง audio/wav กลับ browser
  -> app.js สร้าง audio object + waveform + timing detail
```

## ไฟล์ code แต่ละไฟล์ทำงานอย่างไร

### `start_nmf_player.bat`

ใช้เปิด web player ครั้งถัดไปแบบง่ายสำหรับผู้ใช้ทั่วไป หน้าที่หลักคือเข้า folder ที่ถูกต้อง แล้วรัน `server.py` บน port ที่กำหนด เช่น `6797`

ใช้เมื่อ:

- ผู้ใช้ต้องการเปิดเว็บ player เอง
- ไม่ต้องจำ command Python เต็ม
- เหมาะกับเครื่องทดสอบ/เครื่อง local

### `nmf_web_player/server.py`

เป็น Python HTTP server หลักของ NICE browser player

หน้าที่หลัก:

- serve ไฟล์ frontend: `index.html`, `app.js`, `styles.css`
- `GET /api/health` ตรวจ NICE runtime, DLL, worker exe และสถานะ converter
- `POST /api/convert` รับ raw `.nmf` bytes แล้วแปลงเป็น WAV
- สร้าง temp folder ต่อ request
- เรียก `NiceSaveMgrWorker.exe` ผ่าน persistent worker queue
- fallback ไป `nice_nmf_to_wav.convert_file()` ได้ ถ้าไม่มี worker exe แต่ยังมี PowerShell bridge
- อ่าน WAV metadata เช่น sample rate, channels, bits, frames, duration
- ตรวจ peak แบบ sampling ใน production
- ส่ง metadata กลับด้วย `X-NMF-*` headers
- ส่ง timing detail กลับด้วย `X-NMF-debug-timings`

องค์ประกอบสำคัญใน `server.py`:

- `SaveMgrWorker`
  จัดการ process `NiceSaveMgrWorker.exe --worker` ให้เปิดค้าง โหลด NICE DLL ค้าง และรับคำสั่งแปลงหลายไฟล์ต่อเนื่อง

- `SAVE_MGR_WORKER.lock`
  ทำหน้าที่เป็น queue แบบง่าย ทำให้ conversion ทำทีละงาน เพื่อเลี่ยงปัญหา thread-safety ของ NICE DLL

- `nice_status()`
  ตรวจไฟล์ runtime และรายงานสถานะให้ UI แสดงใน zone NICE runtime

- `convert_nmf()`
  flow หลักของ server สำหรับ 1 request: เขียน temp input, optional timeline debug, ส่งงานเข้า worker, อ่าน output, peak check, metadata

- `wav_peak()`
  production ใช้ sample บางส่วนเพื่อลดเวลา ถ้าดูเหมือนเงียบจึง fallback full scan

### `nmf_web_player/index.html`

โครงสร้างหน้าเว็บ player

ส่วนสำคัญ:

- sidebar สำหรับเลือกไฟล์/โฟลเดอร์ `.nmf`
- zone แสดง NICE runtime และ DLL ที่พบ
- list ไฟล์ `.nmf`
- player area: ชื่อไฟล์, progress, waveform, seek bar, ปุ่ม control
- modal สำหรับ timing detail
- `<audio>` สำหรับเล่น WAV ที่ server ส่งกลับ

### `nmf_web_player/styles.css`

ออกแบบ UI ของ player

ดูแลเรื่อง:

- layout ซ้าย/ขวา
- card และ panel ของ runtime
- list ไฟล์
- waveform card
- playback controls
- timing detail modal
- responsive layout เมื่อจอแคบ

ข้อควรระวังตอนแก้:

- อย่าให้ timing detail ทับ waveform
- list ไฟล์ควรมีพื้นที่ scroll เพียงพอ
- ปุ่ม control ควรมีขนาดคงที่ ไม่กระโดดตามข้อความ

### `nmf_web_player/app.js`

logic ฝั่ง browser

หน้าที่หลัก:

- รับไฟล์จาก file picker หรือ folder picker
- filter เฉพาะ `.nmf`
- แสดงรายการไฟล์และสถานะ `NMF`, `...`, `WAV`, `ERR`
- เมื่อผู้ใช้คลิกไฟล์ จะส่งไฟล์ไป `POST /api/convert`
- วัด browser timing เช่น read file, upload/wait, read blob, render waveform
- อ่าน `X-NMF-*` headers จาก server
- สร้าง Blob URL ให้ `<audio>` เล่น
- parse WAV เพื่อวาด waveform
- sync seek bar กับเวลาเล่น
- แสดง timing summary และ timing detail modal
- ถ้า URL มี `?debug=1` จะส่ง `debug=1` ไป server เพื่อเปิด timeline scan

### `tools/NiceSaveMgrWorker.cs`

source code ของ worker หลัก

หน้าที่:

- compile เป็น x86 `.NET Framework` exe
- โหลด NICE DLL จาก `C:\Program Files (x86)\NICE Systems\NICE Player Release 6`
- ติดตั้ง `AssemblyResolve` เพื่อ resolve DLL dependency จาก NICE folder
- สร้าง `LocalPlaylist`
- เรียก `WaveController`
- รองรับสองโหมด:
  - one-shot: `NiceSaveMgrWorker.exe input.nmf output.wav`
  - persistent worker: `NiceSaveMgrWorker.exe --worker`

worker mode protocol:

```text
stdin:
CONVERT<TAB><base64 input path><TAB><base64 output path>

stdout:
OK<TAB><elapsed ms><TAB><base64 output path>
ERR<TAB><elapsed ms><TAB><base64 error message>
```

เหตุผลที่ใช้ base64 path: ป้องกันปัญหา path ที่มี space, Unicode, tab หรือ character พิเศษ

คำสั่ง build:

```powershell
C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe `
  /nologo `
  /platform:x86 `
  /target:exe `
  /out:C:\Users\ZerOBat\Desktop\Encrypt\Nice\tools\NiceSaveMgrWorker.exe `
  C:\Users\ZerOBat\Desktop\Encrypt\Nice\tools\NiceSaveMgrWorker.cs
```

ต้อง build เป็น x86 เท่านั้น เพราะ NICE Player Release 6 เป็น 32-bit

### `tools/NiceSaveMgrWorker.exe`

compiled worker ที่ server ใช้งานจริง

ข้อดีเมื่อเทียบกับ PowerShell bridge เดิม:

- ไม่ต้องเปิด 32-bit PowerShell ต่อไฟล์
- ไม่ต้อง `Add-Type` compile C# ทุก request
- โหลด NICE DLL ค้างไว้ใน process เดียว
- request ถัดไปเร็วขึ้นมาก
- server สามารถคุม queue ได้ชัดเจน

### `tools/nice_nmf_to_wav.py`

Python wrapper สำหรับแปลง `.nmf` เป็น `.wav` นอกเว็บ หรือใช้เป็น fallback path

function หลัก:

```python
convert_file(
    input_nmf: Path,
    output_wav: Path,
    sample_rate: int = 8000,
    preserve_timeline: bool = True,
    engine: str = "dotnet",
)
```

พฤติกรรมปัจจุบัน:

- ถ้าเจอ `NiceSaveMgrWorker.exe` จะใช้ exe นี้แบบ one-shot
- ถ้าไม่มี worker exe จะ fallback ไป `try_nice_player_wave_convert.ps1`
- legacy code สำหรับ `NmfToVox PCM_A_LAW` ยังอยู่ แต่ไม่ใช่ path หลักสำหรับ production

ตัวอย่าง CLI:

```powershell
python C:\Users\ZerOBat\Desktop\Encrypt\Nice\tools\nice_nmf_to_wav.py `
  C:\audio\input.nmf `
  C:\audio\output.wav
```

### `tools/try_nice_player_wave_convert.ps1`

PowerShell bridge แบบเดิม ใช้เป็น fallback/legacy

หน้าที่:

- รันด้วย 32-bit PowerShell
- ใช้ `Add-Type` compile C# bridge ใน memory
- โหลด NICE DLL
- เรียก `LocalPlaylist` และ `WaveController`
- สร้าง WAV output

ยังควรเก็บไฟล์นี้ไว้ เพราะ:

- ใช้ debug เมื่อ worker exe มีปัญหา
- ใช้เป็น fallback หาก exe ถูกลบหรือ build ไม่ได้
- ใช้เทียบ behavior ระหว่าง worker กับ bridge เดิม

คำสั่ง:

```powershell
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe `
  -NoProfile `
  -ExecutionPolicy Bypass `
  -File C:\Users\ZerOBat\Desktop\Encrypt\Nice\tools\try_nice_player_wave_convert.ps1 `
  -InputNmf C:\audio\input.nmf `
  -OutputFile C:\audio\output.wav
```

### `tools/try_nice_nmf_convert.ps1`

legacy experiment สำหรับ path `MediaFileConverter.NmfToVox`

สถานะ:

- ไม่ใช่ production path
- เคยใช้ทดลอง export payload เป็น codec เช่น `PCM_A_LAW`
- บางไฟล์ได้เสียงเงียบหรือ duration/sample ไม่ตรง manual save
- เก็บไว้เพื่อ reference/research เท่านั้น

### `tools/NiceNmfConverter.cs`

legacy C# helper สำหรับ path `NmfToVox`

สถานะ:

- ไม่ใช่ production path
- ไม่ควรใช้แทน SaveMgr สำหรับงานจริง
- ใช้ศึกษา API ของ NICE MediaFileConverter ได้

### `NICE_NMF_INTEGRATION_GUIDE.md`

เอกสาร markdown สำหรับอ่านใน editor, repo, หรือส่งต่อ dev

### `NICE_NMF_INTEGRATION_GUIDE.html`

เอกสาร HTML สำหรับเปิดอ่านใน browser ให้อ่านง่ายกว่า markdown

## API สำหรับเชื่อมต่อระบบอื่น

### Health check

```http
GET http://127.0.0.1:6797/api/health
```

ตัวอย่าง response:

```json
{
  "ok": true,
  "niceBase": "C:\\Program Files (x86)\\NICE Systems\\NICE Player Release 6",
  "powershell32": "C:\\Windows\\SysWOW64\\WindowsPowerShell\\v1.0\\powershell.exe",
  "saveMgrWorker": "C:\\Users\\ZerOBat\\Desktop\\Encrypt\\Nice\\tools\\NiceSaveMgrWorker.exe",
  "saveMgrWorkerReady": true,
  "playerSaveBridge": "C:\\Users\\ZerOBat\\Desktop\\Encrypt\\Nice\\tools\\try_nice_player_wave_convert.ps1",
  "dotnetReady": true,
  "supportedEngines": ["dotnet"],
  "missing": []
}
```

### Convert

```http
POST http://127.0.0.1:6797/api/convert?name=<filename.nmf>&engine=dotnet
Content-Type: application/octet-stream

<raw .nmf bytes>
```

เปิด debug:

```http
POST http://127.0.0.1:6797/api/convert?name=<filename.nmf>&engine=dotnet&debug=1
```

ตัวอย่าง `curl`:

```powershell
curl.exe -X POST `
  --data-binary "@C:\audio\input.nmf" `
  "http://127.0.0.1:6797/api/convert?name=input.nmf&engine=dotnet" `
  -o "C:\audio\output.wav"
```

response สำเร็จ:

```text
HTTP/1.0 200 OK
Content-Type: audio/wav
Content-Length: <wav bytes>
X-NMF-source-name: input.nmf
X-NMF-source-size: 1250000
X-NMF-sample-rate: 8000
X-NMF-channels: 1
X-NMF-bits: 16
X-NMF-frames: 689656
X-NMF-duration: 86.207
X-NMF-timeline: skipped
X-NMF-peak: 12345
X-NMF-engine: dotnet_save_mgr_worker
X-NMF-convert-ms: 571.5
X-NMF-server-ms: 582.5
X-NMF-cache-status: fresh
X-NMF-debug-timings: [...]
```

## ความหมายของ timing

`Convert time`
เวลาที่ worker ใช้เรียก NICE SaveMgr/WaveController เพื่อสร้าง WAV จริง ไม่รวมเวลารอคิว, เขียน temp, อ่าน WAV, peak check และส่งกลับ browser

`Server time`
เวลารวมฝั่ง server ต่อ request รวม read upload, temp file, queue wait, conversion, read WAV, metadata และ peak check

`Browser time`
เวลารวมตั้งแต่ browser เริ่มอ่านไฟล์ `.nmf`, upload, รอ server, รับ WAV blob และเตรียม playback

`Queue wait`
เวลาที่ request รอ worker ว่าง ถ้ามีผู้ใช้หลายคนกดแปลงพร้อมกัน ค่านี้จะสูงขึ้น

`Start x86 .NET SaveMgr worker`
เกิดเฉพาะ request แรกหลังเปิด server หรือหลัง worker restart เพราะต้องเปิด process และโหลด NICE DLL

`Sample WAV peak`
ตรวจระดับเสียงแบบ sampling เพื่อความเร็ว

`Scan NMF timeline packets`
มีเฉพาะ `?debug=1` ไม่ทำใน production

## การนำไปพัฒนาต่อหรือเชื่อมต่อกับระบบอื่น

แนวทางที่แนะนำที่สุดคือให้ระบบอื่นเรียกผ่าน HTTP API:

```text
ระบบหลัก -> POST .nmf -> NICE conversion service -> audio/wav -> ระบบหลัก/browser
```

ข้อดี:

- แยก dependency NICE 32-bit ออกจากระบบหลัก
- ระบบหลักไม่ต้องโหลด DLL เก่าโดยตรง
- scale แยก service ได้ง่ายกว่า
- debug ผ่าน `/api/health` และ headers ได้

ถ้าต้อง integrate ใน Python โดยตรง:

```python
from pathlib import Path
from nice_nmf_to_wav import convert_file

convert_file(
    Path(r"C:\audio\input.nmf"),
    Path(r"C:\audio\output.wav"),
    engine="dotnet",
)
```

ถ้าต้อง integrate กับ backend อื่น เช่น Node.js, .NET Web API, Java:

- แนะนำให้เรียก HTTP service เดิม
- หรือ spawn `NiceSaveMgrWorker.exe` เป็น worker แยก process
- อย่าโหลด NICE DLL เข้า process หลักของ backend โดยตรงถ้า backend เป็น 64-bit

## ข้อควรระวังด้าน production

- NICE runtime เป็น 32-bit และเก่า ควร isolate เป็น worker/service แยก
- conversion ถูก serialize ผ่าน queue เดียวเพื่อความเสถียร
- ถ้าผู้ใช้เยอะ ควรทำ job queue + progress + retry
- ถ้าต้องการ parallel จริง ควรทดสอบหลาย worker process แยกกัน ไม่ควรทำ multi-thread ใน process worker เดียวทันที
- ตั้ง timeout ต่อ conversion
- log ชื่อไฟล์, file size, convert time, server time, error message
- temp folder ควรถูกลบหลังจบ request
- ห้าม expose service นี้ออก internet โดยตรงโดยไม่มี auth/rate limit/file size limit

## Error ที่อาจเกิดขึ้น

### NICE Player runtime is not ready

สาเหตุ:

- ไม่มี NICE Player Release 6
- path runtime ไม่ตรง
- DLL สำคัญหาย
- worker exe หาย และ PowerShell fallback ก็ใช้ไม่ได้

วิธีตรวจ:

```http
GET /api/health
```

ให้ดู field:

- `ok`
- `missing`
- `requiredFiles`
- `saveMgrWorkerReady`
- `dotnetReady`

### missing .NET SaveMgr worker

สาเหตุ:

- ไม่มี `Nice/tools/NiceSaveMgrWorker.exe`
- ยังไม่ได้ build worker
- deploy ข้ามไฟล์ exe ไป

วิธีแก้:

- build จาก `NiceSaveMgrWorker.cs`
- หรือให้ fallback ใช้ `try_nice_player_wave_convert.ps1`

### NiceSaveMgrWorker must be compiled/run as x86

สาเหตุ:

- build เป็น AnyCPU หรือ x64
- ใช้ `Framework64` compiler โดยไม่ได้กำหนด `/platform:x86`

วิธีแก้:

```powershell
C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe /platform:x86 ...
```

### NICE SaveMgr worker did not start correctly

สาเหตุ:

- worker เปิดไม่ได้
- runtime DLL load fail
- process ถูก antivirus/block
- stdout ไม่ได้ส่ง `READY`

วิธีแก้:

- รัน `NiceSaveMgrWorker.exe --worker` ด้วยมือ
- ตรวจว่าไม่มี error จาก runtime
- ลอง one-shot mode กับไฟล์จริง

### LocalPlaylist did not load any media from the NMF file

สาเหตุ:

- ไฟล์ `.nmf` เสีย
- เป็น NMF format คนละ version
- NICE runtime อ่านไฟล์นี้ไม่ได้
- path/temp permission มีปัญหา

วิธีแก้:

- เปิดไฟล์เดียวกันด้วย NICE Player GUI
- ลอง manual Save WAV
- ตรวจว่าไฟล์ upload มาเต็มหรือไม่

### LocalPlaylist did not expose any media streams

สาเหตุ:

- playlist load ได้ แต่ไม่มี media stream
- NMF อาจเป็น metadata-only หรือ format ไม่รองรับ

วิธีแก้:

- ตรวจไฟล์ด้วย NICE Player GUI
- ลองไฟล์ reference อื่นเพื่อแยกว่าเป็นปัญหาไฟล์หรือ runtime

### WaveController produced an empty WAV

สาเหตุ:

- SaveMgr ทำงานแต่ไม่ได้เขียนเสียง
- output path เขียนไม่ได้
- ไฟล์ unsupported
- dependency บางตัว load ไม่ครบ

วิธีแก้:

- ตรวจ permission temp folder
- ลอง output path สั้น ๆ เช่น `C:\Temp\out.wav`
- เทียบกับ manual Save WAV

### NICE Player SaveMgr produced a near-silent WAV

สาเหตุ:

- WAV ออกมาแทบเงียบ
- ไฟล์อาจไม่รองรับ
- conversion path ผิด

หมายเหตุ:

- production จะ sample peak ก่อน
- ถ้า sample peak ต่ำ จะ full scan ซ้ำก่อน error

### only .nmf files are supported

สาเหตุ:

- query `name=` ไม่ลงท้าย `.nmf`
- upload file ผิดชนิด

วิธีแก้:

- ส่งชื่อไฟล์จริงพร้อม `.nmf`
- ตรวจ frontend/backend integration

### empty upload

สาเหตุ:

- body ว่าง
- client ส่ง request ผิด
- file picker ได้ไฟล์ 0 byte

วิธีแก้:

- ตรวจ Content-Length
- ตรวจไฟล์ต้นทาง

## Debug mode

เปิด debug ด้วย URL:

```text
http://127.0.0.1:6797/?debug=1
```

ผลที่เปลี่ยน:

- browser ส่ง `debug=1` ไป `/api/convert`
- server scan NMF timeline packets
- header `X-NMF-timeline` จะเป็น `payload` หรือ `preserved`
- timing detail จะมี `Scan NMF timeline packets`
- peak check ใช้ full scan

ใช้ debug mode เมื่อ:

- ต้องการวิเคราะห์ว่าเวลาหายตรงไหน
- ต้องการเทียบ payload/preserved
- ต้องการตรวจไฟล์แปลก ๆ

ไม่ควรเปิด debug เป็น default ใน production เพราะทำให้ช้าลง

## การ build และ deploy

ไฟล์ที่ควร deploy:

```text
Nice/
  start_nmf_player.bat
  nmf_web_player/
    index.html
    styles.css
    app.js
    server.py
  tools/
    NiceSaveMgrWorker.exe
    NiceSaveMgrWorker.cs
    nice_nmf_to_wav.py
    try_nice_player_wave_convert.ps1
```

ไฟล์ที่ไม่จำเป็นต้อง deploy:

```text
__pycache__/
NMF/
Manual NMF/
NMF Converted/
```

ยกเว้นถ้าต้องการส่งไฟล์ทดสอบไปด้วย

## Checklist ก่อนส่งต่อระบบจริง

- ติดตั้ง NICE Player Release 6 บน server
- `GET /api/health` ได้ `ok: true`
- `saveMgrWorkerReady: true`
- DLL ทุกตัวใน `requiredFiles` เป็น `exists: true`
- ทดสอบ convert ไฟล์จริงอย่างน้อย 3 ขนาด: เล็ก, กลาง, ใหญ่
- เทียบ duration กับ NICE Player manual save
- ตรวจว่า `X-NMF-engine` เป็น `dotnet_save_mgr_worker`
- ตรวจว่า production ได้ `X-NMF-timeline: skipped`
- เปิด `?debug=1` แล้ว timing detail แสดงครบ
- ทดสอบ 2 request พร้อมกันและดู `queue_wait`
- ตั้ง limit ขนาดไฟล์และ timeout ตามระบบจริง
- เก็บ log error ต่อไฟล์เพื่อ trace ภายหลัง

## สรุปสำหรับทีม Dev

ระบบนี้ไม่ได้ถอดรหัส `.nmf` ด้วย algorithm ที่เขียนเอง แต่เรียก flow export WAV ของ NICE Player ผ่าน DLL ของ NICE โดยตรง ดังนั้น server ที่ใช้งานต้องมี NICE runtime ครบ

เส้นทาง production ที่ควรใช้:

```text
HTTP POST .nmf -> server.py -> NiceSaveMgrWorker.exe -> NICE WaveController -> WAV
```

เส้นทาง fallback:

```text
nice_nmf_to_wav.py -> try_nice_player_wave_convert.ps1 -> Add-Type C# bridge -> WAV
```

ไม่แนะนำให้ใช้ legacy `NmfToVox PCM_A_LAW` เป็น production path เพราะเคยพบว่า output ไม่ตรงกับ manual Save WAV ในบางไฟล์
