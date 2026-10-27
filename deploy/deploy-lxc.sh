#!/usr/bin/env bash
# ==============================================================================
# UzTrack (UZ-LTS) - Automated 1-Click Deployment Script for LXC VPS
# Compatible with: Debian 11/12, Ubuntu 22.04/24.04 inside Proxmox / LXC
# ==============================================================================

set -e

echo "🚀 Starting UzTrack Deployment on LXC VPS..."

# 1. Update system packages
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git build-essential ufw ca-certificates

# 2. Check deployment mode: Docker vs Native Systemd
if command -v docker &> /dev/null; then
    echo "🐳 Docker detected. Deploying via Docker Compose..."
    cd /opt/uztrack/deploy
    docker compose down || true
    docker compose up -d --build
    echo "✅ UzTrack successfully deployed via Docker Compose on LXC!"
    docker compose ps
    exit 0
fi

echo "📦 Setting up Native Bare-Metal Service inside LXC..."

# 3. Create unprivileged service user
id -u uztrack &>/dev/null || useradd -r -s /bin/false uztrack

# 4. Create directory structure
mkdir -p /opt/uztrack/bin
mkdir -p /opt/uztrack/public
mkdir -p /opt/uztrack/config

# 5. Install PostgreSQL & Redis if not already installed
if ! command -v psql &> /dev/null; then
    echo "🐘 Installing PostgreSQL & PostGIS..."
    apt-get install -y postgresql postgresql-contrib postgis postgresql-16-postgis-3 || apt-get install -y postgresql postgis
    systemctl enable postgresql
    systemctl start postgresql

    # Create database & user
    sudo -u postgres psql -c "CREATE USER uztrack WITH PASSWORD 'uztrack_secret';" || true
    sudo -u postgres psql -c "CREATE DATABASE uztrack_db OWNER uztrack;" || true
    sudo -u postgres psql -d uztrack_db -f /opt/uztrack/deploy/db/init.sql || true
fi

if ! command -v redis-server &> /dev/null; then
    echo "⚡ Installing Redis..."
    apt-get install -y redis-server
    systemctl enable redis-server
    systemctl start redis-server
fi

# 6. Copy binary and public assets
cp /opt/uztrack/deploy/systemd/uztrack.service /etc/systemd/system/uztrack.service
chown -R uztrack:uztrack /opt/uztrack

# 7. Start and enable service
systemctl daemon-reload
systemctl enable uztrack
systemctl restart uztrack

echo "🎉 UzTrack is now running as a native systemd daemon!"
systemctl status uztrack --no-pager
