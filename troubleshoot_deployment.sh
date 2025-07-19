#!/bin/bash

# GPU Thermal Reporting System - Deployment Troubleshooting Script
# This script fixes common deployment issues and verifies the system

set -e

echo "🔧 GPU Thermal Reporting System - Troubleshooting Script"
echo "========================================================"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script should be run with sudo privileges"
    echo "   Run: sudo ./troubleshoot_deployment.sh"
    exit 1
fi

echo ""
echo "📋 Step 1: Checking system services..."
echo "--------------------------------------"

# Check PostgreSQL status
echo "Checking PostgreSQL..."
if systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is not running. Starting..."
    systemctl start postgresql
    systemctl enable postgresql
fi

# Check if database exists
echo "Checking database..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw gpu_thermal_db; then
    echo "✅ Database 'gpu_thermal_db' exists"
else
    echo "❌ Database 'gpu_thermal_db' not found. Creating..."
    sudo -u postgres psql -c "CREATE DATABASE gpu_thermal_db;"
    sudo -u postgres psql -c "CREATE USER gpu_user WITH PASSWORD 'gpu_password';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gpu_thermal_db TO gpu_user;"
    sudo -u postgres psql -d gpu_thermal_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
fi

# Check TimescaleDB extension
echo "Checking TimescaleDB extension..."
if sudo -u postgres psql -d gpu_thermal_db -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';" | grep -q timescaledb; then
    echo "✅ TimescaleDB extension is installed"
else
    echo "❌ TimescaleDB extension not found. Installing..."
    sudo -u postgres psql -d gpu_thermal_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
fi

echo ""
echo "📋 Step 2: Checking application directory..."
echo "-------------------------------------------"

# Check application directory
if [ -d "/opt/gpu-thermal-reporting" ]; then
    echo "✅ Application directory exists"
    
    # Fix permissions
    echo "Fixing permissions..."
    chown -R drew:drew /opt/gpu-thermal-reporting
    chmod -R 755 /opt/gpu-thermal-reporting
    
    # Create necessary directories
    mkdir -p /opt/gpu-thermal-reporting/uploads
    mkdir -p /opt/gpu-thermal-reporting/logs
    chown -R drew:drew /opt/gpu-thermal-reporting/uploads
    chown -R drew:drew /opt/gpu-thermal-reporting/logs
    chmod 755 /opt/gpu-thermal-reporting/uploads
    chmod 755 /opt/gpu-thermal-reporting/logs
    
    # Create log file if it doesn't exist
    touch /opt/gpu-thermal-reporting/logs/gpu_thermal.log
    chown drew:drew /opt/gpu-thermal-reporting/logs/gpu_thermal.log
    chmod 644 /opt/gpu-thermal-reporting/logs/gpu_thermal.log
    
else
    echo "❌ Application directory not found. Please run the deployment script first."
    exit 1
fi

echo ""
echo "📋 Step 3: Checking Python environment..."
echo "----------------------------------------"

# Check virtual environment
if [ -d "/opt/gpu-thermal-reporting/venv" ]; then
    echo "✅ Virtual environment exists"
    
    # Check if requirements are installed
    if /opt/gpu-thermal-reporting/venv/bin/python -c "import flask, pandas, sqlalchemy" 2>/dev/null; then
        echo "✅ Python dependencies are installed"
    else
        echo "❌ Python dependencies missing. Installing..."
        cd /opt/gpu-thermal-reporting
        /opt/gpu-thermal-reporting/venv/bin/pip install -r requirements.txt
    fi
else
    echo "❌ Virtual environment not found. Creating..."
    cd /opt/gpu-thermal-reporting
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

echo ""
echo "📋 Step 4: Checking systemd service..."
echo "-------------------------------------"

# Check if service file exists
if [ -f "/etc/systemd/system/gpu-thermal-reporting.service" ]; then
    echo "✅ Systemd service file exists"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Check service status
    if systemctl is-active --quiet gpu-thermal-reporting; then
        echo "✅ GPU Thermal Reporting service is running"
    else
        echo "❌ GPU Thermal Reporting service is not running. Starting..."
        systemctl start gpu-thermal-reporting
        systemctl enable gpu-thermal-reporting
    fi
