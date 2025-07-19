# Junior Engineer Task List: GPU Thermal Reporting System

## 🎯 Objective
Install, verify, and populate the GPU Thermal Reporting System database with CSV data on Ubuntu 22.04.

## ⏱️ Estimated Time
- **Total Time**: 2-3 hours
- **Installation**: 45 minutes
- **Verification**: 30 minutes  
- **Data Population**: 45 minutes
- **Testing**: 30 minutes

---

## 📋 Pre-Installation Checklist

### Task 1: System Requirements Verification
- [ ] **Verify Ubuntu 22.04 LTS**
  ```bash
  lsb_release -a
  ```
  Expected output: `Ubuntu 22.04.x LTS`

- [ ] **Check available disk space**
  ```bash
  df -h
  ```
  Ensure at least 5GB free space

- [ ] **Verify internet connectivity**
  ```bash
  ping -c 3 google.com
  ```

- [ ] **Check sudo privileges**
  ```bash
  sudo whoami
  ```
  Should return: `root`

### Task 2: Prepare CSV Files
- [ ] **Locate your CSV files**
  - Find the thermally failed CSV file
  - Find the throttled CSV file
  - Verify file format matches expected structure

- [ ] **Validate CSV structure**
  ```bash
  head -5 your_thermal_failed.csv
  head -5 your_throttled.csv
  ```
  Should show headers: `node,timestamp,gpu_id,temp,avg_temp,reason,date`

---

## 🚀 Installation Phase

### Task 3: Download and Prepare Project
- [ ] **Create project directory**
  ```bash
  mkdir -p ~/gpu-thermal-project
  cd ~/gpu-thermal-project
  ```

- [ ] **Download project files**
  ```bash
  # If using git:
  git clone <repository-url> .
  
  # Or copy files manually to this directory
  ```

- [ ] **Verify project structure**
  ```bash
  ls -la
  ```
  Should show: `app.py`, `database.py`, `data_processor.py`, `dashboard.py`, `requirements.txt`, `deploy.sh`

### Task 4: Run Automated Deployment
- [ ] **Make deployment script executable**
  ```bash
  chmod +x deploy.sh
  ```

- [ ] **Run deployment script**
  ```bash
  ./deploy.sh
  ```
  ⚠️ **Important**: This will take 10-15 minutes. Watch for any error messages.

- [ ] **Monitor deployment progress**
  - Watch for success messages
  - Note any warnings (some are normal)
  - Record the final server IP address

### Task 5: Verify Installation
- [ ] **Check service status**
  ```bash
  sudo systemctl status gpu-thermal-reporting
  ```
  Should show: `Active: active (running)`

- [ ] **Check database status**
  ```bash
  sudo systemctl status postgresql
  ```
  Should show: `Active: active (running)`

- [ ] **Check nginx status**
  ```bash
  sudo systemctl status nginx
  ```
  Should show: `Active: active (running)`

- [ ] **Get server IP address**
  ```bash
  hostname -I
  ```
  Note this IP for dashboard access

---

## 🔍 Verification Phase

### Task 6: Database Connection Test
- [ ] **Test database connectivity**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT version();"
  ```
  Should return PostgreSQL version

- [ ] **Verify TimescaleDB extension**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"
  ```
  Should return 1 row

- [ ] **Check database tables**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "\dt"
  ```
  Should show: `gpu_thermal_events` and `gpu_metadata`

### Task 7: Application Health Check
- [ ] **Test API endpoint**
  ```bash
  curl http://localhost:5000/health
  ```
  Should return: `{"status": "healthy", "timestamp": "..."}`

- [ ] **Test dashboard access**
  ```bash
  curl -I http://localhost
  ```
  Should return: `HTTP/1.1 200 OK`

- [ ] **Check application logs**
  ```bash
  tail -20 /opt/gpu-thermal-reporting/logs/gpu_thermal.log
  ```
  Look for any ERROR messages

### Task 8: Web Interface Verification
- [ ] **Open web browser**
  - Navigate to: `http://YOUR_SERVER_IP`
  - Should see GPU Thermal Monitoring Dashboard

- [ ] **Test dashboard elements**
  - [ ] Verify dashboard loads without errors
  - [ ] Check that filter dropdowns are present
  - [ ] Confirm charts area is visible
  - [ ] Note that data will be empty initially

---

## 📊 Data Population Phase

### Task 9: Prepare CSV Files for Upload
- [ ] **Copy CSV files to upload directory**
  ```bash
  sudo cp your_thermal_failed.csv /opt/gpu-thermal-reporting/uploads/
  sudo cp your_throttled.csv /opt/gpu-thermal-reporting/uploads/
  ```

- [ ] **Set proper permissions**
  ```bash
  sudo chown $USER:$USER /opt/gpu-thermal-reporting/uploads/*.csv
  sudo chmod 644 /opt/gpu-thermal-reporting/uploads/*.csv
  ```

- [ ] **Verify files are accessible**
  ```bash
  ls -la /opt/gpu-thermal-reporting/uploads/
  ```

### Task 10: Process CSV Data
- [ ] **Navigate to application directory**
  ```bash
  cd /opt/gpu-thermal-reporting
  ```

- [ ] **Activate virtual environment**
  ```bash
  source venv/bin/activate
  ```

- [ ] **Run data processing script**
  ```bash
  python3 process_data.py
  ```
  Expected output: Processing results showing record counts

