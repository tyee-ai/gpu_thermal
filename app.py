#!/usr/bin/env python3
"""
GPU Thermal Reporting System
Main Flask application for ingesting CSV data and providing time-based reporting
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
from database import DatabaseManager
from data_processor import GPUDataProcessor
from dashboard import create_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gpu_thermal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database and data processor
db_manager = DatabaseManager()
data_processor = GPUDataProcessor(db_manager)

# Create dashboard
dashboard = create_dashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    return dashboard.index()

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Handle CSV file uploads"""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Process the uploaded file
                processed_count = data_processor.process_csv_file(filepath)
                return jsonify({
                    'message': f'Successfully processed {processed_count} records',
                    'filename': filename
                })
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        
        return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400
    
    return render_template('upload.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get GPU thermal data"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        gpu_id = request.args.get('gpu_id')
        issue_type = request.args.get('issue_type')  # 'throttled' or 'failed'
        
        # Get data from database
        data = db_manager.get_gpu_data(start_date, end_date, gpu_id, issue_type)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error retrieving data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """API endpoint to get summary statistics"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        stats = db_manager.get_summary_stats(start_date, end_date)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gpus')
def get_gpu_list():
    """API endpoint to get list of all GPUs"""
    try:
        gpus = db_manager.get_all_gpus()
        return jsonify(gpus)
    except Exception as e:
        logger.error(f"Error retrieving GPU list: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Initialize database tables
    db_manager.create_tables()
    
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True) 