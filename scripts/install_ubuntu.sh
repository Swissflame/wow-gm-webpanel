#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/wow-gm-webpanel}"
APP_USER="${APP_USER:-wowpanel}"
DB_NAME="${DB_NAME:-wow_gm_webpanel}"
DB_USER="${DB_USER:-wowpanel}"
DB_PASS="${DB_PASS:-$(openssl rand -hex 18)}"
DOMAIN="${DOMAIN:-_}"

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx mariadb-server git openssl build-essential default-libmysqlclient-dev

id "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR" /var/log/wow-gm-webpanel
rsync -a --delete --exclude .git --exclude .env --exclude .venv ./ "$APP_DIR/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" /var/log/wow-gm-webpanel

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

mysql <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

if [ ! -f "$APP_DIR/.env" ]; then
  cat > "$APP_DIR/.env" <<ENV
APP_NAME="WoW GM Webpanel"
APP_SECRET_KEY="$(openssl rand -hex 32)"
APP_BASE_URL="http://$(hostname -I | awk '{print $1}')"
APP_LANG="de"
PANEL_DB_URL="mysql+pymysql://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}?charset=utf8mb4"
CONFIGURED="false"
ENV
  chmod 600 "$APP_DIR/.env"
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
fi

cat > /etc/systemd/system/wow-gm-webpanel.service <<SERVICE
[Unit]
Description=WoW GM Webpanel
After=network.target mariadb.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

cat > /etc/nginx/sites-available/wow-gm-webpanel <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};
    client_max_body_size 50m;
    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/wow-gm-webpanel /etc/nginx/sites-enabled/wow-gm-webpanel
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now mariadb wow-gm-webpanel nginx
systemctl restart nginx wow-gm-webpanel
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q active; then
  ufw allow 80/tcp comment 'WoW GM Webpanel HTTP' || true
fi

echo "Installation abgeschlossen: http://$(hostname -I | awk '{print $1}')/"
echo "Panel-DB: ${DB_NAME}, User: ${DB_USER}. Passwort steht nur in ${APP_DIR}/.env"
