FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY . /app

# تثبيت المكتبات
RUN pip install --no-cache-dir aiogram playwright

# تعديل هذا السطر لاستدعاء بلاي رايت عبر البايثون
RUN python3 -m playwright install chromium
RUN python3 -m playwright install-deps chromium

CMD ["python3", "id.py"]
