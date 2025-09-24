#!/usr/bin/env python3
"""
Test API endpoints with populated test data
"""

import json
import sys

import requests


def test_api_endpoints():
    """Test key API endpoints that drive the monitoring dashboard"""
    print("Testing API endpoints with populated test data...")

    base_url = "http://localhost:8000"
    endpoints = [
        ("/health", "Health check"),
        ("/api/v1/dashboard/summary", "Dashboard summary"),
        ("/api/v1/dashboard/table-file-counts?limit=5", "Table file counts"),
        ("/api/v1/dashboard/cluster-stats", "Cluster statistics"),
        ("/api/v1/tables/metrics?cluster_id=1", "Table metrics for cluster 1"),
        (
            "/api/v1/tables/small-files?cluster_id=1",
            "Small files summary for cluster 1",
        ),
    ]

    success_count = 0
    total_count = len(endpoints)

    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"Testing {description}: {endpoint}")

            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                # Show summary of response
                if isinstance(data, dict):
                    if "total_tables" in data:
                        print(f"  ✓ Total tables: {data.get('total_tables', 0)}")
                    if "total_files" in data:
                        print(f"  ✓ Total files: {data.get('total_files', 0)}")
                    if "total_small_files" in data:
                        print(
                            f"  ✓ Total small files: {data.get('total_small_files', 0)}"
                        )
                elif isinstance(data, list):
                    print(f"  ✓ Returned {len(data)} items")

                success_count += 1
                print(f"  ✅ Status: {response.status_code}")

            else:
                print(f"  ❌ Status: {response.status_code}")
                print(f"     Response: {response.text[:200]}...")

        except Exception as e:
            print(f"  ❌ Error: {e}")

        print()

    print(f"API Test Results: {success_count}/{total_count} endpoints successful")
    return success_count == total_count


if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)
