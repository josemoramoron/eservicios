#!/bin/bash
set -e
cd /var/www/eservicios

if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
if [ -d migrations ]; then
    flask db upgrade
fi

echo "Deploy completado: $(date)"
sudo systemctl restart eservicios
