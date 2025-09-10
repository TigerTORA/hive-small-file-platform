#!/usr/bin/env python3
"""
Test script to verify bulk cluster scan endpoint functionality
"""

import sys
import os
import asyncio

# Add backend directory to path
sys.path.append('/Users/luohu/new_project/hive-small-file-platform/backend')

from app.config.database import get_db
from app.models.cluster import Cluster
from app.api.clusters import scan_all_cluster_tables
from sqlalchemy.orm import Session

async def test_bulk_scan():
    """Test bulk cluster scan endpoint functionality"""
    print("Testing bulk cluster scan endpoint...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Test cluster scan with limited scope
        print("Testing bulk scan with cluster_id=1, max_tables=3, max_databases=2...")
        
        try:
            result = await scan_all_cluster_tables(
                cluster_id=1,
                max_tables_per_db=3,
                max_databases=2,
                db=db
            )
            
            print("✓ Bulk scan completed successfully!")
            print(f"  Cluster ID: {result.get('cluster_id')}")
            print(f"  Cluster Name: {result.get('cluster_name')}")
            print(f"  Total Databases Scanned: {len(result.get('scan_results', {}).get('database_results', []))}")
            
            # Show summary
            summary = result.get('scan_results', {}).get('summary', {})
            print(f"  Total Tables Scanned: {summary.get('total_tables_scanned', 0)}")
            print(f"  Total Files Found: {summary.get('total_files', 0)}")
            print(f"  Total Small Files: {summary.get('total_small_files', 0)}")
            
            # Show database results
            database_results = result.get('scan_results', {}).get('database_results', [])
            for db_result in database_results[:2]:  # Show first 2 databases
                db_name = db_result.get('database_name', 'Unknown')
                tables_scanned = len(db_result.get('table_results', []))
                print(f"  Database '{db_name}': {tables_scanned} tables scanned")
            
            return True
            
        except Exception as e:
            print(f"❌ Bulk scan failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_bulk_scan())
    sys.exit(0 if success else 1)