else
    echo "❌ Systemd service file not found. Creating..."
    cat > /etc/systemd/system/gpu-thermal-reporting.service << 'EOF'
[Unit]
Description=GPU Thermal Reporting System
After=network.target postgresql.service

[Service]
Type=simple
User=drew
WorkingDirectory=/opt/gpu-thermal-reporting
Environment=PATH=/opt/gpu-thermal-reporting/venv/bin
Environment=DATABASE_URL=postgresql://gpu_user:gpu_password@localhost:5432/gpu_thermal_db
ExecStart=/opt/gpu-thermal-reporting/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable gpu-thermal-reporting
    systemctl start gpu-thermal-reporting
fi

echo ""
echo "📋 Step 5: Checking nginx..."
echo "----------------------------"

# Check nginx
if command -v nginx &> /dev/null; then
    echo "✅ Nginx is installed"
    
    if systemctl is-active --quiet nginx; then
        echo "✅ Nginx is running"
    else
        echo "❌ Nginx is not running. Starting..."
        systemctl start nginx
        systemctl enable nginx
    fi
    
    # Check nginx configuration
    if nginx -t &> /dev/null; then
        echo "✅ Nginx configuration is valid"
    else
        echo "❌ Nginx configuration is invalid. Fixing..."
        cat > /etc/nginx/sites-available/gpu-thermal-reporting << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/gpu-thermal-reporting/static;
    }
}
EOF

        ln -sf /etc/nginx/sites-available/gpu-thermal-reporting /etc/nginx/sites-enabled/
        rm -f /etc/nginx/sites-enabled/default
        systemctl restart nginx
    fi
else
    echo "❌ Nginx not installed. Installing..."
    apt update
    apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
fi

echo ""
echo "📋 Step 6: Testing the application..."
echo "------------------------------------"

# Wait a moment for services to start
sleep 5

# Test database connection
echo "Testing database connection..."
if sudo -u postgres psql -d gpu_thermal_db -c "SELECT version();" &> /dev/null; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
fi

# Test application health
echo "Testing application health..."
if curl -s http://localhost:5000/health &> /dev/null; then
    echo "✅ Application is responding"
    curl -s http://localhost:5000/health
else
    echo "❌ Application is not responding"
    echo "Checking application logs..."
    tail -20 /opt/gpu-thermal-reporting/logs/gpu_thermal.log
fi

# Test web access
echo "Testing web access..."
if curl -s -I http://localhost | grep -q "200 OK"; then
    echo "✅ Web server is responding"
else
    echo "❌ Web server is not responding"
fi

echo ""
echo "📋 Step 7: Final status check..."
echo "--------------------------------"

echo "Service Status:"
systemctl status gpu-thermal-reporting --no-pager -l | head -10

echo ""
echo "Database Status:"
systemctl status postgresql --no-pager -l | head -5

echo ""
echo "Nginx Status:"
systemctl status nginx --no-pager -l | head -5

echo ""
echo "📊 System Information:"
echo "Server IP: $(hostname -I | awk '{print $1}')"
echo "Dashboard URL: http://$(hostname -I | awk '{print $1}')"
echo "API URL: http://$(hostname -I | awk '{print $1}'):5000/api"

echo ""
echo "✅ Troubleshooting complete!"
echo ""
echo "If you still have issues, check the logs:"
echo "  Application logs: tail -f /opt/gpu-thermal-reporting/logs/gpu_thermal.log"
echo "  System logs: sudo journalctl -u gpu-thermal-reporting -f"
echo ""
echo "Next steps:"
echo "1. Upload your CSV files to /opt/gpu-thermal-reporting/uploads/"
echo "2. Run: cd /opt/gpu-thermal-reporting && source venv/bin/activate && python3 process_data.py"
echo "3. Access the dashboard at http://$(hostname -I | awk '{print $1}')" 