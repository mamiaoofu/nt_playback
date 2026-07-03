# NICE NMF Integration Guide

อัปเดต: 2026-07-03

เอกสารนี้อธิบายระบบแปลงไฟล์เสียง NICE `.nmf` เป็น `.wav` สำหรับ browser player ในโปรเจคนี้ โดยเวอร์ชันปัจจุบันใช้เส้นทางเดียวคือ **.NET SaveMgr** เพื่อให้ผลลัพธ์ตรงกับการกด Save WAV จาก NICE Player มากที่สุด

> หมายเหตุสำคัญ: ยังมีไฟล์ legacy บางตัวใน `Nice/tools` สำหรับการทดลองเดิม แต่ flow ที่ใช้จริงสำหรับเว็บและการ integrate คือ `.NET SaveMgr` เท่านั้น ไม่ใช้ `NmfToVox PCM_A_LAW` เป็นทางหลักแล้ว

## สรุปสั้น

- Input: ไฟล์ NICE `.nmf`
- Output: PCM WAV เล่นบน browser ได้ทันที
- Engine ที่ใช้จริง: `.NET SaveMgr`
- Runtime ที่ต้องมีบนเครื่อง server: `C:\Program Files (x86)\NICE Systems\NICE Player Release 6`
- Bridge หลัก: `Nice/tools/try_nice_player_wave_convert.ps1`
- Python entry point: `Nice/tools/nice_nmf_to_wav.py`
- Web server: `Nice/nmf_web_player/server.py`
- Browser player: `Nice/nmf_web_player/index.html`, `app.js`, `styles.css`

## ทำไมเปลี่ยนมาใช้ .NET SaveMgr อย่างเดียว

ก่อนหน้านี้เคยทดลอง path `MediaFileConverter.NmfToVox(..., PCM_A_LAW)` แล้ว decode A-law เป็น WAV เอง แต่พบปัญหา:

- บางไฟล์แปลงออกมาเป็นเสียงเงียบหรือ waveform ไม่ขึ้น
- บางไฟล์ duration ใกล้เคียงแต่ sample ไม่ตรงกับไฟล์ที่ Save จาก NICE Player
- flow นั้นไม่ใช่ flow เดียวกับเมนู Save WAV ใน NICE Player

หลังจากแกะ flow ของ NICE Player พบว่าเมนู Save WAV ใช้แนวทาง:

```text
LocalPlaylist.Load(input.nmf, bUseSummedMedia: true, bIsFTFMode: false)
-> เลือก item แรกจาก playlist
-> ตั้ง item.OutputFileName = output.wav
-> WaveController.Init(item, -1, SaveMediaType.AllTypes)
-> WaveController.Save(...)
```

เมื่อนำ flow นี้มาใช้ ผลเทียบกับไฟล์ manual ที่ Save จาก NICE Player ได้ตรงแบบ byte-level สำหรับชุดทดสอบ 7/7 ไฟล์

## Runtime ที่ต้องมี

ต้องติดตั้ง NICE Player Release 6 บนเครื่องที่รัน server:

```text
C:\Program Files (x86)\NICE Systems\NICE Player Release 6
```

ไฟล์ DLL หลักที่ health check ตรวจ:

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

ควรเก็บ runtime ทั้ง folder ไว้ครบ เพราะ DLL เหล่านี้อาจ resolve dependency อื่นต่อจาก folder เดียวกัน

## บทบาทของ 32-bit PowerShell

ถึงชื่อไฟล์ bridge จะเป็น `.ps1` แต่ในเวอร์ชันปัจจุบัน **ไม่ได้ใช้ PowerShell เป็น converter mode** และไม่ได้เรียก `NmfToVox`

เหตุผลที่ยังใช้ 32-bit PowerShell:

- NICE Player Release 6 เป็น 32-bit
- DLL ของ NICE ต้องถูกโหลดใน process แบบ x86
- script ใช้ `Add-Type` compile C# bridge ใน memory
- C# bridge เป็นตัวเรียก `LocalPlaylist` และ `WaveController`

ดังนั้นให้มองว่า:

```text
32-bit PowerShell = x86 host process
.NET SaveMgr     = actual conversion flow
```

## Flow การทำงาน

```text
Browser
  -> POST /api/convert?name=<file.nmf>&engine=dotnet
  -> server.py
  -> nice_nmf_to_wav.convert_file(..., engine="dotnet")
  -> extract_wav_with_player_save(...)
  -> 32-bit PowerShell host
  -> try_nice_player_wave_convert.ps1
  -> Add-Type C# bridge
  -> NICE LocalPlaylist + WaveController
  -> output PCM WAV
  -> server ส่ง audio/wav กลับ browser
```

## ไฟล์สำคัญ

### `Nice/nmf_web_player/server.py`

ทำหน้าที่เป็น HTTP server สำหรับเว็บ player

หน้าที่หลัก:

- `GET /api/health`
  - ตรวจ NICE runtime
  - ตรวจ DLL ที่จำเป็น
  - ตรวจ bridge `.NET SaveMgr`
