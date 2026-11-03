FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    RUMBU_DB=/app/data/rumbu.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data /app/static/audio /app/static/recordings \
    && useradd --create-home rumbu && chown -R rumbu /app
USER rumbu

EXPOSE 8000

# One worker keeps SQLite and the background SMS/airtime threads in one process;
# threads let it serve several Africa's Talking callbacks at once.
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 60
