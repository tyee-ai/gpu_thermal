#!/bin/bash

# GPU Thermal Reporting System Deployment Script for Ubuntu 22.04
# This script sets up the complete system with PostgreSQL + TimescaleDB

set -e

echo "🚀 Starting GPU Thermal Reporting System deployment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib curl wget git

# Install TimescaleDB
echo "🗄️ Installing TimescaleDB..."
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ jammy main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-2-postgresql-14

# Configure PostgreSQL for TimescaleDB
echo "⚙️ Configuring PostgreSQL..."
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql

# Create database and user
echo "🗃️ Setting up database..."
sudo -u postgres psql -c "CREATE DATABASE gpu_thermal_db;"
sudo -u postgres psql -c "CREATE USER gpu_user WITH PASSWORD 'gpu_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gpu_thermal_db TO gpu_user;"
sudo -u postgres psql -d gpu_thermal_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /opt/gpu-thermal-reporting
sudo chown $USER:$USER /opt/gpu-thermal-reporting

# Copy application files
echo "📋 Copying application files..."
cp -r . /opt/gpu-thermal-reporting/
cd /opt/gpu-thermal-reporting

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create upload directory
echo "📂 Creating upload directory..."
mkdir -p uploads
chmod 755 uploads

# Create log directory
echo "📝 Setting up logging..."
mkdir -p logs
touch logs/gpu_thermal.log
chmod 644 logs/gpu_thermal.log

# Create systemd service file
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/gpu-thermal-reporting.service > /dev/null <<EOF
[Unit]
Description=GPU Thermal Reporting System
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/gpu-thermal-reporting
Environment=PATH=/opt/gpu-thermal-reporting/venv/bin
Environment=DATABASE_URL=postgresql://gpu_user:gpu_password@localhost:5432/gpu_thermal_db
ExecStart=/opt/gpu-thermal-reporting/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration
echo "🌐 Setting up nginx..."
sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/gpu-thermal-reporting > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias /opt/gpu-thermal-reporting/static;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/gpu-thermal-reporting /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Enable and start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable gpu-thermal-reporting
sudo systemctl start gpu-thermal-reporting

# Create firewall rules
echo "🔥 Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Create sample data files
echo "📊 Creating sample data files..."
cat > sample_thermal_failed.csv <<EOF
node,timestamp,gpu_id,temp,avg_temp,reason,date
10.4.21.8,2025-03-17,GPU_28,44.0,28.08,Thermally Failed,2025-03-17
10.4.21.8,2025-03-18,GPU_28,45.0,28.61,Thermally Failed,2025-03-18
10.4.21.8,2025-03-19,GPU_28,45.0,28.6,Thermally Failed,2025-03-19
EOF

cat > sample_throttled.csv <<EOF
node,timestamp,gpu_id,temp,reason,date
10.4.21.8,2025-04-15,GPU_28,86.24,Throttled,2025-04-15
10.4.21.8,2025-04-16,GPU_28,91.23,Throttled,2025-04-16
10.4.21.62,2025-02-10,GPU_22,91.31,Throttled,2025-02-10
EOF

# Create data processing script
echo "📝 Creating data processing script..."
cat > process_data.py <<EOF
#!/usr/bin/env python3
"""
Data processing script for GPU thermal data
"""

import sys
import os
sys.path.append('/opt/gpu-thermal-reporting')

from database import DatabaseManager
from data_processor import GPUDataProcessor

def main():
    """Process CSV files in the uploads directory"""
    db_manager = DatabaseManager()
    processor = GPUDataProcessor(db_manager)
    
    upload_dir = 'uploads'
    if not os.path.exists(upload_dir):
        print(f"Upload directory {upload_dir} does not exist")
        return
    
    results = processor.process_directory(upload_dir)
    
    print("Processing results:")
    for filename, count in results.items():
        print(f"  {filename}: {count} records processed")

if __name__ == '__main__':
    main()
EOF

chmod +x process_data.py

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > monitor.sh <<EOF
#!/bin/bash

echo "=== GPU Thermal Reporting System Status ==="
echo "Service status:"
sudo systemctl status gpu-thermal-reporting --no-pager -l

echo -e "\nDatabase status:"
sudo systemctl status postgresql --no-pager -l

echo -e "\nNginx status:"
sudo systemctl status nginx --no-pager -l

echo -e "\nRecent logs:"
tail -20 logs/gpu_thermal.log

echo -e "\nDisk usage:"
df -h /opt/gpu-thermal-reporting

echo -e "\nMemory usage:"
free -h
EOF

chmod +x monitor.sh

# Create backup script
echo "💾 Creating backup script..."
cat > backup.sh <<EOF
#!/bin/bash

BACKUP_DIR="/opt/backups/gpu-thermal"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

echo "Creating backup: \$BACKUP_DIR/backup_\$DATE.sql"
sudo -u postgres pg_dump gpu_thermal_db > \$BACKUP_DIR/backup_\$DATE.sql

echo "Backup completed: \$BACKUP_DIR/backup_\$DATE.sql"
EOF

chmod +x backup.sh

# Set up log rotation
echo "📋 Setting up log rotation..."
sudo tee /etc/logrotate.d/gpu-thermal-reporting > /dev/null <<EOF
/opt/gpu-thermal-reporting/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload gpu-thermal-reporting
    endscript
}
EOF

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access the dashboard at: http://$(hostname -I | awk '{print $1}')"
echo "📊 API endpoint: http://$(hostname -I | awk '{print $1}'):5000/api"
echo "📁 Upload directory: /opt/gpu-thermal-reporting/uploads"
echo "📝 Logs: /opt/gpu-thermal-reporting/logs/gpu_thermal.log"
echo ""
echo "🔧 Useful commands:"
echo "  Monitor system: ./monitor.sh"
echo "  Process data: python3 process_data.py"
echo "  Backup database: ./backup.sh"
echo "  View logs: tail -f logs/gpu_thermal.log"
echo "  Restart service: sudo systemctl restart gpu-thermal-reporting"
echo ""
echo "📋 Next steps:"
echo "1. Upload your CSV files to the uploads directory"
echo "2. Run: python3 process_data.py"
echo "3. Access the dashboard to view your data" 