- `POST /api/convert`
  - รับ binary `.nmf`
  - เขียนลง temp folder
  - เรียก `convert_file(..., engine="dotnet")`
  - อ่าน WAV กลับมา
  - ส่ง response เป็น `audio/wav`
  - ส่ง metadata ผ่าน `X-NMF-*` headers

headers สำคัญที่ส่งกลับ:

```text
X-NMF-source-name
X-NMF-source-size
X-NMF-sample-rate
X-NMF-channels
X-NMF-bits
X-NMF-frames
X-NMF-duration
X-NMF-peak
X-NMF-engine
X-NMF-convert-ms
X-NMF-server-ms
X-NMF-cache-status
```

ค่า engine ที่คาดหวัง:

```text
dotnet
.net
net
```

ระบบ normalize เป็น `.NET SaveMgr` และ response header จะรายงานเป็น:

```text
X-NMF-engine: dotnet_save_mgr
```

### `Nice/tools/nice_nmf_to_wav.py`

เป็น Python wrapper สำหรับเรียก converter

function ที่ใช้จริง:

```python
convert_file(
    input_nmf: Path,
    output_wav: Path,
    sample_rate: int = 8000,
    preserve_timeline: bool = True,
    engine: str = "dotnet",
)
```

เมื่อ `engine` เป็น `dotnet`, `.net`, `net`, `player`, `player_save`, หรือ `save_mgr` จะเรียก:

```python
extract_wav_with_player_save(input_nmf, output_wav)
```

เส้นทางนี้จะได้ WAV จาก NICE `WaveController` โดยตรง จึงไม่ต้อง decode A-law เอง

### `Nice/tools/try_nice_player_wave_convert.ps1`

เป็น bridge หลักสำหรับ `.NET SaveMgr`

ต้องรันด้วย:

```text
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe
```

parameter:

```powershell
-InputNmf <path to input.nmf>
-OutputFile <path to output.wav>
```

ตัวอย่าง:

```powershell
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe `
  -NoProfile `
  -ExecutionPolicy Bypass `
  -File C:\Users\ZerOBat\Desktop\Encrypt\Nice\tools\try_nice_player_wave_convert.ps1 `
  -InputNmf C:\audio\input.nmf `
  -OutputFile C:\audio\output.wav
```

สิ่งที่ script ทำ:

1. ตรวจว่ารันใน 32-bit process
2. ตั้ง `NiceBase` เป็น NICE Player runtime folder
3. ติดตั้ง `AssemblyResolve` เพื่อโหลด dependency จาก NICE folder
4. โหลด DLL หลักของ NICE
5. สร้าง `LocalPlaylist`
6. เรียก `LocalPlaylist.Load(inputNmf, true, false)`
7. รอจน playlist load item ได้
8. เลือก item แรก
9. ตั้ง `item.OutputFileName = outputWav`
10. สร้าง `WaveController`
11. เรียก `WaveController.Init(item, -1, SaveMediaType.AllTypes)`
12. เรียก `WaveController.Save(null)`
13. ตรวจว่า output WAV ถูกสร้างและไม่ว่าง

จุดสำคัญคือ `Load(..., true, false)` และ `Init(item, -1, ...)` เพราะตรงกับ flow ของ `SaveForm/SaveMgr` ใน NICE Player มากกว่า save เฉพาะ media stream เดี่ยว

## API สำหรับ integrate

### Health check

```http
GET http://127.0.0.1:7797/api/health
```

ตัวอย่าง response:

```json
{
  "ok": true,
  "niceBase": "C:\\Program Files (x86)\\NICE Systems\\NICE Player Release 6",
  "powershell32": "C:\\Windows\\SysWOW64\\WindowsPowerShell\\v1.0\\powershell.exe",
  "playerSaveBridge": "C:\\Users\\ZerOBat\\Desktop\\Encrypt\\Nice\\tools\\try_nice_player_wave_convert.ps1",
  "dotnetReady": true,
  "supportedEngines": ["dotnet"],
  "missing": []
}
```

คำว่า `powershell32` ใน response หมายถึง host process ที่ใช้โหลด NICE 32-bit DLL ไม่ใช่ PowerShell converter mode

### Convert

```http
POST http://127.0.0.1:7797/api/convert?name=<filename.nmf>&engine=dotnet
Content-Type: application/octet-stream

<raw .nmf bytes>
```

ตัวอย่าง `curl`:

```powershell
curl.exe -X POST `
  --data-binary "@C:\audio\input.nmf" `
  "http://127.0.0.1:7797/api/convert?name=input.nmf&engine=dotnet" `
  -o "C:\audio\output.wav"
```

ตัวอย่าง response header:

```text
HTTP/1.0 200 OK
Content-Type: audio/wav
X-NMF-sample-rate: 8000
X-NMF-channels: 1
X-NMF-bits: 16
X-NMF-duration: 86.207
X-NMF-engine: dotnet_save_mgr
X-NMF-convert-ms: 2460.1
X-NMF-server-ms: 2600.0
```

## ตัวอย่าง integrate จาก Python

```python
from pathlib import Path
from nice_nmf_to_wav import convert_file

convert_file(
    Path(r"C:\audio\input.nmf"),
    Path(r"C:\audio\output.wav"),
    engine="dotnet",
)
```

