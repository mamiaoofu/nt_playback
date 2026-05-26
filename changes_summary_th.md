# เอกสารสรุปการปรับปรุงระบบสิทธิ์การใช้งาน (ID-Based Permissions)

เอกสารฉบับนี้อธิบายรายละเอียดเกี่ยวกับไฟล์ที่ถูกเพิ่มใหม่และไฟล์ที่ถูกแก้ไขทั้งหมดในส่วนของระบบสิทธิ์การใช้งาน (Permissions System) ทั้งฝั่ง Backend (Django) และ Frontend (Vue) จากเดิมที่ระบุสิทธิ์ด้วย **ชื่อข้อความ (String Name)** มาเป็น **รหัสตัวเลข (Database ID)** เพื่อความมั่นคงและป้องกันปัญหาการเปลี่ยนแปลงชื่อการแสดงผลในอนาคต

---

## 📂 รายการไฟล์ที่เพิ่มใหม่ (New Files)

### 1. ฝั่ง Backend
#### 📄 [permission_ids.py](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/core/utils/permission_ids.py)
* **วัตถุประสงค์**: เป็นศูนย์รวมค่าคงที่ (Constants) ของสิทธิ์การใช้งานทั้ง 46 รายการที่เป็นตัวเลข ID ในระบบฐานข้อมูล เพื่อให้สามารถเรียกใช้งานในโค้ดฝั่ง Backend ได้อย่างเป็นระเบียบและลดการพิมพ์ค่าคงที่ผิดพลาด
* **ฟังก์ชัน / คลาสสำคัญ**:
  * `class PermissionIDs`: บรรจุตัวแปรค่าคงที่ เช่น:
    * `AUDIO_RECORDS_ACCESS = 1` (สิทธิ์ในการเข้าถึงเมนู Audio Records)
    * `PLAYBACK_AUDIO_RECORDS = 13` (สิทธิ์ในการฟังบันทึกเสียง)
    * `DOWNLOAD_AUDIO_RECORDS = 14` (สิทธิ์ในการดาวน์โหลดบันทึกเสียง)

### 2. ฝั่ง Frontend
#### 📄 [permissions.constants.js](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/stores/permissions.constants.js)
* **วัตถุประสงค์**: บรรจุค่าคงที่สิทธิ์การใช้งานเป็นตัวเลข ID ฝั่ง Frontend เพื่อใช้ในการตั้งค่าใน Routing (ไฟล์ `router/index.js`) และการเช็คสิทธิ์ในจุดต่าง ๆ
* **ตัวแปรสำคัญ**:
  * `export const PERMISSIONS`: ออบเจกต์เก็บคู่คีย์-ค่าสิทธิ์ เช่น `AUDIO_RECORDS_ACCESS: 1`, `USER_MANAGEMENT_ACCESS: 2` เพื่อลดความผิดพลาดในการเรียกใช้สิทธิ์ด้วยตัวเลขดิบ ๆ และลดปัญหา Circular Dependency (การนำเข้าไฟล์วนลูป) ระหว่าง Router กับ Auth Store

---

## 🛠️ รายการไฟล์ที่แก้ไข (Modified Files)

### 1. ระบบฐานข้อมูลและโมเดล (Database Models & Migrations)
#### 📄 [models.py (configuration)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/configuration/models.py)
* **การแก้ไข**: 
  * เพิ่มตาราง `UserPermissionType` (สำหรับประเภทกลุ่มสิทธิ์) และ `UserPermissionAction` (สำหรับรายการสิทธิ์)
  * ปรับโครงสร้างตาราง `UserPermissionDetail` โดยให้ฟิลด์ `action` และ `type` เชื่อมโยงเป็น `ForeignKey` ไปยังตารางใหม่ แทนการใช้ฟิลด์ข้อความแบบเดิม

#### 📄 [0002_userpermissionaction_userpermissiontype_and_more.py (configuration/migrations)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/configuration/migrations/0002_userpermissionaction_userpermissiontype_and_more.py)
* **การแก้ไข**: ไฟล์ Auto-migration ของ Django เพื่อสร้างตารางใหม่และแปลงโครงสร้างข้อมูลฟิลด์ `action` และ `type` ในโมเดลสิทธิ์

#### 📄 [0003_seed_permissions.py (configuration/migrations)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/configuration/migrations/0003_seed_permissions.py)
* **การแก้ไข**: ดำเนินการลบข้อมูลสิทธิ์เก่าและจัดเก็บสิทธิ์ใหม่ที่มี ID ตายตัว (1 ถึง 46) พร้อมใส่สิทธิ์เริ่มต้นให้ 4 บทบาทหลัก (Administrator, Auditor, Operator, Ticket) รวมถึงสร้าง Stubs บทบาทผู้ใช้แบบกำหนดเอง (Custom Roles) เพื่อไม่ให้เกิดข้อผิดพลาดคีย์ต่างประเทศ และเรียกคืนข้อมูลการเข้าถึงของบัญชีต่าง ๆ จากไฟล์สำรองข้อมูล

---

### 2. ฟังก์ชันตรวจสอบสิทธิ์ฝั่ง Backend (Backend Middleware & Decorator)
#### 📄 [permissions.py (core/utils)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/core/utils/permissions.py)
* **การแก้ไข**: 
  * ปรับปรุงฟังก์ชัน `get_user_actions(user)`: ดึงข้อมูลรายการ ID สิทธิ์ของผู้ใช้นั้น ๆ ในรูปของเซตตัวเลข (`set` ของ `int`) โดยมีระบบข้ามสิทธิ์สำหรับ superuser / root user (ID: 1)
  * ปรับปรุงเดคอเรเตอร์ `@require_action(*action_ids)`: ใช้สำหรับครอบฟังก์ชัน View เพื่อระบุสิทธิ์ที่ต้องใช้ในการดำเนินการ โดยจะเปรียบเทียบเซตตัวเลข ID ของผู้ใช้เข้ากับรายการสิทธิ์ที่ต้องการ

