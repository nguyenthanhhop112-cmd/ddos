FROM python:3.9-slim

WORKDIR /app
COPY . .

# Cài đặt các thư viện cần thiết
RUN pip install --no-cache-dir telethon locust

# Chạy bot
CMD ["python", "bot.py"]