ถ้า integrate ผ่าน HTTP:

```python
import requests
from pathlib import Path

src = Path(r"C:\audio\input.nmf")
url = "http://127.0.0.1:7797/api/convert"

response = requests.post(
    url,
    params={"name": src.name, "engine": "dotnet"},
    data=src.read_bytes(),
    headers={"Content-Type": "application/octet-stream"},
    timeout=120,
)
response.raise_for_status()
Path(r"C:\audio\output.wav").write_bytes(response.content)
```

## ข้อควรระวังเรื่อง performance

ปัจจุบัน `.NET SaveMgr` ยังเป็นการ spawn 32-bit host process ต่อ conversion หนึ่งครั้ง:

```text
request 1 -> start 32-bit PowerShell -> load NICE DLL -> convert -> exit
request 2 -> start 32-bit PowerShell -> load NICE DLL -> convert -> exit
```

ข้อดี:

- แยก process ต่อไฟล์
- memory/state ของ NICE runtime ไม่ค้างข้าม request
- debug ง่าย
- ผลลัพธ์ตรงกับ NICE Player Save WAV

ข้อเสีย:

- มี overhead จากการเปิด process และ load DLL ทุกครั้ง
- ถ้ามีผู้ใช้หลายคนแปลงพร้อมกัน server จะใช้ CPU/RAM เพิ่มตามจำนวน process

แนวทาง production ที่แนะนำ:

- จำกัดจำนวน conversion พร้อมกันด้วย queue
- ตั้ง timeout ต่อ conversion
- ลบ temp file ทุกครั้งหลังแปลง
- log convert time และ error ต่อไฟล์
- ถ้าปริมาณงานสูงมาก ค่อยพิจารณาทำ x86 worker/service ที่โหลด NICE DLL ค้างไว้

## ข้อควรระวังเรื่อง thread/process

NICE DLL รุ่นนี้เก่าและเป็น 32-bit จึงควรหลีกเลี่ยงการโหลด DLL เข้า process web หลักโดยตรง ถ้า web server เป็น 64-bit หรือมีงานอื่นร่วมกัน

รูปแบบที่ปลอดภัยกว่า:

```text
Web/API 64-bit process
  -> spawn isolated x86 conversion process
  -> receive WAV
  -> return to browser
```

หรือใน production:

```text
Web/API
  -> queue
  -> dedicated x86 converter worker
  -> WAV result
```

## การตรวจสอบว่า output ถูกต้อง

สิ่งที่ควรเช็ค:

- WAV เปิดเล่นได้
- sample rate = `8000 Hz`
- channels = `1`
- bits = `16`
- duration ตรงกับ NICE Player manual save
- waveform ไม่เงียบ
- ถ้ามีไฟล์ manual reference ให้เทียบ byte-level ได้

ผลทดสอบล่าสุดในโปรเจคนี้:

```text
NMF 7 files
Manual WAV reference 7 files
.NET SaveMgr output byte_equal true 7/7
```

## Error ที่พบบ่อย

### NICE runtime ไม่ครบ

อาการ:

```text
NICE Player runtime is not ready
missing DLL...
```

วิธีแก้:

- ตรวจ folder `C:\Program Files (x86)\NICE Systems\NICE Player Release 6`
- ตรวจ DLL ตามรายการ health check
- อย่า copy เฉพาะ DLL บางตัวถ้า dependency อื่นไม่ครบ

### รันผิด bitness

อาการ:

```text
This script must be run with 32-bit Windows PowerShell
```

วิธีแก้:

ใช้:

```text
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe
```

ไม่ใช่:

```text
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
```

### Output WAV ว่าง

อาการ:

```text
WaveController produced an empty WAV
```

สาเหตุที่เป็นไปได้:

- NMF ไม่สมบูรณ์
- NICE runtime อ่านไฟล์ไม่ได้
- permission temp/output path มีปัญหา
- DLL dependency บางตัวโหลดไม่ครบ

## สรุปสำหรับทีม Dev

สำหรับระบบจริงให้ใช้แนวทางนี้:

```text
POST .nmf -> /api/convert?engine=dotnet -> receive WAV
```

หรือถ้าเรียกจาก Python โดยตรง:

```text
convert_file(input_nmf, output_wav, engine="dotnet")
```

ไม่ควร integrate กับ path เดิม `NmfToVox PCM_A_LAW` สำหรับงานจริง เพราะไม่ตรงกับ NICE Player Save WAV ในทุกไฟล์

## Checklist ก่อนนำขึ้นระบบ

- ติดตั้ง NICE Player Release 6 บน server
- `GET /api/health` ต้องได้ `ok: true`
- `dotnetReady: true`
- required DLL ทุกตัวเป็น `exists: true`
- ทดสอบ convert ด้วยไฟล์ตัวอย่างจริง
- ตรวจ `X-NMF-duration`, `X-NMF-engine`, `X-NMF-convert-ms`
- จำกัด concurrent conversion
- ตั้ง cleanup temp file
- เก็บ log error พร้อมชื่อไฟล์และ convert time
