# NICE NMF Integration Guide (.NET SaveMgr Mode)

อัปเดตล่าสุด: 2026-07-03

เอกสารฉบับนี้อธิบายรายละเอียดเกี่ยวกับระบบสตรีมและเล่นไฟล์เสียง NICE `.nmf` (NMF Web Playback) ผ่านเว็บเบราว์เซอร์ โดยใช้เทคโนโลยี **.NET SaveMgr (WaveController)** ของ NICE Player Release 6 เพื่อดึงและถอดรหัสสัญญาณเสียงให้มีความถูกต้องสูงสุด (เทียบเท่ากับการกด Save WAV บนโปรแกรมเล่นเสียง NICE Player โดยตรง)

---

## 📊 ผังแสดงตรรกะการทำงาน (Program Logic Flowchart)

นี่คือผังการทำงานหลัก (Flowchart) ของระบบเล่นเสียง NMF ที่แสดงการตัดสินใจในแต่ละเงื่อนไข (ตามรูปแบบมาตรฐานที่คุณแนะนำ):

```mermaid
flowchart TD
    Start([เริ่ม: ผู้ใช้กดปุ่มเล่นเสียง NMF บนหน้าเว็บ]) --> Request[หลังบ้าน Django รับคำขอสตรีมเสียง]
    Request --> CheckNmf{เป็นไฟล์ตระกูล .nmf?}
    
    CheckNmf --ไม่ใช่--> NormalStream[สตรีมไฟล์เสียงแบบปกติ / แปลงฟอร์แมตทั่วไป]
    CheckNmf --ใช่--> CheckEnv{สภาพแวดล้อมที่รัน Django?}
    
    CheckEnv --Docker (Linux Container)--> CallAPI[ส่งคำขอ POST ไปยัง NiceNmfService ที่เครื่อง Host พอร์ต 10797]
    CheckEnv --Windows Host (Direct Running)--> RunLocal[รัน NiceNmfConverter.exe บนเครื่องโดยตรง]
    
    CallAPI --> ServiceConvert[NiceNmfService เรียกใช้ NiceNmfConverter.exe]
    
    RunLocal --> ConvertFlow[ใช้ LocalPlaylist & WaveController แปลงไฟล์เป็น WAV]
    ServiceConvert --> ConvertFlow
    
    ConvertFlow --> CheckWav{แปลงไฟล์สำเร็จและได้ WAV ที่ไม่ว่าง?}
    
    CheckWav --ไม่สำเร็จ/เงียบ--> Error([แจ้งเตือนข้อผิดพลาด: ไฟล์ไม่สมบูรณ์หรือไม่รองรับ])
    CheckWav --สำเร็จ--> Normalize[เร่งระดับเสียงและทำ Normalization ด้วย Python]
    
    Normalize --> Stream[ส่งข้อมูลไฟล์ WAV กลับไปสตรีมที่เบราว์เซอร์]
    Stream --> Play([เบราว์เซอร์เล่นเสียงและวาดคลื่น Waveform])
```

---

## 🏗️ สถาปัตยกรรมระบบ (System Architecture)

เนื่องจากไลบรารีของ NICE Player เป็น **Windows Native (32-bit)** แต่ระบบหลังบ้านหลักของโปรเจครันอยู่ใน **Linux Docker Container** เราจึงแยกส่วนการถอดรหัสออกมาเป็น **Microservice (NiceNmfService)** รันอยู่เบื้องหลังบน Windows Host

```mermaid
graph TD
    subgraph Browser ["Web Browser (Vue.js Client)"]
        UI["AudioPlayer.vue Modal"]
    end

    subgraph LinuxDocker ["Linux Docker Container"]
        Backend["Django Daphne Server"]
        SMB["SMB client (pysmb)"]
    end

    subgraph WindowsHost ["Windows Host Machine"]
        Service["NiceNmfService (Python Server, Port 10797)"]
        Converter["NiceNmfConverter.exe (C# 32-bit)"]
        NICE_DLL["NICE Player Release 6 DLLs"]
        LocalFiles["SMB Shared Folder (NMF Files)"]
    end

    UI -->|1. Request Audio Playback| Backend
    Backend -->|2. Pull NMF File| SMB
    SMB -->|3. Read File Bytes| LocalFiles
    Backend -->|4. HTTP POST /api/convert| Service
    Service -->|5. Run process| Converter
    Converter -->|6. Load DLLs & Convert| NICE_DLL
    Converter -->|7. Output WAV| Service
    Service -->|8. Apply Normalization| Service
    Service -->|9. Send WAV back| Backend
    Backend -->|10. Stream Audio Response| UI
```

---

## 🔒 ความปลอดภัยของระบบและการจัดเก็บไฟล์เสียง (Security & SMB Privacy)

ระบบจัดเก็บและถอดรหัสไฟล์เสียงนี้มีลักษณะการออกแบบเชิงความปลอดภัยแบบ **Backend-Proxy Gate** ซึ่งเป็นแนวทางมาตรฐานความปลอดภัยระดับสูง มีจุดเด่นดังนี้:

### 1. การซ่อนโฟลเดอร์ต้นทาง (Folder Obfuscation)
* **ผู้ใช้ฝั่ง Client จะมองไม่เห็นโฟลเดอร์ต้นทาง 100%**: ผู้ใช้ปลายทางที่ใช้งานเบราว์เซอร์จะไม่ทราบเลยว่าไฟล์เสียงจริงถูกเก็บไว้ที่ Network Path ใด (เช่น `\\NICHETEL-DOMAIN\Users\...`) หรือเก็บไว้ในเครื่อง Server ใด
* **การจำกัดสิทธิ์การเข้าถึง**: สิทธิ์การเข้าถึงโฟลเดอร์เก็บไฟล์เสียง (SMB Share) จะถูกจำกัดไว้ให้เฉพาะเครื่องหลังบ้าน Django เท่านั้น เครื่องผู้ใช้ภายนอกไม่มีสิทธิ์เข้าถึงหรือ Map Network Drive ดังกล่าวได้โดยตรง

### 2. การรักษาความลับของสิทธิ์เข้าถึง (Credential Masking)
* บัญชีผู้ใช้งานและรหัสผ่าน (Username / Password) ที่ใช้เชื่อมต่อ SMB จะถูกเก็บเป็นความลับที่ **ฝั่ง Server เท่านั้น** (อยู่ในฐานข้อมูลหลังบ้านหรือเก็บแบบเข้ารหัส) และจะไม่มีการส่งข้อมูลรหัสผ่านนี้ออกไปฝั่ง Client อย่างเด็ดขาด

### 3. วงจรชีวิตของไฟล์ชั่วคราว (Temporary File Lifecycle)
* **การทำงาน**: เมื่อผู้ใช้กดปุ่มเล่นเสียง หลังบ้าน Django จะต่อเข้าไปดึงไฟล์ผ่าน SMB นำมาเขียนลงโฟลเดอร์ Temp บนฝั่ง Server จากนั้นส่งไฟล์ Temp นี้ไปที่ API เพื่อทำการแปลงเป็น WAV 
* **การลบไฟล์ทันทีหลังส่งออก**: หลังจากส่งข้อมูลไบนารีเสียง WAV กลับไปยังหน้าเบราว์เซอร์จนจบคำขอแล้ว ตัวระบบ Django (ผ่านคลาส `RangeFileResponse.close()`) จะสั่ง **ลบไฟล์ Temp นั้นออกจากเครื่อง Server ทันที** ทำให้ไม่มีไฟล์ตกค้างสะสมอยู่ในระบบ จึงปลอดภัยจากการถูกดึงไฟล์ข้อมูลออกไปในภายหลัง

---

## 🔄 ลำดับขั้นตอนการเล่นไฟล์เสียง (Sequence Diagram)

