# GPU Thermal Reporting System

A comprehensive time-series based reporting system for monitoring GPU thermal issues, including both throttled GPUs and thermally failed GPUs. Built with PostgreSQL + TimescaleDB for optimal performance with thousands of records.

## 🚀 Features

- **Time-Series Database**: PostgreSQL with TimescaleDB for efficient handling of large datasets
- **CSV Data Ingestion**: Automatic processing of CSV files with flexible column mapping
- **Interactive Dashboard**: Real-time visualizations with Plotly and Dash
- **RESTful API**: Complete API for data access and integration
- **Bulk Data Processing**: Optimized for processing thousands of records
- **Automated Deployment**: One-click deployment script for Ubuntu 22.04

## 📊 Data Format

The system accepts CSV files with the following columns:

### Required Columns:
- `node`: Server/node identifier (e.g., "10.4.21.8")
- `timestamp`: Event timestamp (e.g., "2025-03-17")
- `gpu_id`: GPU identifier (e.g., "GPU_28")
- `reason`: Issue type ("Thermally Failed" or "Throttled")

### Optional Columns:
- `temp`: Current temperature in Celsius
- `avg_temp`: Average temperature in Celsius
- `date`: Event date

### Example CSV Format:

**Thermal Failures:**
```csv
node,timestamp,gpu_id,temp,avg_temp,reason,date
10.4.21.8,2025-03-17,GPU_28,44.0,28.08,Thermally Failed,2025-03-17
10.4.21.8,2025-03-18,GPU_28,45.0,28.61,Thermally Failed,2025-03-18
```

**Throttling Events:**
```csv
node,timestamp,gpu_id,temp,reason,date
10.4.21.8,2025-04-15,GPU_28,86.24,Throttled,2025-04-15
10.4.21.62,2025-02-10,GPU_22,91.31,Throttled,2025-02-10
```

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CSV Files     │    │   Web Dashboard │    │   REST API      │
│   (Upload)      │    │   (Dash/Plotly) │    │   (Flask)       │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    Data Processor         │
                    │    (Pandas/SQLAlchemy)    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  PostgreSQL + TimescaleDB │
                    │    (Time-Series DB)       │
                    └───────────────────────────┘
```

## 🛠️ Installation & Deployment

### Prerequisites
- Ubuntu 22.04 LTS
- sudo privileges
- Internet connection

### Quick Deployment

1. **Clone or download the project:**
```bash
git clone <repository-url>
cd gpu-thermal-reporting
```

2. **Run the deployment script:**
```bash
chmod +x deploy.sh
./deploy.sh
```

The deployment script will:
- Install PostgreSQL and TimescaleDB
- Set up Python virtual environment
- Install all dependencies
- Configure nginx web server
- Create systemd service
- Set up firewall rules
- Create monitoring and backup scripts

### Manual Installation

If you prefer manual installation:

1. **Install system dependencies:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx
```

2. **Install TimescaleDB:**
```bash
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ jammy main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-2-postgresql-14
```

3. **Set up database:**
```bash
sudo -u postgres psql -c "CREATE DATABASE gpu_thermal_db;"
sudo -u postgres psql -c "CREATE USER gpu_user WITH PASSWORD 'gpu_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gpu_thermal_db TO gpu_user;"
sudo -u postgres psql -d gpu_thermal_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

4. **Install Python dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. **Run the application:**
```bash
python app.py
```

## 📖 Usage Guide

### 1. Uploading Data

**Option A: Web Interface**
- Access the dashboard at `http://your-server-ip`
- Use the upload form to submit CSV files

**Option B: File System**
- Copy CSV files to `/opt/gpu-thermal-reporting/uploads/`
- Run the processing script:
```bash
cd /opt/gpu-thermal-reporting
python3 process_data.py
```

### 2. Accessing the Dashboard

- **Main Dashboard**: `http://your-server-ip`
- **API Endpoints**: `http://your-server-ip:5000/api`

### 3. API Usage

**Get all GPU data:**
```bash
curl "http://your-server-ip:5000/api/data"
```