- [ ] **Verify processing results**
  - Note the number of records processed for each file
  - Check for any error messages
  - Ensure both files were processed successfully

### Task 11: Verify Data Population
- [ ] **Check database record count**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT COUNT(*) FROM gpu_thermal_events;"
  ```
  Should show total number of records

- [ ] **Check data by issue type**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT issue_type, COUNT(*) FROM gpu_thermal_events GROUP BY issue_type;"
  ```
  Should show counts for 'throttled' and 'failed'

- [ ] **Check unique GPUs**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT COUNT(DISTINCT gpu_id) FROM gpu_thermal_events;"
  ```

- [ ] **Check unique nodes**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT COUNT(DISTINCT node) FROM gpu_thermal_events;"
  ```

---

## 🧪 Testing Phase

### Task 12: API Testing
- [ ] **Test data retrieval API**
  ```bash
  curl "http://localhost:5000/api/data" | head -20
  ```
  Should return JSON data

- [ ] **Test statistics API**
  ```bash
  curl "http://localhost:5000/api/stats"
  ```
  Should return summary statistics

- [ ] **Test GPU list API**
  ```bash
  curl "http://localhost:5000/api/gpus"
  ```
  Should return list of GPUs

### Task 13: Dashboard Testing
- [ ] **Refresh dashboard**
  - Navigate to: `http://YOUR_SERVER_IP`
  - Click "Refresh Data" button

- [ ] **Verify summary cards**
  - [ ] Total Events card shows correct count
  - [ ] Throttled Events card shows throttled count
  - [ ] Failed Events card shows failed count
  - [ ] Average Temperature card shows temperature

- [ ] **Test filters**
  - [ ] Select a date range
  - [ ] Select specific GPU IDs
  - [ ] Filter by issue type
  - [ ] Verify charts update accordingly

- [ ] **Verify charts**
  - [ ] Time series chart shows data over time
  - [ ] Temperature distribution chart shows histogram
  - [ ] GPU events chart shows bar chart
  - [ ] Node events chart shows pie chart

- [ ] **Check data table**
  - [ ] Recent events table shows last 50 events
  - [ ] Data includes node, GPU ID, timestamp, temperature, issue type, reason

### Task 14: Data Validation
- [ ] **Cross-reference with original CSV**
  ```bash
  # Count lines in original CSV (minus header)
  wc -l your_thermal_failed.csv
  wc -l your_throttled.csv
  
  # Compare with database counts
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT issue_type, COUNT(*) FROM gpu_thermal_events GROUP BY issue_type;"
  ```

- [ ] **Verify temperature ranges**
  ```bash
  sudo -u postgres psql -d gpu_thermal_db -c "SELECT MIN(temperature), MAX(temperature), AVG(temperature) FROM gpu_thermal_events;"
  ```
  Should match expected ranges from your data

---

## 📝 Documentation Phase

### Task 15: Create Installation Report
- [ ] **Document system details**
  - Server IP address: `_________________`
  - Total records processed: `_________________`
  - Throttled records: `_________________`
  - Failed records: `_________________`
  - Unique GPUs: `_________________`
  - Unique nodes: `_________________`

- [ ] **Record any issues encountered**
  - List any error messages
  - Note any workarounds used
  - Document unexpected behavior

- [ ] **Test dashboard URL**
  - Confirm: `http://YOUR_SERVER_IP` works
  - Test from different browser/device if possible

### Task 16: Performance Verification
- [ ] **Test dashboard responsiveness**
  - [ ] Page loads within 5 seconds
  - [ ] Charts render properly
  - [ ] Filters respond quickly
  - [ ] No browser console errors

- [ ] **Check system resources**
  ```bash
  free -h
  df -h
  top -n 1
  ```

---

## 🚨 Troubleshooting Guide

### Common Issues and Solutions

**Issue**: Deployment script fails
- **Solution**: Check internet connection and sudo privileges
- **Command**: `sudo apt update && sudo apt upgrade -y`

**Issue**: Service won't start
- **Solution**: Check logs for specific errors
- **Command**: `sudo journalctl -u gpu-thermal-reporting -f`

**Issue**: Database connection fails
- **Solution**: Verify PostgreSQL is running
- **Command**: `sudo systemctl restart postgresql`

**Issue**: CSV processing errors
- **Solution**: Check CSV format and column names
- **Command**: `head -1 your_file.csv`

**Issue**: Dashboard shows no data
- **Solution**: Verify data was processed and refresh dashboard
- **Command**: `curl http://localhost:5000/api/stats`

---

## ✅ Final Checklist

Before considering the task complete:

- [ ] System is fully installed and running
- [ ] Database contains all CSV data
- [ ] Dashboard displays data correctly
- [ ] All API endpoints respond properly
- [ ] Filters and charts work as expected
- [ ] Performance is acceptable
- [ ] Documentation is complete
- [ ] Any issues are documented with solutions

---

## 📞 Escalation Points

If you encounter issues you cannot resolve:

1. **Check the logs first**: `/opt/gpu-thermal-reporting/logs/gpu_thermal.log`
2. **Review this task list** for missed steps
3. **Document the exact error** and what you were doing when it occurred
4. **Escalate to senior engineer** with:
   - Error messages
   - Steps taken
   - System information
   - Log files

---

**🎉 Congratulations!** You have successfully installed, verified, and populated the GPU Thermal Reporting System. The system is now ready for production use. 