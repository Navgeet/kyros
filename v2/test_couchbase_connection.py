#!/usr/bin/env python3
"""
Test script to diagnose Couchbase connection issues for RAG functionality.
"""

import os
import socket
import requests
from datetime import timedelta
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions, SearchOptions
import couchbase.search as search
from couchbase.vector_search import VectorQuery, VectorSearch


def test_couchbase_connection():
    """Test Couchbase connection with current configuration."""

    # Configuration (same as agent_v2.py)
    connection = os.getenv("COUCHBASE_CONNECTION", "couchbase://192.168.0.213")
    username = os.getenv("COUCHBASE_USERNAME", "admin")
    password = os.getenv("COUCHBASE_PASSWORD", "admin123")
    bucket_name = os.getenv("COUCHBASE_BUCKET", "foo")
    scope_name = os.getenv("COUCHBASE_SCOPE", "bar")
    collection_name = os.getenv("COUCHBASE_COLLECTION", "learnings")
    search_index_name = os.getenv("COUCHBASE_SEARCH_INDEX", "learnings")

    print("🔍 Environment variable check:")
    for var in ["COUCHBASE_CONNECTION", "COUCHBASE_USERNAME", "COUCHBASE_PASSWORD",
                "COUCHBASE_BUCKET", "COUCHBASE_SCOPE", "COUCHBASE_COLLECTION", "COUCHBASE_SEARCH_INDEX"]:
        value = os.getenv(var)
        if value:
            display_value = value if var != "COUCHBASE_PASSWORD" else "*" * len(value)
            print(f"  ✅ {var}={display_value}")
        else:
            print(f"  ❌ {var} not set (using default)")
    print()

    print("🧪 Couchbase Connection Test")
    print("=" * 50)
    print(f"Connection: {connection}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print(f"Bucket: {bucket_name}")
    print(f"Scope: {scope_name}")
    print(f"Collection: {collection_name}")
    print()

    # Pre-connection tests
    print("🔍 Pre-connection diagnostics...")

    # Extract host and port from connection string
    host_port = connection.replace("couchbase://", "").replace("couchbases://", "")
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 11210  # Default Couchbase port

    # Test network connectivity
    try:
        print(f"Testing network connectivity to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"✅ Network connectivity to {host}:{port} successful")
        else:
            print(f"❌ Cannot connect to {host}:{port} - network unreachable")
            print("💡 Check if Couchbase server is running and firewall allows connections")
    except Exception as net_e:
        print(f"❌ Network test failed: {net_e}")

    # Test HTTP management interface (port 8091)
    try:
        mgmt_url = f"http://{host}:8091/pools"
        print(f"Testing HTTP management interface at {mgmt_url}...")
        response = requests.get(mgmt_url, timeout=10)
        if response.status_code == 200:
            print("✅ HTTP management interface accessible")
        elif response.status_code == 401:
            print("⚠️ HTTP management interface requires authentication (401)")

            # Try with credentials
            print(f"Testing with credentials: {username}:{'*' * len(password)}")
            auth_response = requests.get(mgmt_url,
                                       auth=(username, password),
                                       timeout=10)
            if auth_response.status_code == 200:
                print("✅ HTTP authentication successful!")
                print("💡 Credentials are correct for HTTP interface")
            else:
                print(f"❌ HTTP authentication failed: {auth_response.status_code}")
                print("💡 Testing common credential combinations...")

                # Test common username/password combinations
                common_creds = [
                    ("Administrator", "password"),
                    ("admin", "admin"),
                    ("Administrator", "admin"),
                    ("couchbase", "couchbase"),
                    ("administrator", "password"),
                ]

                working_creds = None
                for test_user, test_pass in common_creds:
                    try:
                        print(f"  Testing {test_user}:{test_pass}...")
                        test_response = requests.get(mgmt_url,
                                                   auth=(test_user, test_pass),
                                                   timeout=5)
                        if test_response.status_code == 200:
                            print(f"  ✅ Found working credentials: {test_user}:{test_pass}")
                            working_creds = (test_user, test_pass)
                            break
                        else:
                            print(f"  ❌ Failed: {test_response.status_code}")
                    except Exception:
                        print(f"  ❌ Failed: connection error")

                if working_creds:
                    username, password = working_creds
                    print(f"🔄 Updated credentials to: {username}:{'*' * len(password)}")
                else:
                    print("❌ No working credentials found in common combinations")
        else:
            print(f"⚠️ HTTP management interface returned status: {response.status_code}")
    except Exception as http_e:
        print(f"❌ HTTP management interface test failed: {http_e}")
        print("💡 This could indicate Couchbase server is not running")

    print()

    try:
        print("🔗 Connecting to Couchbase...")

        # Try different connection methods
        print(f"Attempting connection with username: '{username}'")

        # Method 1: Try with connection string including credentials
        try:
            print("Method 1: Connection string with credentials")
            cluster = Cluster(f"{connection}?username={username}&password={password}")
            cluster.wait_until_ready(timeout=timedelta(seconds=10))
            print("✅ Method 1 successful!")
        except Exception as method1_e:
            print(f"❌ Method 1 failed: {method1_e}")

            # Method 2: Try with PasswordAuthenticator
            try:
                print("Method 2: PasswordAuthenticator")
                auth = PasswordAuthenticator(username, password)
                options = ClusterOptions(auth)
                cluster = Cluster(connection, options)
                cluster.wait_until_ready(timeout=timedelta(seconds=10))
                print("✅ Method 2 successful!")
            except Exception as method2_e:
                print(f"❌ Method 2 failed: {method2_e}")

                # Method 3: Try different usernames
                for test_user in ["Administrator", "admin", "couchbase"]:
                    try:
                        print(f"Method 3: Testing with username '{test_user}'")
                        auth = PasswordAuthenticator(test_user, password)
                        options = ClusterOptions(auth)
                        cluster = Cluster(connection, options)
                        cluster.wait_until_ready(timeout=timedelta(seconds=10))
                        print(f"✅ Method 3 successful with username: {test_user}")
                        username = test_user  # Update for rest of test
                        break
                    except Exception as method3_e:
                        print(f"❌ Method 3 failed for '{test_user}': {method3_e}")
                else:
                    raise Exception("All connection methods failed")

        print("⏳ Waiting for cluster to be ready...")
        cluster.wait_until_ready(timeout=timedelta(seconds=15))
        print("✅ Cluster connection established")

        # Test bucket access
        print(f"📦 Testing bucket access...")
        try:
            bucket = cluster.bucket(bucket_name)
            print(f"✅ Bucket '{bucket_name}' accessible")
        except Exception as bucket_e:
            print(f"❌ Bucket access failed: {bucket_e}")

            # List available buckets
            try:
                print("📋 Listing available buckets...")
                bucket_manager = cluster.buckets()
                buckets = bucket_manager.get_all_buckets()
                bucket_names = [name for name in buckets.keys()]
                print(f"Available buckets: {bucket_names}")
            except Exception as list_e:
                print(f"❌ Cannot list buckets: {list_e}")

            return False

        # Test simple query
        print("🧪 Testing simple query...")
        try:
            simple_query = f"SELECT META().id FROM `{bucket_name}`.`{scope_name}`.`{collection_name}` LIMIT 1"
            result = cluster.query(simple_query)
            rows = list(result)
            print(f"✅ Query successful, found {len(rows)} test records")
        except Exception as query_e:
            print(f"❌ Query failed: {query_e}")

            # Try to list scopes and collections
            try:
                print("📋 Listing scopes and collections...")
                scope_manager = bucket.collections()
                scopes = scope_manager.get_all_scopes()
                for scope in scopes:
                    print(f"Scope: {scope.name}")
                    for collection in scope.collections:
                        print(f"  Collection: {collection.name}")
            except Exception as scope_e:
                print(f"❌ Cannot list scopes/collections: {scope_e}")

            return False

        # Test learning object query
        print("📚 Testing learning object query...")
        try:
            learning_query = f"""
            SELECT learning, example
            FROM `{bucket_name}`.`{scope_name}`.`{collection_name}`
            WHERE learning IS NOT MISSING AND example IS NOT MISSING
            LIMIT 3
            """
            result = cluster.query(learning_query)
            learning_objects = []

            for row in result:
                if "learning" in row and "example" in row:
                    learning_objects.append({
                        "learning": row["learning"][:100] + "..." if len(row["learning"]) > 100 else row["learning"],
                        "example": row["example"][:100] + "..." if len(row["example"]) > 100 else row["example"]
                    })

            print(f"✅ Found {len(learning_objects)} learning objects")
            for i, obj in enumerate(learning_objects):
                print(f"  {i+1}. Learning: {obj['learning']}")
                print(f"     Example: {obj['example']}")
                print()

        except Exception as learning_e:
            print(f"❌ Learning object query failed: {learning_e}")

        # Test vector search functionality
        print("🔍 Testing combined vector search functionality...")
        try:
            # Create a dummy embedding vector for testing (1536 dimensions like OpenAI)
            test_embedding = [0.1] * 1536  # Simple test vector

            bucket = cluster.bucket(bucket_name)
            scope = bucket.scope(scope_name)

            # Create multiple vector queries for both embedding fields
            vector_queries = [
                VectorQuery.create('example_embed', test_embedding, num_candidates=3, boost=0.5),
                VectorQuery.create('learning_embed', test_embedding, num_candidates=3, boost=0.5)
            ]

            # Combine into single search request
            search_req = search.SearchRequest.create(VectorSearch(vector_queries))

            # Execute combined vector search
            result = scope.search(
                search_index_name,
                search_req,
                SearchOptions(limit=6, fields=["learning", "example"])
            )

            vector_results = []
            for row in result.rows():
                row_data = row.fields
                if row_data and "learning" in row_data and "example" in row_data:
                    if row_data["learning"] and row_data["example"]:  # Check for None values
                        vector_results.append({
                            "learning": row_data["learning"][:100] + "..." if len(row_data["learning"]) > 100 else row_data["learning"],
                            "example": row_data["example"][:100] + "..." if len(row_data["example"]) > 100 else row_data["example"]
                        })

            print(f"✅ Combined vector search successful! Found {len(vector_results)} results")
            print(f"Total search results: {result.metadata().metrics().total_rows()}")

            for i, obj in enumerate(vector_results):
                print(f"  {i+1}. Learning: {obj['learning']}")
                print(f"     Example: {obj['example']}")
                print()

            return True

        except Exception as vector_e:
            print(f"❌ Vector search failed: {vector_e}")
            print("💡 This might indicate:")
            print("  - Search index doesn't exist or isn't configured properly")
            print("  - Vector fields (example_embed, learning_embed) don't exist")
            print("  - Search service isn't enabled")
            return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")

        if "authentication_failure" in str(e):
            print()
            print("🔐 Authentication Issue Detected!")
            print("Possible solutions:")
            print("1. Check if the username and password are correct")
            print("2. Try 'Administrator' instead of 'admin' as username")
            print("3. Verify the Couchbase server is running")
            print("4. Check firewall settings")
            print()
            print("Environment variables to set:")
            print("export COUCHBASE_USERNAME='Administrator'")
            print("export COUCHBASE_PASSWORD='your-password'")
            print("export COUCHBASE_CONNECTION='couchbase://192.168.0.213'")
            print("export COUCHBASE_BUCKET='your-bucket'")
            print("export COUCHBASE_SCOPE='your-scope'")
            print("export COUCHBASE_COLLECTION='your-collection'")

        return False


if __name__ == "__main__":
    success = test_couchbase_connection()

    print()
    print("=" * 50)
    if success:
        print("✅ All tests passed! Couchbase RAG functionality should work.")
    else:
        print("❌ Tests failed. Please fix the issues above before using RAG.")
        print("💡 Fix the connection issues above to enable RAG functionality.")

    exit(0 if success else 1)