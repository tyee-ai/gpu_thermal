#!/usr/bin/env python3
"""
Database Manager for GPU Thermal Reporting System
Handles all database operations for storing and retrieving GPU thermal data
Uses PostgreSQL with TimescaleDB for optimal time-series performance
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import os
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Float, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd

logger = logging.getLogger(__name__)

Base = declarative_base()

class GPUThermalEvent(Base):
    """SQLAlchemy model for GPU thermal events"""
    __tablename__ = 'gpu_thermal_events'
    
    id = Column(Integer, primary_key=True)
    node = Column(String(50), nullable=False)
    gpu_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    temperature = Column(Float)
    avg_temperature = Column(Float)
    issue_type = Column(String(20), nullable=False)  # 'throttled' or 'failed'
    reason = Column(String(100))
    date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class GPUMetadata(Base):
    """SQLAlchemy model for GPU metadata"""
    __tablename__ = 'gpu_metadata'
    
    id = Column(Integer, primary_key=True)
    gpu_id = Column(String(50), unique=True, nullable=False)
    node = Column(String(50))
    model = Column(String(100))
    location = Column(String(100))
    max_temp = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    def __init__(self, db_url: str = None):
        if db_url is None:
            # Default to PostgreSQL with TimescaleDB
            db_url = os.getenv('DATABASE_URL', 'postgresql://gpu_user:gpu_password@localhost:5432/gpu_thermal_db')
        
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_database()
    
    def init_database(self):
        """Initialize database connection and create tables with TimescaleDB"""
        try:
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            # Initialize TimescaleDB extension and create hypertable
            with self.engine.connect() as conn:
                # Enable TimescaleDB extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                
                # Convert to hypertable for time-series optimization
                conn.execute(text("""
                    SELECT create_hypertable('gpu_thermal_events', 'timestamp', 
                                           if_not_exists => TRUE,
                                           chunk_time_interval => INTERVAL '1 day')
                """))
                
                # Create indexes for better performance
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_gpu_thermal_events_gpu_id 
                    ON gpu_thermal_events(gpu_id)
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_gpu_thermal_events_issue_type 
                    ON gpu_thermal_events(issue_type)
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_gpu_thermal_events_node 
                    ON gpu_thermal_events(node)
                """))
                
                # Create time_bucket function for efficient time-based queries
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION get_time_buckets(
                        bucket_width INTERVAL,
                        start_time TIMESTAMPTZ DEFAULT NULL,
                        end_time TIMESTAMPTZ DEFAULT NULL
                    )
                    RETURNS TABLE (
                        bucket TIMESTAMPTZ,
                        event_count BIGINT,
                        avg_temperature DOUBLE PRECISION,
                        max_temperature DOUBLE PRECISION
                    )
                    AS $$
                    BEGIN
                        RETURN QUERY
                        SELECT 
                            time_bucket(bucket_width, timestamp) AS bucket,
                            COUNT(*) AS event_count,
                            AVG(temperature) AS avg_temperature,
                            MAX(temperature) AS max_temperature
                        FROM gpu_thermal_events
                        WHERE (start_time IS NULL OR timestamp >= start_time)
                          AND (end_time IS NULL OR timestamp <= end_time)
                        GROUP BY bucket
                        ORDER BY bucket;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                conn.commit()
                logger.info("Database initialized successfully with TimescaleDB")
                
        except SQLAlchemyError as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def create_tables(self):
        """Create database tables (alias for init_database)"""
        self.init_database()
    
    def insert_gpu_event(self, node: str, gpu_id: str, timestamp: datetime, 
                        temperature: float, avg_temperature: float = None,
                        issue_type: str = None, reason: str = None, 
                        date: datetime = None) -> int:
        """Insert a new GPU thermal event"""
        try:
            session = self.SessionLocal()
            
            # Determine issue type from reason if not provided
            if issue_type is None and reason:
                if 'throttled' in reason.lower():
                    issue_type = 'throttled'
                elif 'failed' in reason.lower():
                    issue_type = 'failed'
            
            event = GPUThermalEvent(
                node=node,
                gpu_id=gpu_id,
                timestamp=timestamp,
                temperature=temperature,
                avg_temperature=avg_temperature,
                issue_type=issue_type,
                reason=reason,
                date=date
            )
            
            session.add(event)
            session.commit()
            event_id = event.id
            session.close()
            
            logger.info(f"Inserted GPU event: {event_id} for GPU {gpu_id}")
            return event_id
            
        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            logger.error(f"Error inserting GPU event: {str(e)}")
            raise
    
    def insert_gpu_metadata(self, gpu_id: str, node: str = None, model: str = None, 
                           location: str = None, max_temp: float = None) -> int:
        """Insert or update GPU metadata"""
        try:
            session = self.SessionLocal()
            
            # Check if GPU metadata exists
            existing = session.query(GPUMetadata).filter(GPUMetadata.gpu_id == gpu_id).first()
            
            if existing:
                # Update existing record
                if node: existing.node = node
                if model: existing.model = model
                if location: existing.location = location
                if max_temp: existing.max_temp = max_temp
                existing.updated_at = datetime.utcnow()
                metadata_id = existing.id
            else:
                # Create new record
                metadata = GPUMetadata(
                    gpu_id=gpu_id,
                    node=node,
                    model=model,
                    location=location,
                    max_temp=max_temp
                )
                session.add(metadata)
                metadata_id = metadata.id
            
            session.commit()
            session.close()
            
            logger.info(f"Inserted/Updated GPU metadata for {gpu_id}")
            return metadata_id
            
        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            logger.error(f"Error inserting GPU metadata: {str(e)}")
            raise
    
    def get_gpu_data(self, start_date: str = None, end_date: str = None, 
                    gpu_id: str = None, issue_type: str = None, node: str = None) -> List[Dict]:
        """Retrieve GPU thermal data with optional filters"""
        try:
            session = self.SessionLocal()
            
            query = session.query(GPUThermalEvent, GPUMetadata).outerjoin(
                GPUMetadata, GPUThermalEvent.gpu_id == GPUMetadata.gpu_id
            )
            
            if start_date:
                query = query.filter(GPUThermalEvent.timestamp >= start_date)
            
            if end_date:
                query = query.filter(GPUThermalEvent.timestamp <= end_date)
            
            if gpu_id:
                query = query.filter(GPUThermalEvent.gpu_id == gpu_id)
            
            if issue_type:
                query = query.filter(GPUThermalEvent.issue_type == issue_type)
            
            if node:
                query = query.filter(GPUThermalEvent.node == node)
            
            results = query.order_by(GPUThermalEvent.timestamp.desc()).all()
            
            # Convert to list of dictionaries
            data = []
            for event, metadata in results:
                event_dict = {
                    'id': event.id,
                    'node': event.node,
                    'gpu_id': event.gpu_id,
                    'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                    'temperature': event.temperature,
                    'avg_temperature': event.avg_temperature,
                    'issue_type': event.issue_type,
                    'reason': event.reason,
                    'date': event.date.isoformat() if event.date else None,
                    'created_at': event.created_at.isoformat() if event.created_at else None,
                    'model': metadata.model if metadata else None,
                    'location': metadata.location if metadata else None
                }
                data.append(event_dict)
            
            session.close()
            return data
            
        except SQLAlchemyError as e:
            session.close()
            logger.error(f"Error retrieving GPU data: {str(e)}")
            raise
    
    def get_summary_stats(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get summary statistics for GPU thermal events using TimescaleDB functions"""
        try:
            with self.engine.connect() as conn:
                # Base conditions
                where_clause = "WHERE 1=1"
                params = {}
                
                if start_date:
                    where_clause += " AND timestamp >= :start_date"
                    params['start_date'] = start_date
                
                if end_date:
                    where_clause += " AND timestamp <= :end_date"
                    params['end_date'] = end_date
                
                # Total events
                result = conn.execute(text(f"""
                    SELECT COUNT(*) as total_events
                    FROM gpu_thermal_events
                    {where_clause}
                """), params)
                total_events = result.fetchone()[0]
                
                # Events by type
                result = conn.execute(text(f"""
                    SELECT issue_type, COUNT(*) as count
                    FROM gpu_thermal_events
                    {where_clause}
                    GROUP BY issue_type
                """), params)
                events_by_type = dict(result.fetchall())
                
                # Top GPUs by event count
                result = conn.execute(text(f"""
                    SELECT gpu_id, COUNT(*) as count
                    FROM gpu_thermal_events
                    {where_clause}
                    GROUP BY gpu_id
                    ORDER BY count DESC
                    LIMIT 10
                """), params)
                top_gpus = [{'gpu_id': row[0], 'count': row[1]} for row in result.fetchall()]
                
                # Temperature statistics
                result = conn.execute(text(f"""
                    SELECT AVG(temperature) as avg_temp, 
                           MAX(temperature) as max_temp,
                           MIN(temperature) as min_temp
                    FROM gpu_thermal_events
                    {where_clause}
                """), params)
                temp_stats = result.fetchone()
                
                # Events by node
                result = conn.execute(text(f"""
                    SELECT node, COUNT(*) as count
                    FROM gpu_thermal_events
                    {where_clause}
                    GROUP BY node
                    ORDER BY count DESC
                """), params)
                events_by_node = [{'node': row[0], 'count': row[1]} for row in result.fetchall()]
                
                return {
                    'total_events': total_events,
                    'events_by_type': events_by_type,
                    'top_gpus': top_gpus,
                    'events_by_node': events_by_node,
                    'temperature_stats': {
                        'average': float(temp_stats[0]) if temp_stats[0] else None,
                        'maximum': float(temp_stats[1]) if temp_stats[1] else None,
                        'minimum': float(temp_stats[2]) if temp_stats[2] else None
                    }
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving summary stats: {str(e)}")
            raise
    
    def get_all_gpus(self) -> List[Dict]:
        """Get list of all GPUs with their metadata"""
        try:
            session = self.SessionLocal()
            
            # Get distinct GPUs with event counts
            results = session.query(
                GPUThermalEvent.gpu_id,
                GPUMetadata.model,
                GPUMetadata.location,
                GPUMetadata.node
            ).outerjoin(
                GPUMetadata, GPUThermalEvent.gpu_id == GPUMetadata.gpu_id
            ).distinct().all()
            
            gpus = []
            for gpu_id, model, location, node in results:
                # Get event count for this GPU
                event_count = session.query(GPUThermalEvent).filter(
                    GPUThermalEvent.gpu_id == gpu_id
                ).count()
                
                # Get last event timestamp
                last_event = session.query(GPUThermalEvent.timestamp).filter(
                    GPUThermalEvent.gpu_id == gpu_id
                ).order_by(GPUThermalEvent.timestamp.desc()).first()
                
                gpus.append({
                    'gpu_id': gpu_id,
                    'model': model,
                    'location': location,
                    'node': node,
                    'event_count': event_count,
                    'last_event': last_event[0].isoformat() if last_event and last_event[0] else None
                })
            
            session.close()
            return sorted(gpus, key=lambda x: x['event_count'], reverse=True)
            
        except SQLAlchemyError as e:
            session.close()
            logger.error(f"Error retrieving GPU list: {str(e)}")
            raise
    
    def get_time_series_data(self, gpu_id: str = None, issue_type: str = None, 
                           node: str = None, interval: str = 'day') -> List[Dict]:
        """Get time series data for plotting using TimescaleDB time_bucket"""
        try:
            with self.engine.connect() as conn:
                # Determine bucket width based on interval
                if interval == 'hour':
                    bucket_width = "INTERVAL '1 hour'"
                elif interval == 'day':
                    bucket_width = "INTERVAL '1 day'"
                elif interval == 'week':
                    bucket_width = "INTERVAL '1 week'"
                else:
                    bucket_width = "INTERVAL '1 day'"
                
                where_clause = "WHERE 1=1"
                params = {}
                
                if gpu_id:
                    where_clause += " AND gpu_id = :gpu_id"
                    params['gpu_id'] = gpu_id
                
                if issue_type:
                    where_clause += " AND issue_type = :issue_type"
                    params['issue_type'] = issue_type
                
                if node:
                    where_clause += " AND node = :node"
                    params['node'] = node
                
                result = conn.execute(text(f"""
                    SELECT 
                        time_bucket({bucket_width}, timestamp) as time_period,
                        COUNT(*) as event_count,
                        AVG(temperature) as avg_temperature,
                        MAX(temperature) as max_temperature
                    FROM gpu_thermal_events
                    {where_clause}
                    GROUP BY time_period
                    ORDER BY time_period
                """), params)
                
                rows = result.fetchall()
                return [
                    {
                        'time_period': row[0].isoformat() if row[0] else None,
                        'event_count': row[1],
                        'avg_temperature': float(row[2]) if row[2] else None,
                        'max_temperature': float(row[3]) if row[3] else None
                    }
                    for row in rows
                ]
                
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving time series data: {str(e)}")
            raise
    
    def bulk_insert_events(self, events_data: List[Dict]) -> int:
        """Bulk insert multiple GPU events for better performance"""
        try:
            session = self.SessionLocal()
            
            events = []
            for event_data in events_data:
                event = GPUThermalEvent(**event_data)
                events.append(event)
            
            session.bulk_save_objects(events)
            session.commit()
            inserted_count = len(events)
            session.close()
            
            logger.info(f"Bulk inserted {inserted_count} GPU events")
            return inserted_count
            
        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            logger.error(f"Error bulk inserting GPU events: {str(e)}")
            raise 