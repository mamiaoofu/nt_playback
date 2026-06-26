# ข้อมูลจำเพาะการเก็บ Log ของระบบ Data Retention (Retention Log Specification)

---

## 1. ปรับการเก็บ Log ในฝั่ง Schedule Retention (ตารางทำงานลบอัตโนมัติ)

### เมื่อกด Save and Run:
- **Action:** `Save and Run Schedule Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end} | {Once หรือ Recurrence} | {Indexes หรือ Indexes & Voice Files}`

### เมื่อกด Stop (ปุ่มหยุดทำงาน):
- **Action:** `Stop Schedule Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end}`

### เมื่อกด Run (ปุ่มเริ่มทำงาน / ปุ่มเปิดตารางใหม่):
- **Action:** `Run Schedule Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end} | {Once หรือ Recurrence} | {Indexes หรือ Indexes & Voice Files}`

### เมื่อถึงรอบเวลาการประมวลผลลบชั่วคราว (Soft Delete):
- **Action:** `Complete Soft Delete Schedule Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end} | Indexes`

### เมื่อข้อมูลหมดอายุและถูกลบจริงถาวร (Permanent Delete):
- **Action:** `Complete Delete Schedule Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end} | {Indexes หรือ Indexes & Voice Files}`

### เมื่อกด Restore (กู้คืนข้อมูล):
- **Action:** `Restore Data Schedule Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end} | Indexes`

---

## 2. ปรับการเก็บ Log ในฝั่ง Immediately Retention (สั่งลบทันทีแบบแมนนวล)

### เมื่อกด Save and Run (ลบชั่วคราวทันที):
- **Action:** `Complete Soft Delete Immediately Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {start - end} | Indexes`

### เมื่อข้อมูลหมดอายุและถูกลบจริงถาวร (Permanent Delete):
- **Action:** `Complete Delete Immediately Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {over xx days/months/years หรือ start - end} | {Indexes หรือ Indexes & Voice Files}`

### เมื่อกด Restore (กู้คืนข้อมูล):
- **Action:** `Restore Data Immediately Retention`
- **Detail:** `Retention ID : {เลข retention id} | Retention Period : {start - end} | Indexes`
