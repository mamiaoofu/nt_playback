# เอกสารสรุปการแก้ไขและเพิ่มไฟล์ (การย้ายระบบ Configuration ไปยัง Database)

เอกสารฉบับนี้สรุปรายการไฟล์ที่มีการแก้ไขและเพิ่มใหม่ในการปรับปรุงระบบดึงค่า Configuration (Active Directory, Network Share, Mail Settings) จากเดิมที่อ่านจาก `.env` มาดึงจาก Database แทน พร้อมทั้งเข้ารหัสข้อมูลสำคัญด้วย AES-256-GCM

---

## 1. ไฟล์ที่เพิ่มใหม่ (New Files)

### 📂 [helpers.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/helpers.py)
- **คำอธิบาย**: เป็นไฟล์ Helper ของระบบ Setting ทำหน้าที่สร้างฟังก์ชันในการดึงข้อมูลการตั้งค่าจากโมเดลในฐานข้อมูลขึ้นมาใช้งาน ประกอบด้วย:
  - `get_ad_settings()`: ดึงค่า Active Directory
  - `get_network_share_settings()`: ดึงค่า Network Share (SMB)
  - `get_mail_settings()`: ดึงค่า SMTP Mail
- **Fallback Logic**: หากในฐานข้อมูลยังไม่มีข้อมูลตั้งค่า หรือเกิดข้อผิดพลาดในการดึงข้อมูล ฟังก์ชันเหล่านี้จะดึงค่าจากไฟล์ `.env` เดิม (ผ่าน Django settings) มาใช้งานชั่วคราวโดยอัตโนมัติ เพื่อป้องกันไม่ให้ระบบหยุดทำงาน

### 📂 [email_backend.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/email_backend.py)
- **คำอธิบาย**: สร้าง Custom Email Backend คลาสชื่อ `DbEmailBackend` ซึ่งสืบทอดมาจากคลาสส่งเมลพื้นฐานของ Django (`SmtpEmailBackend`)
- **การทำงาน**: เมื่อระบบมีการส่งเมล คลาสนี้จะถูกเรียกใช้งานเพื่อเข้าไปอ่านข้อมูลการตั้งค่า SMTP (เช่น Host, Port, TLS, User, Password) จาก Database โดยตรงแบบ Real-time (พร้อมถอดรหัสผ่านด้วยคีย์ AES) ทำให้ระบบส่งเมลเปลี่ยนแปลงค่าได้ทันทีโดยไม่ต้อง Restart เซิร์ฟเวอร์

### 📂 [0002_populate_settings.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/migrations/0002_populate_settings.py)
- **คำอธิบาย**: ไฟล์ Data Migration สำหรับการย้ายข้อมูลและสร้างชุดข้อมูลเริ่มต้น (Data Seeding)
- **การทำงาน**: เมื่อรันคำสั่ง `python manage.py migrate` สคริปต์นี้จะอ่านค่าการตั้งค่า Active Directory, Network Share และ Mail Settings ที่ระบุไว้ในไฟล์ `.env` เดิมมาเข้ากระบวนการเข้ารหัสผ่าน (Password) ด้วยคีย์ AES-256-GCM ก่อนจะนำไปเซฟลงตารางในฐานข้อมูลเป็นเรคคอร์ดเริ่มต้น (ID=1) เพื่อช่วยให้ผู้ใช้ไม่ต้องกรอกข้อมูลใหม่ทั้งหมดเมื่อย้ายระบบ

---

## 2. ไฟล์ที่มีการแก้ไข (Modified Files)

### 📂 [models.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/models.py)
- **คำอธิบาย**: เพิ่มการประกาศคลาสโมเดลเพื่อใช้เก็บตารางตั้งค่าในฐานข้อมูล ได้แก่:
  - `ActiveDirectorySetting` (ตาราง `tb_setting_active_directory`)
  - `NetworkShareSetting` (ตาราง `tb_setting_network_share`)
  - `MailSetting` (ตาราง `tb_setting_mail`)
- **ความปลอดภัย**: ภายในโมเดลมีฟังก์ชัน `get_password()` และ `set_password()` ที่เรียกใช้งาน `smb_crypto` ในการเข้ารหัสและถอดรหัสผ่านด้วยอัลกอริทึม **AES-256-GCM** โดยอัตโนมัติเมื่อมีการบันทึกหรือดึงข้อมูลผ่านโมเดล

### 📂 [views.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/views.py)
- **คำอธิบาย**: เพิ่มฟังก์ชัน API endpoints 3 ตัวสำหรับรับ-ส่งข้อมูลระหว่าง Frontend และ Database:
  - `ApiActiveDirectorySetting`: ดึงและบันทึกข้อมูล Active Directory
  - `ApiNetworkShareSetting`: ดึงและบันทึกข้อมูล Network Share
  - `ApiMailSetting`: ดึงและบันทึกข้อมูล Mail Settings
