#!/bin/bash
# ============================================================
#  SMART AI IoT - Update/Redeploy Script
#  Jalankan setelah push kode baru ke VPS
#  Usage: sudo bash deploy/update.sh
# ============================================================

set -e

APP_NAME="smart-aiot"
APP_DIR="/home/$APP_NAME/backend"
APP_USER="smart-aiot"

echo "=========================================="
echo "  Updating SMART AI IoT Backend"
echo "=========================================="

# 1. Pull kode terbaru (jika pakai git)
echo "[1/4] Pulling latest code..."
if [ -d "$APP_DIR/.git" ]; then
    su - "$APP_USER" -c "cd $APP_DIR && git pull"
else
    echo "Not a git repo. Pastikan file sudah di-upload manual."
fi

# 2. Update dependencies
echo "[2/4] Updating Python dependencies..."
su - "$APP_USER" -c "
    cd $APP_DIR
    source venv/bin/activate
    pip install -r requirements.txt --quiet
"

# 3. Run database migrations
echo "[3/4] Running database migrations..."
su - "$APP_USER" -c "
    cd $APP_DIR
    source venv/bin/activate
    alembic upgrade head
"

# 4. Restart service
echo "[4/4] Restarting service..."
systemctl restart "$APP_NAME"

# Tunggu 3 detik lalu cek status
sleep 3
if systemctl is-active --quiet "$APP_NAME"; then
    echo ""
    echo "Update berhasil! Backend berjalan."
    echo "Cek log: sudo journalctl -u ${APP_NAME} -f"
else
    echo ""
    echo "GAGAL! Backend tidak bisa start."
    echo "Lihat error: sudo journalctl -u ${APP_NAME} --no-pager -n 50"
fi
