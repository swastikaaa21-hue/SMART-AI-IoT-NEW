#!/bin/bash
# ============================================================
#  SMART AI IoT Backend - VPS Setup Script
#  Jalankan sebagai root: sudo bash deploy/setup-vps.sh
# ============================================================

set -e

APP_NAME="smart-aiot"
APP_DIR="/home/$APP_NAME/backend"
APP_USER="smart-aiot"
PYTHON_VERSION="3.11"
DOMAIN=""  # Akan ditanya saat runtime

echo "=========================================="
echo "  SMART AI IoT - VPS Setup"
echo "=========================================="

# ── 1. Tanya domain ─────────────────────────────────────────
read -p "Masukkan domain/subdomain (contoh: api.smartaiot.com) atau kosongkan untuk IP saja: " DOMAIN
read -p "Masukkan email untuk SSL Let's Encrypt (kosongkan jika tanpa domain): " SSL_EMAIL

# ── 2. Update sistem ────────────────────────────────────────
echo "[1/8] Updating system..."
apt update && apt upgrade -y

# ── 3. Install dependencies ─────────────────────────────────
echo "[2/8] Installing system dependencies..."
apt install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    ufw \
    build-essential \
    libpq-dev

# ── 4. Buat user aplikasi ───────────────────────────────────
echo "[3/8] Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
    echo "User '$APP_USER' created."
else
    echo "User '$APP_USER' already exists."
fi

# ── 5. Setup direktori project ───────────────────────────────
echo "[4/8] Setting up project directory..."
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "/home/$APP_USER"

echo ""
echo "=========================================="
echo "  UPLOAD PROJECT FILES"
echo "=========================================="
echo ""
echo "Upload semua file backend ke: $APP_DIR"
echo ""
echo "Dari komputer lokal, jalankan:"
echo "  scp -r ./backend/* ${APP_USER}@<IP_VPS>:${APP_DIR}/"
echo ""
echo "Atau jika pakai git:"
echo "  su - $APP_USER"
echo "  cd /home/$APP_USER"
echo "  git clone <repo-url> backend"
echo ""
read -p "Tekan Enter setelah file sudah di-upload..." _

# ── 6. Setup Python virtual environment ─────────────────────
echo "[5/8] Setting up Python virtual environment..."
su - "$APP_USER" -c "
    cd $APP_DIR
    python${PYTHON_VERSION} -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"

# ── 7. Setup .env ────────────────────────────────────────────
echo "[6/8] Setting up environment file..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo ""
    echo "PENTING: Edit file .env dengan credential yang benar:"
    echo "  nano $APP_DIR/.env"
    echo ""
    read -p "Tekan Enter setelah .env sudah diisi..." _
else
    echo ".env sudah ada, skip."
fi

# ── 8. Setup systemd service ────────────────────────────────
echo "[7/8] Creating systemd service..."
cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=SMART AI IoT Backend
After=network.target
Wants=network-online.target

[Service]
Type=exec
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PATH=${APP_DIR}/venv/bin:/usr/local/bin:/usr/bin
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${APP_NAME}

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${APP_DIR}/logs
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

# Buat direktori logs
mkdir -p "$APP_DIR/logs"
chown "$APP_USER:$APP_USER" "$APP_DIR/logs"

systemctl daemon-reload
systemctl enable "$APP_NAME"
systemctl start "$APP_NAME"

echo "Service '$APP_NAME' started."

# ── 9. Setup Nginx ───────────────────────────────────────────
echo "[8/8] Configuring Nginx..."

if [ -n "$DOMAIN" ]; then
    # Dengan domain
    cat > /etc/nginx/sites-available/${APP_NAME} << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    # Redirect HTTP ke HTTPS (akan aktif setelah certbot)
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    # SSL akan dikonfigurasi oleh certbot
    # ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # API & general proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 90;
    }

    # WebSocket proxy
    location /api/v1/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF
else
    # Tanpa domain (akses via IP)
    cat > /etc/nginx/sites-available/${APP_NAME} << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 90;
    }

    location /api/v1/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF
fi

# Aktifkan site
ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# ── 10. SSL dengan Let's Encrypt ─────────────────────────────
if [ -n "$DOMAIN" ] && [ -n "$SSL_EMAIL" ]; then
    echo "Setting up SSL certificate..."
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$SSL_EMAIL"
    echo "SSL certificate installed."
fi

# ── 11. Firewall ─────────────────────────────────────────────
echo "Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

# ── 12. Selesai ──────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  SETUP SELESAI!"
echo "=========================================="
echo ""
echo "Backend berjalan di:"
if [ -n "$DOMAIN" ]; then
    echo "  https://${DOMAIN}"
    echo "  https://${DOMAIN}/docs     (Swagger UI)"
    echo "  https://${DOMAIN}/health   (Health check)"
else
    echo "  http://<IP_VPS>"
    echo "  http://<IP_VPS>/docs       (Swagger UI)"
    echo "  http://<IP_VPS>/health     (Health check)"
fi
echo ""
echo "Perintah berguna:"
echo "  sudo systemctl status ${APP_NAME}      # Cek status"
echo "  sudo systemctl restart ${APP_NAME}     # Restart"
echo "  sudo journalctl -u ${APP_NAME} -f      # Lihat log real-time"
echo "  sudo systemctl stop ${APP_NAME}        # Stop"
echo ""
echo "Database migration:"
echo "  su - ${APP_USER}"
echo "  cd ${APP_DIR} && source venv/bin/activate"
echo "  alembic upgrade head"
echo ""