แผนภาพแสดงขั้นตอนตั้งแต่การกดปุ่มเล่นเสียงบนหน้าเว็บเบราว์เซอร์ ไปจนถึงการสตรีมและเล่นคลื่นเสียงกลับมายังผู้ใช้:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Browser (AudioPlayer.vue)
    participant Django as Django Backend (Docker Container)
    participant SMB as Remote Storage (SMB Server)
    participant API as NiceNmfService (Windows Host)
    participant CSharp as NiceNmfConverter.exe (C#)
    participant NICE as NICE Player Release 6 DLLs

    Client->>Django: Request playback for Nice-1.nmf
    Note over Django: Check credentials & network path
    Django->>SMB: Connect and fetch Nice-1.nmf bytes
    SMB-->>Django: Return Nice-1.nmf file stream
    Django->>API: HTTP POST /api/convert (Send NMF bytes)
    Note over API: Write temp Nice-1.nmf to disk
    API->>CSharp: Execute: NiceNmfConverter.exe input.nmf output.wav PLAYER_WAV
    Note over CSharp: Set current directory to NICE Base
    CSharp->>NICE: Load assemblies: PlayMgr.dll & dependencies
    CSharp->>NICE: LocalPlaylist.Load(input.nmf, bMergeMedia: true)
    Note over CSharp: Resolve and combine streams (Agent & Customer)
    CSharp->>NICE: WaveController.Init(item, -1, SaveMediaType.AllTypes)
    CSharp->>NICE: WaveController.Save(output.wav)
    NICE-->>CSharp: Write merged PCM WAV file
    CSharp-->>API: Process exited (0 - Success)
    Note over API: Apply Dynamic Volume Normalization (Amplify)
    API-->>Django: HTTP 200 OK (Send WAV bytes + Metadata headers)
    Django-->>Client: Stream WAV audio response
    Note over Client: Clear canvas and display wave info
    Client->>Client: Decode PCM WAV using AudioContext and Play
```

---

## 🛠️ จุดเด่นและการเพิ่มประสิทธิภาพ (Optimizations)

### 1. การเปลี่ยนผ่านจาก A-Law สู่ .NET SaveMgr (WaveController)
* **ปัญหาเดิม**: การใช้ฟังก์ชันแปลงไฟล์ปกติ (`NmfToVox` แปลงเป็น `PCM_A_LAW`) จะถอดรหัสเฉพาะ Audio Stream หลัก (มักเป็นช่องของ Agent อย่างเดียว หรือไม่ก็เงียบสนิทในไฟล์ที่มีการเข้ารหัส)
* **การแก้ไขด้วย SaveMgr**: ระบบจะจำลองการโหลด Playlist และใช้ `WaveController` สั่งออกข้อมูลเป็นไฟล์เสียง WAV ซึ่งจะได้เนื้อเสียงครบถ้วนจากทุกช่องสัญญาณ (ทั้งฝั่ง Agent และ Customer) และรองรับการถอดรหัสไฟล์บันทึกเสียงที่มีความปลอดภัยสูงได้ทั้งหมด

### 2. ขจัดความล่าช้าด้วย Native C# (ลดจาก 6 วินาที เหลือต่ำกว่า 0.5 วินาที)
* **ปัญหาเดิม (PowerShell Bridge)**: การใช้สคริปต์ PowerShell (`.ps1`) เพื่อคอมไพล์ C# บนหน่วยความจำในอดีต ทำให้เสียเวลาเปิดโปรเซส PowerShell สูงถึง 5 - 7 วินาทีต่อการเล่นเสียงหนึ่งครั้ง และมักมีปัญหา **`StackOverflowException`** จาก Assembly Resolver ภายใน Windows
* **การแก้ไข**: เราพัฒนาโปรแกรม [NiceNmfConverter.exe](file:///C:/Users/ACER/Documents/GitHub/nt_playback/NiceNmfService/tools/NiceNmfConverter.exe) ขึ้นด้วยภาษา C# และคอมไพล์เป็นโปรแกรมทำงานแบบ 32-bit โดยตรง ทำให้เปิดทำงานได้อย่างทันที ปลอดภัยจากปัญหาหน่วยความจำล้น และถอดรหัสไฟล์เสร็จสิ้นภายในไม่กี่มิลลิวินาที

### 3. ระบบเร่งระดับเสียงอัจฉริยะ (Dynamic Volume Normalization)
เนื่องจากไฟล์เสียงสนทนาที่ถูกบีบอัดมักมีระดับเสียงที่เบากว่าปกติ หลังจากการแปลงไฟล์ด้วย C# เสร็จสิ้น ระบบหลังบ้าน Python จะทำการ:
* ตรวจสอบหาค่าความดังสูงสุด (Peak Amplitude) ของเสียง
* คำนวณและปรับเร่งเสียงเพิ่มโดยอัตโนมัติ (ขยายระดับเสียงขึ้นสูงสุดได้ถึง 6 เท่า) ให้ได้ความดังมาตรฐานที่ 85% ของคลื่นเสียงทั้งหมด (`Peak = 28000`)
* มีกลไกป้องกันเสียงแตก (Clipping Protection) และป้องกันการเร่งเสียงรบกวนในไฟล์เงียบสนิท (Noise Gate Protection)

---

## 🌐 รายละเอียด API บริการ (API Reference)

ตัวบริการรันด้วย Python `ThreadingHTTPServer` ที่พอร์ต **`10797`**

### 1. ตรวจสอบสถานะการเชื่อมต่อ (Health Check)
ใช้เพื่อเช็คความพร้อมการโหลดไลบรารีและเวอร์ชันของ NICE DLL
* **Endpoint**: `GET http://127.0.0.1:10797/api/health`
* **Response (JSON)**:
  ```json
  {
    "ok": true,
    "niceBase": "C:\\Program Files (x86)\\NICE Systems\\NICE Player Release 6",
    "powershell32": "C:\\Windows\\SysWOW64\\WindowsPowerShell\\v1.0\\powershell.exe",
    "dotnetConverter": "C:\\Users\\ACER\\Documents\\GitHub\\nt_playback\\NiceNmfService\\tools\\NiceNmfConverter.exe",
    "dotnetReady": true,
    "supportedEngines": ["dotnet", "powershell"],
    "requiredFiles": [
      { "name": "ERS.Common.dll", "exists": true },
      { "name": "NiceApplications.Playback.Utils.dll", "exists": true },
      { "name": "NiceApplications.Playback.PlayMgr.dll", "exists": true }
      // ... รายชื่อ DLL ตัวอื่นๆ
    ],
    "missing": []
  }
  ```

### 2. แปลงไฟล์เสียง (Convert File)
ส่งข้อมูล NMF ไบนารีเพื่อรับไฟล์เสียง WAV
* **Endpoint**: `POST http://127.0.0.1:10797/api/convert?name=recording.nmf&engine=dotnet`
* **Request Header**: `Content-Type: application/octet-stream`
* **Response Body**: ข้อมูลไบนารีไฟล์เสียงมาตรฐาน `audio/wav`
* **Response Headers (Metadata)**:
  * `X-NMF-duration`: ความยาวเสียงจริง (วินาที)
  * `X-NMF-sample-rate`: อัตราสุ่มสัญญาณ (เช่น 8000 Hz)
  * `X-NMF-convert-ms`: ระยะเวลาที่ใช้ในการแปลงไฟล์ (มิลลิวินาที)
  * `X-NMF-server-ms`: ระยะเวลารวมทั้งหมดของคำขอแปลงไฟล์
