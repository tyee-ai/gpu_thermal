# Quick Reference Card - GPU Thermal Reporting System

## 🚀 Essential Commands

### System Status
```bash
# Check all services
sudo systemctl status gpu-thermal-reporting postgresql nginx

# Check application logs
tail -f /opt/gpu-thermal-reporting/logs/gpu_thermal.log

# Check system resources
htop
df -h
free -h
```

### Database Operations
```bash
# Connect to database
sudo -u postgres psql -d gpu_thermal_db

# Check record counts
sudo -u postgres psql -d gpu_thermal_db -c "SELECT COUNT(*) FROM gpu_thermal_events;"

# Check data by type
sudo -u postgres psql -d gpu_thermal_db -c "SELECT issue_type, COUNT(*) FROM gpu_thermal_events GROUP BY issue_type;"

# View recent data
sudo -u postgres psql -d gpu_thermal_db -c "SELECT * FROM gpu_thermal_events ORDER BY timestamp DESC LIMIT 10;"
```

### Data Processing
```bash
# Process CSV files
cd /opt/gpu-thermal-reporting
source venv/bin/activate
python3 process_data.py

# Validate CSV format
python3 -c "from data_processor import GPUDataProcessor; from database import DatabaseManager; p = GPUDataProcessor(DatabaseManager()); print(p.validate_csv_format('your_file.csv'))"
```

### API Testing
```bash
# Health check
curl http://localhost:5000/health

# Get all data
curl http://localhost:5000/api/data

# Get statistics
curl http://localhost:5000/api/stats

# Get GPU list
curl http://localhost:5000/api/gpus
```

## 🔧 Troubleshooting

### Service Issues
```bash
# Restart application
sudo systemctl restart gpu-thermal-reporting

# Restart database
sudo systemctl restart postgresql

# Restart web server
sudo systemctl restart nginx

# Check service logs
sudo journalctl -u gpu-thermal-reporting -f
```

### Database Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -d gpu_thermal_db -c "SELECT version();"

# Check TimescaleDB
sudo -u postgres psql -d gpu_thermal_db -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"
```

### File Permission Issues
```bash
# Fix upload directory permissions
sudo chown -R $USER:$USER /opt/gpu-thermal-reporting/uploads/
sudo chmod 755 /opt/gpu-thermal-reporting/uploads/

# Fix log file permissions
sudo chown $USER:$USER /opt/gpu-thermal-reporting/logs/gpu_thermal.log
sudo chmod 644 /opt/gpu-thermal-reporting/logs/gpu_thermal.log
```

## 📊 Data Validation

### CSV Format Check
```bash
# Check CSV headers
head -1 your_file.csv

# Count lines (minus header)
wc -l your_file.csv

# View sample data
head -5 your_file.csv
```

### Database Validation
```bash
# Compare CSV count with database
echo "CSV lines: $(($(wc -l < your_file.csv) - 1))"
sudo -u postgres psql -d gpu_thermal_db -c "SELECT COUNT(*) FROM gpu_thermal_events;"

# Check temperature ranges
sudo -u postgres psql -d gpu_thermal_db -c "SELECT MIN(temperature), MAX(temperature), AVG(temperature) FROM gpu_thermal_events;"
```

## 🌐 Web Access

### Dashboard URLs
- **Main Dashboard**: `http://YOUR_SERVER_IP`
- **API Base**: `http://YOUR_SERVER_IP:5000/api`
- **Health Check**: `http://YOUR_SERVER_IP:5000/health`

### Get Server IP
```bash
hostname -I
```

## 📁 Important Directories

```bash
# Application directory
/opt/gpu-thermal-reporting/

# Upload directory
/opt/gpu-thermal-reporting/uploads/

# Log directory
/opt/gpu-thermal-reporting/logs/

# Virtual environment
/opt/gpu-thermal-reporting/venv/
```

## 🔄 Common Workflows

### Complete Data Processing
```bash
# 1. Copy CSV files
sudo cp your_file.csv /opt/gpu-thermal-reporting/uploads/

# 2. Set permissions
sudo chown $USER:$USER /opt/gpu-thermal-reporting/uploads/*.csv

# 3. Process data
cd /opt/gpu-thermal-reporting
source venv/bin/activate
python3 process_data.py

# 4. Verify data
sudo -u postgres psql -d gpu_thermal_db -c "SELECT COUNT(*) FROM gpu_thermal_events;"

# 5. Test API
curl http://localhost:5000/api/stats
```

### System Restart
```bash
# 1. Stop services
sudo systemctl stop gpu-thermal-reporting nginx

# 2. Restart database
sudo systemctl restart postgresql

# 3. Start services
sudo systemctl start gpu-thermal-reporting nginx

# 4. Verify status
sudo systemctl status gpu-thermal-reporting postgresql nginx
```

## ⚠️ Emergency Commands

### Complete Reset (Use with caution)
```bash
# Stop all services
sudo systemctl stop gpu-thermal-reporting nginx postgresql

# Clear database (WARNING: This deletes all data!)
sudo -u postgres psql -d gpu_thermal_db -c "TRUNCATE gpu_thermal_events, gpu_metadata;"

# Restart services
sudo systemctl start postgresql gpu-thermal-reporting nginx
```

### Backup Database
```bash
# Create backup
sudo -u postgres pg_dump gpu_thermal_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup (if needed)
sudo -u postgres psql -d gpu_thermal_db < backup_file.sql
```

## 📞 Support Information

### Log Locations
- Application: `/opt/gpu-thermal-reporting/logs/gpu_thermal.log`
- System: `sudo journalctl -u gpu-thermal-reporting`
- Nginx: `/var/log/nginx/`
- PostgreSQL: `/var/log/postgresql/`

### Key Files
- Configuration: `/opt/gpu-thermal-reporting/app.py`
- Database: `/opt/gpu-thermal-reporting/database.py`
- Data Processing: `/opt/gpu-thermal-reporting/data_processor.py`
- Service: `/etc/systemd/system/gpu-thermal-reporting.service`

### Environment Variables
```bash
# Check current environment
env | grep DATABASE

# Set environment variable
export DATABASE_URL="postgresql://gpu_user:gpu_password@localhost:5432/gpu_thermal_db"
``` 