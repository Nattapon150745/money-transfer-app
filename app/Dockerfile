# ใช้ Python image เป็นฐาน
FROM python:3.9-slim

# ตั้งค่าโฟลเดอร์ทำงานภายใน container
WORKDIR /app

# คัดลอกไฟล์ที่จำเป็นไปยัง container
COPY requirements.txt requirements.txt

# ติดตั้ง dependencies
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอก source code ไปที่ container
COPY . .

# กำหนดให้ Flask ทำงานเมื่อ container เริ่มต้น
CMD ["flask", "run", "--host=0.0.0.0"]
