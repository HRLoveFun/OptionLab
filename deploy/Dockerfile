# Optional: container build for Oracle (or any host with Docker).
# The recommended Oracle path is the systemd setup (deploy/setup_oracle.sh);
# use this only if you prefer running the app as a container.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    MARKET_DB_PATH=/data/market_data.sqlite \
    PORT=5001

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn

COPY . .

# Persist the SQLite DB across container restarts by mounting a volume at /data.
VOLUME ["/data"]
EXPOSE 5001

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5001", "--workers", "2", "--threads", "4", "--timeout", "120"]