- **การป้องกันข้อมูลรั่วไหล**: ข้อมูลรหัสผ่าน (Password) ในส่วนของข้อมูลดึง (GET) จะถูกแปลงเป็นสตริง `******` เสมอ เพื่อความปลอดภัย และรองรับการเซฟข้ามหากข้อมูลที่ส่งมาไม่ถูกเปลี่ยนแปลง

### 📂 [urls.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/urls.py)
- **คำอธิบาย**: ลงทะเบียน Path URL ใหม่เพื่อให้ฝั่ง Frontend ยิง API เข้ามาจัดการตั้งค่าได้แก่:
  - `api/setting/active-directory/`
  - `api/setting/network-share/`
  - `api/setting/mail/`

### 📂 [settings.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/config/settings.py)
- **คำอธิบาย**: แก้ไขการตั้งค่าระบบส่งอีเมลให้เปลี่ยนมาใช้คลาส `DbEmailBackend` ที่สร้างขึ้นใหม่:
  - `EMAIL_BACKEND = 'apps.setting.email_backend.DbEmailBackend'`

### 📂 [ad_backend.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/core/utils/ad_backend.py)
- **คำอธิบาย**: ปรับปรุงหน้าล็อกอินผ่าน Active Directory ให้หันมาดึงค่า Host และ Domain จาก Database ผ่านฟังก์ชัน `get_ad_settings()` แทนการดึงจาก Django Settings (`.env`) โดยตรง

### 📂 [views.py (User Management)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/user_management/views.py)
- **คำอธิบาย**: อัปเดตฟังก์ชันเชื่อมต่อ AD ในไฟล์ตัวจัดการผู้ใช้ ได้แก่ `sync_ad_accounts`, `ApiGetUSerProfile` และ `ApiGetAdUsers` ให้เปลี่ยนมาใช้การดึงข้อมูลและรหัสผ่านจากฐานข้อมูลด้วย Helper `get_ad_settings()`

### 📂 [views.py (Home)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/home/views.py)
- **คำอธิบาย**:
  - เปลี่ยนแปลงหน้าเล่นและดาวน์โหลดไฟล์เสียง (`ApiProxyAudio` และฟังก์ชันดาวน์โหลดไฟล์) ให้ดึงที่ตั้งและรหัสผ่านเชื่อมต่อ SMB จากโมเดลฐานข้อมูลผ่าน `get_network_share_settings()`
  - อัปเดตฟังก์ชันสำหรับสร้างการส่งอีเมลแชร์ไฟล์เสียง ให้ดึงอีเมลผู้ส่ง (`from_email`) ผ่าน `get_mail_settings()`

---

## 3. ไฟล์การตั้งค่าและส่วนติดต่อผู้ใช้ (Frontend & API Paths)

### 📂 [paths.js](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/api/paths.js)
- **คำอธิบาย**: ประกาศตัวแปรพาธ API ใหม่ 3 ตัวเพื่อให้ Frontend เรียกใช้สอดคล้องกับฝั่ง Backend:
  - `API_ACTIVE_DIRECTORY_CONFIG`
  - `API_NETWORK_SHARE_CONFIG`
  - `API_MAIL_SETTINGS_CONFIG`

### 📂 [ActiveDirectoryConfig.vue](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/views/ActiveDirectoryConfig.vue)
- **คำอธิบาย**: เพิ่มคำสั่ง `onMounted` เพื่อดึงข้อมูลการตั้งค่า AD ปัจจุบันมาใส่ในฟอร์มเมื่อหน้าจอแสดงผล และเขียนฟังก์ชัน `saveChanges` ในการส่งข้อมูลกลับไปเก็บยังฐานข้อมูลพร้อมระบบแจ้งเตือนผลลัพธ์ (Toast alert)

### 📂 [NetworkShareConfig.vue](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/views/NetworkShareConfig.vue)
- **คำอธิบาย**: ใส่ส่วนการดึงข้อมูลและบันทึกการตั้งค่า SMB Share ผ่าน API พร้อมแจ้งเตือนผลลัพธ์การทำงานอย่างเหมาะสม

### 📂 [MailSettingsConfig.vue](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/views/MailSettingsConfig.vue)
- **คำอธิบาย**: ใส่ส่วนการเชื่อมโยงข้อมูล SMTP Mail (GET/POST) พร้อมการตอบสนองเมื่อผู้ใช้แก้ไขข้อมูลเสร็จสิ้น
