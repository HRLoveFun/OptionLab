#!/usr/bin/env bash
# =============================================================================
# OptionLab — Oracle Cloud Always-Free deployment bootstrap
# Run as root on a FRESH Ubuntu 24.04 Always-Free VM:
#     sudo bash deploy/setup_oracle.sh
#
# What it does:
#   1. installs Python 3.12 + git + build tools
#   2. creates an unprivileged 'optionlab' user
#   3. clones the repo to /opt/optionlab
#   4. builds a venv and installs requirements.txt + gunicorn
#   5. writes /opt/optionlab/.env (DB on a persistent dir, Agg backend)
#   6. installs & starts the systemd unit (always-on, no sleep)
#
# NOTE: Oracle free tier gives a PERSISTENT boot volume, so data survives
# reboots by default. For extra safety you can attach a separate Block Volume
# and mount it at /data, then edit DATA_DIR below. See the deployment guide.
# =============================================================================
set -euo pipefail

APP_USER=optionlab
APP_HOME=/opt/optionlab
DATA_DIR="$APP_HOME/data"          # change to /data if you mount a Block Volume
REPO_URL=https://github.com/HRLoveFun/OptionLab.git
BRANCH=main

echo "==> apt update + base deps"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.12 python3.12-venv python3.12-dev git curl build-essential

echo "==> app user"
id -u "$APP_USER" &>/dev/null || useradd -m -s /bin/bash "$APP_USER"

# Safety net: AMD micro shape has only 1 GB RAM; add swap so scipy/matplotlib
# installs and renders don't OOM. ARM A1 (24 GB) skips this harmlessly.
if [ "$(free -m | awk '/^Mem:/{print $2}')" -lt 2048 ]; then
    echo "==> small RAM detected — creating 2 GB swap"
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile && swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi

echo "==> data dir (persistent)"
mkdir -p "$DATA_DIR"
chown -R "$APP_USER:$APP_USER" "$DATA_DIR"

echo "==> clone repo"
rm -rf "$APP_HOME"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP_HOME"
chown -R "$APP_USER:$APP_USER" "$APP_HOME"

echo "==> venv + deps"
sudo -u "$APP_USER" bash -c "
    cd $APP_HOME
    python3.12 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    .venv/bin/pip install gunicorn
"

echo "==> .env"
cat > "$APP_HOME/.env" <<EOF
MARKET_DB_PATH=$DATA_DIR/market_data.sqlite
MPLBACKEND=Agg
PORT=5001
# yfinance from an Oracle datacenter IP is often rate-limited by Yahoo (429 /
# empty frames). If first loads show no data, set a proxy here, e.g.:
# YF_PROXY=http://your-proxy-host:1087
# Optional: keep the DB fresh automatically (needs APScheduler, lazy-imported).
# AUTO_UPDATE_TICKERS=AAPL,MSFT,SPY
EOF
chown "$APP_USER:$APP_USER" "$APP_HOME/.env"

echo "==> systemd unit"
cp "$APP_HOME/deploy/optionlab.service" /etc/systemd/system/optionlab.service
# %i templated instance -> port 5001
systemctl daemon-reload
systemctl enable --now optionlab@5001.service

echo "==> DONE. Verify:"
echo "    systemctl status optionlab@5001"
echo "    journalctl -u optionlab@5001 -f"
echo "    curl -sS localhost:5001 | head"
