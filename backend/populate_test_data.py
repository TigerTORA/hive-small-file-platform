#!/usr/bin/env python3
"""
Populate test data for monitoring dashboard
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add backend directory to path
sys.path.append('/Users/luohu/new_project/hive-small-file-platform/backend')

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from sqlalchemy.orm import Session
from sqlalchemy import func

def populate_test_data():
    """Populate test table metrics data"""
    print("Populating test data for table monitoring...")
    
    db = next(get_db())
    
    try:
        # Get test cluster
        cluster = db.query(Cluster).filter(Cluster.id == 1).first()
        if not cluster:
            print("❌ No test cluster found (ID=1)")
            return False
        
        print(f"✓ Found cluster: {cluster.name}")
        
        # Clear existing table metrics
        db.query(TableMetric).filter(TableMetric.cluster_id == 1).delete()
        db.commit()
        print("✓ Cleared existing table metrics")
        
        # Generate sample table data
        databases = ['default', 'sales', 'marketing', 'analytics']
        table_types = ['customer', 'orders', 'products', 'events', 'logs', 'metrics']
        
        total_tables = 0
        
        for db_name in databases:
            tables_in_db = random.randint(3, 8)
            
            for i in range(tables_in_db):
                table_name = f"{random.choice(table_types)}_{i+1}"
                
                # Generate realistic file metrics
                total_files = random.randint(10, 1000)
                small_file_ratio = random.uniform(0.1, 0.8)
                small_files = int(total_files * small_file_ratio)
                
                # Generate size data
                avg_file_size = random.randint(1024 * 1024, 500 * 1024 * 1024)  # 1MB to 500MB
                total_size = total_files * avg_file_size + random.randint(-1000, 1000) * 1024 * 1024
                
                # Create table metric
                table_metric = TableMetric(
                    cluster_id=cluster.id,
                    database_name=db_name,
                    table_name=table_name,
                    table_path=f"/warehouse/tablespace/managed/hive/{db_name}.db/{table_name}",
                    total_files=total_files,
                    small_files=small_files,
                    total_size=total_size,
                    avg_file_size=avg_file_size,
                    is_partitioned=random.choice([0, 1]),
                    partition_count=random.randint(0, 50) if random.choice([True, False]) else 0,
                    scan_time=datetime.now() - timedelta(hours=random.randint(0, 24)),
                    scan_duration=random.uniform(0.5, 30.0)
                )
                
                db.add(table_metric)
                total_tables += 1
        
        db.commit()
        print(f"✓ Created {total_tables} table metrics across {len(databases)} databases")
        
        # Verify data was created
        count = db.query(TableMetric).filter(TableMetric.cluster_id == 1).count()
        total_files = db.query(TableMetric).filter(TableMetric.cluster_id == 1).with_entities(
            func.sum(TableMetric.total_files)).scalar() or 0
        total_small_files = db.query(TableMetric).filter(TableMetric.cluster_id == 1).with_entities(
            func.sum(TableMetric.small_files)).scalar() or 0
        
        print(f"✓ Verification: {count} tables, {total_files} total files, {total_small_files} small files")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to populate test data: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = populate_test_data()
    sys.exit(0 if success else 1)