---

### 3. คอนโทรลเลอร์ฝั่ง Backend (Backend Views)
แก้ไขไฟล์คอนโทรลเลอร์เพื่อให้รองรับสิทธิ์การตรวจสอบที่เป็นตัวเลขคงที่ของ `PermissionIDs`:
* 📄 **[views.py (configuration)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/configuration/views.py)**: ปรับปรุงการบันทึกสิทธิ์บทบาทและเรียกดูสิทธิ์เป็นตัวเลข และเปลี่ยนการตรวจเดคอเรเตอร์ครอบ View
* 📄 **[views.py (user_management)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/user_management/views.py)**: ปรับสิทธิ์ในการบันทึก / แก้ไข / ลบผู้ใช้ให้ตรวจสอบด้วยรหัส ID
* 📄 **[views.py (home)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/home/views.py)**: อัปเดตเดคอเรเตอร์ `@require_action` ของฟังก์ชันเรียกไฟล์เสียง การฟัง และดาวน์โหลด
* 📄 **[views.py (setting)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/setting/views.py)**: อัปเดตเดคอเรเตอร์และโครงสร้างสิทธิ์
* 📄 **[views.py (ticket_history)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/ticket_history/views.py)**: อัปเดตสิทธิ์การดูประวัติคำขอแชร์ไฟล์
* 📄 **[views.py (log_user)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/backend/apps/log_user/views.py)**: อัปเดตสิทธิ์การดูประวัติการบันทึกการใช้งานระบบ

---

### 4. ระบบ Routing และ Store ฝั่ง Frontend (Frontend Routing & Auth Store)
#### 📄 [auth.store.js](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/stores/auth.store.js)
* **การแก้ไข**:
  * ลบคำสั่ง `import router from '../router'` ออกจากส่วนหัวของไฟล์ เพื่อแก้ปัญหา **Circular Dependency** (การโหลดไฟล์วนลูป) ระหว่าง `auth.store` และ `router`
  * เพิ่มฟังก์ชัน `export function setRouter(r)`: ใช้เพื่อให้ไฟล์ `main.js` ส่งออบเจกต์ `router` เข้ามาเก็บที่ตัวแปรภายในเพื่อใช้ในการสั่งเปลี่ยนเส้นทาง (เช่น `router.push('/login')`) ตอนทำ Logout หรือ Redirect
  * เพิ่ม `permissionNameToIdMap`: แผนผังสำหรับแปลงสิทธิ์ข้อความแบบเก่า (เช่น `'User Management'`) ให้เป็นตัวเลข ID อัตโนมัติ เพื่อให้คอมโพเนนต์อื่น ๆ ที่ยังใช้โค้ดแบบเก่าไม่มีปัญหาการทำงาน (Backward Compatibility)
  * ปรับปรุงฟังก์ชัน `hasPermission(actionId)`: เปรียบเทียบข้อมูลสิทธิ์เป็นตัวเลข และมีระบบตรวจสอบ String เพื่อแปลงเป็นตัวเลข ID โดยอัตโนมัติ

#### 📄 [index.js (router)](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/router/index.js)
* **การแก้ไข**:
  * ปรับปรุงค่า `meta.permission` ของทุกหน้าให้ใช้รหัสสิทธิ์จาก `PERMISSIONS` เช่นเปลี่ยนจาก `'Audio Records'` เป็น `PERMISSIONS.AUDIO_RECORDS_ACCESS` (1)
  * ย้ายคำสั่ง `import { PERMISSIONS }` ให้ไปดึงจากไฟล์ `permissions.constants.js` แทนการนำเข้าจาก `auth.store` เพื่อหลีกเลี่ยงข้อผิดพลาด Temporal Dead Zone (ข้อผิดพลาดการเข้าถึงตัวแปรก่อนประกาศ)

#### 📄 [main.js](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/main.js)
* **การแก้ไข**: นำเข้าฟังก์ชัน `setRouter` และเรียกใช้งานโดยส่งออบเจกต์ `router` เข้าไปบันทึกในระบบของ `auth.store` ทันทีหลังจากการสร้างแอปเสร็จสิ้น: `setRouter(router)`

---

### 5. หน้าตั้งค่าและจัดการผู้ใช้ฝั่ง Frontend
#### 📄 [ModalConfiguration.vue](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/components/ModalConfiguration.vue)
* **การแก้ไข**: 
  * ปรับปรุงความสอดคล้องของชื่อคีย์ประเภทและแผนผังพึ่งพาสิทธิ์ (`dependencyMap`) ในการตรวจสอบความพึ่งพากันระหว่างสิทธิ์เข้าใช้งานกับสิทธิ์ดำเนินการเชิงลึก
  * ปรับปรุงกระบวนการดึงข้อมูลสิทธิ์และบันทึกกลุ่มสิทธิ์บทบาทผู้ใช้ให้ทำงานเป็นตัวเลข ID

#### 📄 [useUserForm.js](file:///c:/Users/ACER/Documents/GitHub/nt_playback/frontend/src/composables/useUserForm.js)
* **การแก้ไข**: อัปเดตแผนผังสิทธิ์พึ่งพากัน (`dependencyMap`) และป้ายกลุ่มการแบ่งหมวดสิทธิ์การแสดงผลในหน้าสร้างผู้ใช้ใหม่เพื่อให้เข้ากันได้ดีกับรูปแบบตารางใหม่ของระบบฐานข้อมูลสิทธิ์
