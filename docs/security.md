# ความปลอดภัยของโปรเจค (สรุป)

## ภาพรวม

เอกสารนี้สรุปมาตรการด้านความปลอดภัยที่นำไปใช้ในโปรเจค รวมทั้งการจัดการ token/session, การป้องกัน XSS/CSRF, การตั้งค่า production-safe ของ Django 

## การยืนยันตัวตนและ token
- ใช้ JWT แบบ Access + Refresh (SimpleJWT)
- `ACCESS_TOKEN_LIFETIME`: สั้น (30 นาที)
- `REFRESH_TOKEN_LIFETIME`: วัน (1 วัน)
- `ROTATE_REFRESH_TOKENS` และ `BLACKLIST_AFTER_ROTATION` ถูกใช้เพื่อให้ refresh token เป็นแบบหมุนและสามารถ blacklist ได้
  
เพิ่มเติมคำอธิบายค่าที่สำคัญ:

- `ACCESS_TOKEN_LIFETIME` — เวลาที่ access token มีผล (duration)
  - ความหมาย: เวลาที่ access token (ใช้เรียก API โดยตรง) จะยังถือว่า valid ก่อนที่จะหมดอายุ (`exp` claim)
  - ผลกระทบ: ค่าที่สั้น (ตัวอย่าง: นาที) ปรับปรุงความปลอดภัยเพราะหาก token ถูกขโมยจะใช้ได้น้อยลง แต่จะเพิ่มจำนวนครั้งที่ client ต้องใช้ refresh เพื่อขอ token ใหม่ (UX กลางๆ)
  - ข้อสำคัญ: access token เป็น stateless โดยทั่วไป จึงไม่สามารถ "revoke" ได้ทันทีจากฝั่ง server เว้นแต่จะเก็บสถานะ (denylist) เพิ่มเติม

- `REFRESH_TOKEN_LIFETIME` — เวลาที่ refresh token มีผล
  - ความหมาย: เวลาที่ refresh token (ใช้ขอ access ใหม่) ยังคงใช้งานได้
  - ผลกระทบ: ค่านานช่วยให้ผู้ใช้ไม่ต้องล็อกอินบ่อย แต่ถ้า refresh ถูกขโมย ผู้โจมตีอาจขอ access ใหม่ได้จนกว่าจะหมดอายุหรือถูก blacklist
  - คำแนะนำ: เก็บ refresh เป็น HttpOnly cookie และตั้งค่าให้น้อยพอดี เช่น วันหรือหลายวัน ขึ้นกับนโยบายความปลอดภัย

- `ROTATE_REFRESH_TOKENS` — หมุน (rotate) refresh token ทุกครั้งที่ใช้
  - ความหมาย: เมื่อ client ใช้ refresh token เพื่อขอ access ใหม่ ระบบจะออก refresh token ใหม่พร้อมกับ access ใหม่ (เปลี่ยนค่า refresh ที่ client ได้รับ)
  - ผลกระทบ: ลดความเสี่ยงจากการ replay (reuse) ของ refresh token เก่า เพราะ token ใหม่ออกทุกครั้ง
  - ต้องทำงานร่วมกับ `BLACKLIST_AFTER_ROTATION` เพื่อให้มีผลเต็มที่

- `BLACKLIST_AFTER_ROTATION` — blacklist refresh token เก่าเมื่อมีการหมุน
  - ความหมาย: เมื่อเปิดและใช้ร่วมกับ `ROTATE_REFRESH_TOKENS` ตัว refresh token เก่าจะถูกใส่ใน blacklist (ตาราง `BlacklistedToken`) เพื่อป้องกันการนำกลับมาใช้ซ้ำ
  - ผลกระทบ: ป้องกัน attacker ใช้ token เก่าหลังจาก token ถูก rotate แต่ต้องมี `rest_framework_simplejwt.token_blacklist` ติดตั้งและใช้งาน

หมายเหตุสำคัญเกี่ยวกับการยกเลิก (revocation):
- การ blacklist refresh token ป้องกันไม่ให้ขอ access token ใหม่ แต่จะไม่ยกเลิก access token ที่ออกแล้ว (access token ยัง valid จนกว่าจะถึง `exp`) — หากต้องการยกเลิก access ทันที ต้องมีกลไก server-side เพิ่มเติม เช่นเก็บ denylist ของ `jti` ของ access token และตรวจสอบทุก request


## การเก็บ token (ลดความเสี่ยง XSS)
- **Refresh token**: ถูกตั้งเป็น HttpOnly cookie โดย backend (frontend ไม่สามารถเข้าถึงผ่าน JS)
- **Access token**: เก็บในหน่วยความจำของหน้า (in-memory) เท่านั้น — ไม่เก็บใน `localStorage` หรือ `sessionStorage`

## Logout และ token invalidation
- เพิ่ม endpoint `/api/logout/` ที่:
  - blacklist refresh token ที่ได้รับหรือทั้งหมดของผู้ใช้เป็น fallback
  - ลบ session ฝั่งเซิร์ฟเวอร์ (พยายามลบโดย `session_key` ก่อนเรียก `django_logout()`)
  - ส่ง `Set-Cookie` หมดอายุ (Max-Age=0 / Expires epoch) เป็น fallback เพื่อพยายามลบคุกกี้บนเบราว์เซอร์

## การจัดการ Session ฝั่งเซิร์ฟเวอร์
- เมื่อผู้ใช้ล็อกอิน จะลบ session อื่น ๆ ของผู้ใช้เพื่อป้องกัน concurrent sessions (ตามนโยบายของแอพถ้าต้องการ)
- เมื่อเปลี่ยนรหัสผ่านหรือรีเซ็ตรหัสผ่าน จะ blacklist outstanding tokens และลบ session ที่เกี่ยวข้อง

## การตั้งค่า Django ที่สำคัญ (dev vs production)
- `SECRET_KEY` ต้องมาจาก environment (fail-fast ถ้าไม่กำหนด)
- `DEBUG` ถูกควบคุมด้วย env; ใน production ต้องปิด (`False`)
- ค่าคุกกี้ความปลอดภัย (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`) ถูกตั้งค่าให้ปลอดภัยโดยดีฟอลต์ใน production — แต่สามารถปิดสำหรับ dev
- หากใช้ TLS-terminator (nginx) ให้ตั้ง `SECURE_PROXY_SSL_HEADER` และให้ nginx ส่ง `X-Forwarded-Proto: https`
- เพิ่ม `CSRF_TRUSTED_ORIGINS` ให้ครอบคลุม origin ที่ใช้จริง เช่น `https://localhost` เมื่อทดสอบด้วย HTTPS

## การแฮชรหัสผ่าน
- เป็น `Argon2`

## ปัญหาที่พบและแนวทางแก้ไขที่ทำแล้ว

## ไฟล์ที่เกี่ยวข้อง (สำคัญ)
- `backend/config/settings.py` — การตั้งค่า security/secret/jwt
- `backend/apps/login/views.py` — login + `api_logout` (blacklist + session deletion + cookie deletion)
- `backend/apps/user_management/views.py` — change/reset password token invalidation
- `frontend/src/stores/auth.store.js` — เก็บ access token ในหน่วยความจำและเรียก logout ด้วย `credentials: 'include'`

---