**Get filtered data:**
```bash
curl "http://your-server-ip:5000/api/data?start_date=2025-03-01&end_date=2025-03-31&gpu_id=GPU_28"
```

**Get summary statistics:**
```bash
curl "http://your-server-ip:5000/api/stats"
```

**Get list of GPUs:**
```bash
curl "http://your-server-ip:5000/api/gpus"
```

### 4. Monitoring and Maintenance

**Check system status:**
```bash
./monitor.sh
```

**View logs:**
```bash
tail -f logs/gpu_thermal.log
```

**Backup database:**
```bash
./backup.sh
```

**Restart service:**
```bash
sudo systemctl restart gpu-thermal-reporting
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the application directory:

```env
DATABASE_URL=postgresql://gpu_user:gpu_password@localhost:5432/gpu_thermal_db
FLASK_ENV=production
LOG_LEVEL=INFO
```

### Database Configuration

The system uses TimescaleDB with the following optimizations:
- Automatic time-based partitioning (1-day chunks)
- Indexes on GPU ID, timestamp, and issue type
- Time-bucket functions for efficient aggregation

### Performance Tuning

For large datasets (millions of records):

1. **Adjust TimescaleDB settings:**
```sql
SELECT set_chunk_time_interval('gpu_thermal_events', INTERVAL '1 day');
```

2. **Create additional indexes:**
```sql
CREATE INDEX CONCURRENTLY idx_gpu_thermal_events_node_timestamp 
ON gpu_thermal_events(node, timestamp DESC);
```

3. **Configure PostgreSQL memory settings:**
```bash
sudo timescaledb-tune --quiet --yes
```

## 📊 Dashboard Features

### Interactive Visualizations
- **Time Series Charts**: GPU events over time
- **Temperature Distribution**: Histograms by issue type
- **GPU Analysis**: Events by GPU ID
- **Node Analysis**: Events by server/node
- **Summary Cards**: Key metrics at a glance

### Filtering Options
- Date range selection
- GPU ID filtering
- Issue type filtering (throttled/failed)
- Node filtering

### Real-time Updates
- Automatic data refresh
- Live statistics
- Recent events table

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Error**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
sudo -u postgres psql -d gpu_thermal_db -c "SELECT version();"
```

2. **Service Not Starting**
```bash
# Check service logs
sudo journalctl -u gpu-thermal-reporting -f

# Check application logs
tail -f logs/gpu_thermal.log
```

3. **CSV Processing Errors**
```bash
# Validate CSV format
python3 -c "from data_processor import GPUDataProcessor; from database import DatabaseManager; p = GPUDataProcessor(DatabaseManager()); print(p.validate_csv_format('your_file.csv'))"
```

4. **Performance Issues**
```bash
# Check database performance
sudo -u postgres psql -d gpu_thermal_db -c "SELECT * FROM timescaledb_information.chunks;"

# Monitor system resources
htop
```

### Log Locations
- Application logs: `/opt/gpu-thermal-reporting/logs/gpu_thermal.log`
- System logs: `sudo journalctl -u gpu-thermal-reporting`
- Nginx logs: `/var/log/nginx/`
- PostgreSQL logs: `/var/log/postgresql/`

## 🔒 Security Considerations

1. **Change default passwords** in the deployment script
2. **Configure SSL/TLS** for production use
3. **Set up firewall rules** to restrict access
4. **Regular security updates**
5. **Database backups** and monitoring

## 📈 Scaling Considerations

### For Large Deployments

1. **Database Scaling**
   - Consider TimescaleDB clustering
   - Implement read replicas
   - Use connection pooling

2. **Application Scaling**
   - Deploy multiple application instances
   - Use load balancer (nginx/haproxy)
   - Implement caching (Redis)

3. **Storage Scaling**
   - Monitor disk usage
   - Implement data retention policies
   - Consider object storage for backups

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

---

**Note**: This system is optimized for Ubuntu 22.04 with PostgreSQL 14 and TimescaleDB 2. For other operating systems or database versions, manual configuration may be required. 