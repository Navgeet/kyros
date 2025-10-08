#!/usr/bin/env python3
"""
Interactive Couchbase credential tester.
"""

import os
import getpass
import requests
from datetime import timedelta
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions


def test_credentials():
    """Interactive credential testing."""

    print("🔐 Interactive Couchbase Credential Test")
    print("=" * 50)

    # Get connection details
    host = input("Enter Couchbase host (default: 192.168.0.213): ").strip() or "192.168.0.213"
    connection = f"couchbase://{host}"

    print(f"Connection: {connection}")

    # Test management interface first
    mgmt_url = f"http://{host}:8091/pools"
    print(f"\n🧪 Testing management interface: {mgmt_url}")

    while True:
        print("\nEnter credentials (or 'quit' to exit):")
        username = input("Username: ").strip()

        if username.lower() == 'quit':
            break

        password = getpass.getpass("Password: ")

        if not username or not password:
            print("❌ Username and password cannot be empty")
            continue

        # Test HTTP authentication first
        try:
            print(f"Testing HTTP auth for {username}...")
            response = requests.get(mgmt_url, auth=(username, password), timeout=10)

            if response.status_code == 200:
                print("✅ HTTP authentication successful!")

                # Now test Couchbase SDK connection
                print("Testing Couchbase SDK connection...")
                try:
                    auth = PasswordAuthenticator(username, password)
                    options = ClusterOptions(auth)
                    cluster = Cluster(connection, options)
                    cluster.wait_until_ready(timeout=timedelta(seconds=10))

                    print("✅ Couchbase SDK connection successful!")
                    print(f"🎉 Working credentials found: {username}:{'*' * len(password)}")

                    # Save as environment variables
                    print("\n💾 To use these credentials, set:")
                    print(f"export COUCHBASE_USERNAME='{username}'")
                    print(f"export COUCHBASE_PASSWORD='{password}'")
                    print(f"export COUCHBASE_CONNECTION='{connection}'")

                    # Test bucket access
                    bucket_name = input(f"\nTest bucket access? Enter bucket name (default: foo): ").strip() or "foo"
                    try:
                        bucket = cluster.bucket(bucket_name)
                        print(f"✅ Bucket '{bucket_name}' accessible")

                        # Test simple query
                        test_query = f"SELECT META().id FROM `{bucket_name}` LIMIT 1"
                        print(f"Testing query: {test_query}")
                        result = cluster.query(test_query)
                        rows = list(result)
                        print(f"✅ Query successful, found {len(rows)} test records")

                    except Exception as bucket_e:
                        print(f"⚠️ Bucket test failed: {bucket_e}")
                        # List available buckets
                        try:
                            bucket_manager = cluster.buckets()
                            buckets = bucket_manager.get_all_buckets()
                            bucket_names = list(buckets.keys())
                            print(f"Available buckets: {bucket_names}")
                        except Exception as list_e:
                            print(f"Cannot list buckets: {list_e}")

                    return True

                except Exception as sdk_e:
                    print(f"❌ Couchbase SDK connection failed: {sdk_e}")

            elif response.status_code == 401:
                print("❌ HTTP authentication failed (401 Unauthorized)")
            else:
                print(f"❌ HTTP request failed with status: {response.status_code}")

        except Exception as e:
            print(f"❌ HTTP test failed: {e}")

    return False


if __name__ == "__main__":
    if test_credentials():
        print("\n🎉 Success! You can now use RAG functionality.")
    else:
        print("\n❌ No working credentials found.")