FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# تثبيت المتصفح داخل الدوكر
RUN playwright install chromium

CMD ["python", "id.py"]