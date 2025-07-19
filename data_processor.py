#!/usr/bin/env python3
"""
Data Processor for GPU Thermal Reporting System
Handles CSV file ingestion and data processing
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Any
import os
from database import DatabaseManager

logger = logging.getLogger(__name__)

class GPUDataProcessor:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Expected CSV column mappings for the specific format
        self.column_mappings = {
            'node': ['node', 'host', 'server'],
            'timestamp': ['timestamp', 'time', 'datetime'],
            'gpu_id': ['gpu_id', 'gpu', 'device_id', 'device'],
            'temperature': ['temp', 'temperature', 'gpu_temp', 'thermal'],
            'avg_temperature': ['avg_temp', 'average_temp', 'avg_temperature'],
            'reason': ['reason', 'issue_type', 'type', 'status', 'event_type'],
            'date': ['date', 'event_date']
        }
    
    def process_csv_file(self, filepath: str) -> int:
        """Process a CSV file and insert data into the database"""
        try:
            logger.info(f"Processing CSV file: {filepath}")
            
            # Read CSV file
            df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(df)} rows from CSV file")
            
            # Map columns to expected names
            mapped_df = self._map_columns(df)
            
            # Validate and clean data
            cleaned_df = self._clean_data(mapped_df)
            
            # Insert data into database using bulk insert for better performance
            processed_count = self._bulk_insert_data(cleaned_df)
            
            logger.info(f"Successfully processed {processed_count} records")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing CSV file {filepath}: {str(e)}")
            raise
    
    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map CSV columns to expected column names"""
        mapped_df = df.copy()
        
        # Create a mapping dictionary
        column_mapping = {}
        
        for expected_col, possible_names in self.column_mappings.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    column_mapping[possible_name] = expected_col
                    break
        
        # Rename columns
        if column_mapping:
            mapped_df = mapped_df.rename(columns=column_mapping)
        
        # Log column mapping
        logger.info(f"Column mapping: {column_mapping}")
        logger.info(f"Available columns after mapping: {list(mapped_df.columns)}")
        
        return mapped_df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate the data"""
        cleaned_df = df.copy()
        
        # Ensure required columns exist
        required_columns = ['node', 'gpu_id', 'timestamp', 'reason']
        missing_columns = [col for col in required_columns if col not in cleaned_df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Clean timestamp column
        if 'timestamp' in cleaned_df.columns:
            cleaned_df['timestamp'] = pd.to_datetime(cleaned_df['timestamp'], errors='coerce')
            # Remove rows with invalid timestamps
            cleaned_df = cleaned_df.dropna(subset=['timestamp'])
        
        # Clean date column if present
        if 'date' in cleaned_df.columns:
            cleaned_df['date'] = pd.to_datetime(cleaned_df['date'], errors='coerce')
        
        # Clean temperature columns
        if 'temperature' in cleaned_df.columns:
            cleaned_df['temperature'] = pd.to_numeric(cleaned_df['temperature'], errors='coerce')
        
        if 'avg_temperature' in cleaned_df.columns:
            cleaned_df['avg_temperature'] = pd.to_numeric(cleaned_df['avg_temperature'], errors='coerce')
        
        # Validate and standardize reason/issue_type values
        if 'reason' in cleaned_df.columns:
            cleaned_df['reason'] = cleaned_df['reason'].str.strip()
            
            # Map common variations to standard values
            reason_mapping = {
                'thermally failed': 'failed',
                'thermal failure': 'failed',
                'throttled': 'throttled',
                'thermal throttling': 'throttled',
                'throttling': 'throttled'
            }
            
            cleaned_df['reason'] = cleaned_df['reason'].str.lower().map(
                lambda x: reason_mapping.get(x, x)
            )
            
            # Filter out invalid reason types
            valid_reasons = ['throttled', 'failed']
            cleaned_df = cleaned_df[cleaned_df['reason'].isin(valid_reasons)]
        
        # Clean node and gpu_id columns
        if 'node' in cleaned_df.columns:
            cleaned_df['node'] = cleaned_df['node'].astype(str).str.strip()
        
        if 'gpu_id' in cleaned_df.columns:
            cleaned_df['gpu_id'] = cleaned_df['gpu_id'].astype(str).str.strip()
        
        logger.info(f"Cleaned data: {len(cleaned_df)} rows remaining")
        return cleaned_df
    
    def _bulk_insert_data(self, df: pd.DataFrame) -> int:
        """Bulk insert cleaned data into the database for better performance"""
        try:
            # Prepare data for bulk insert
            events_data = []
            
            for _, row in df.iterrows():
                try:
                    # Determine issue type from reason
                    issue_type = None
                    if 'throttled' in str(row.get('reason', '')).lower():
                        issue_type = 'throttled'
                    elif 'failed' in str(row.get('reason', '')).lower():
                        issue_type = 'failed'
                    
                    event_data = {
                        'node': row['node'],
                        'gpu_id': row['gpu_id'],
                        'timestamp': row['timestamp'],
                        'temperature': row.get('temperature'),
                        'avg_temperature': row.get('avg_temperature'),
                        'issue_type': issue_type,
                        'reason': row.get('reason'),
                        'date': row.get('date')
                    }
                    
                    events_data.append(event_data)
                    
                except Exception as e:
                    logger.error(f"Error preparing row for insertion: {str(e)}")
                    continue
            
            # Bulk insert events
            if events_data:
                processed_count = self.db_manager.bulk_insert_events(events_data)
                
                # Insert GPU metadata for unique GPUs
                unique_gpus = df[['gpu_id', 'node']].drop_duplicates()
                for _, gpu_row in unique_gpus.iterrows():
                    try:
                        self.db_manager.insert_gpu_metadata(
                            gpu_id=gpu_row['gpu_id'],
                            node=gpu_row['node']
                        )
                    except Exception as e:
                        logger.error(f"Error inserting GPU metadata for {gpu_row['gpu_id']}: {str(e)}")
                
                return processed_count
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error bulk inserting data: {str(e)}")
            raise
    
    def process_directory(self, directory_path: str) -> Dict[str, int]:
        """Process all CSV files in a directory"""
        results = {}
        
        try:
            for filename in os.listdir(directory_path):
                if filename.endswith('.csv'):
                    filepath = os.path.join(directory_path, filename)
                    try:
                        count = self.process_csv_file(filepath)
                        results[filename] = count
                    except Exception as e:
                        logger.error(f"Error processing {filename}: {str(e)}")
                        results[filename] = 0
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing directory {directory_path}: {str(e)}")
            raise
    
    def validate_csv_format(self, filepath: str) -> Dict[str, Any]:
        """Validate CSV file format and return validation results"""
        try:
            df = pd.read_csv(filepath)
            
            validation_result = {
                'file_path': filepath,
                'total_rows': len(df),
                'columns': list(df.columns),
                'column_mapping': {},
                'missing_required': [],
                'sample_data': df.head(3).to_dict('records'),
                'data_types': df.dtypes.to_dict()
            }
            
            # Check column mapping
            for expected_col, possible_names in self.column_mappings.items():
                for possible_name in possible_names:
                    if possible_name in df.columns:
                        validation_result['column_mapping'][expected_col] = possible_name
                        break
            
            # Check for missing required columns
            required_columns = ['node', 'gpu_id', 'timestamp', 'reason']
            for col in required_columns:
                if col not in validation_result['column_mapping']:
                    validation_result['missing_required'].append(col)
            
            # Check for unique values in key columns
            if 'gpu_id' in validation_result['column_mapping']:
                gpu_id_col = validation_result['column_mapping']['gpu_id']
                validation_result['unique_gpus'] = df[gpu_id_col].nunique()
            
            if 'node' in validation_result['column_mapping']:
                node_col = validation_result['column_mapping']['node']
                validation_result['unique_nodes'] = df[node_col].nunique()
            
            return validation_result
            
        except Exception as e:
            return {
                'file_path': filepath,
                'error': str(e),
                'valid': False
            }
    
    def create_sample_csv(self, output_path: str = 'sample_gpu_data.csv'):
        """Create a sample CSV file with the expected format"""
        sample_data = {
            'node': ['10.4.21.8', '10.4.21.8', '10.4.21.62', '10.4.21.62'],
            'timestamp': ['2025-03-17', '2025-03-18', '2025-04-15', '2025-04-16'],
            'gpu_id': ['GPU_28', 'GPU_28', 'GPU_22', 'GPU_22'],
            'temp': [44.0, 45.0, 86.24, 91.23],
            'avg_temp': [28.08, 28.61, None, None],
            'reason': ['Thermally Failed', 'Thermally Failed', 'Throttled', 'Throttled'],
            'date': ['2025-03-17', '2025-03-18', '2025-04-15', '2025-04-16']
        }
        
        df = pd.DataFrame(sample_data)
        df.to_csv(output_path, index=False)
        logger.info(f"Created sample CSV file: {output_path}")
        return output_path 