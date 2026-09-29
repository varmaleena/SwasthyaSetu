FROM python:3.12.10-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd -m app && chown -R app:app /app
USER app
ENV APP_ENV=demo
CMD ["sh", "-c", "uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
