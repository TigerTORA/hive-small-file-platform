#!/usr/bin/env python3
"""
Test script to verify HybridTableScanner replacement functionality
"""

import os
import sys

# Add backend directory to path
sys.path.append("/Users/luohu/new_project/hive-small-file-platform/backend")

from app.config.database import get_db
from app.models.cluster import Cluster
from app.monitor.hybrid_table_scanner import HybridTableScanner


def test_hybrid_scanner():
    """Test HybridTableScanner functionality"""
    print("Testing HybridTableScanner replacement...")

    # Get database session
    db = next(get_db())

    try:
        # Get test cluster
        cluster = db.query(Cluster).filter(Cluster.id == 1).first()
        if not cluster:
            print("❌ No test cluster found (ID=1)")
            return False

        print(f"✓ Found test cluster: {cluster.name}")

        # Test HybridTableScanner initialization
        try:
            scanner = HybridTableScanner(cluster)
            print("✓ HybridTableScanner initialized successfully")
        except Exception as e:
            print(f"❌ HybridTableScanner initialization failed: {e}")
            return False

        # Test connections
        print("Testing connections...")
        try:
            results = scanner.test_connections()
            print("✓ Connection test completed:")
            print(f"  Overall status: {results['overall_status']}")

            # Show test results
            for service, result in results.get("tests", {}).items():
                status = "✓" if result.get("connected", False) else "❌"
                message = result.get("message", "No message")
                print(f"  {status} {service}: {message}")

            # Show logs if any
            if results.get("logs"):
                print("  Logs:")
                for log in results["logs"][-3:]:  # Show last 3 logs
                    print(f"    {log['level'].upper()}: {log['message']}")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_hybrid_scanner()
    sys.exit(0 if success else 1)
