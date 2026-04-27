FROM python:3.11-slim

# ตั้งค่า Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Bangkok

WORKDIR /app

# ติดตั้ง dependencies ของระบบที่จำเป็น (เช่น สำหรับ PostgreSQL) และ timezone data
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements และ install
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source code
COPY . /app/

# Command เริ่มต้น (จะถูก override ด้วย docker-compose ได้)
CMD ["python", "manage.py", "runserver", "0.0.0.0:6001"]
