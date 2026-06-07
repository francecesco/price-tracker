FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt && \
    playwright install --with-deps chromium

COPY src/ ./src/

CMD ["python", "src/main.py"]
