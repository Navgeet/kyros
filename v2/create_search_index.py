#!/usr/bin/env python3
"""
Helper script to create the required Couchbase search index for RAG functionality.
"""

import os
import json
import requests
from datetime import timedelta
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions


def create_search_index():
    """Create the search index required for vector search."""

    # Configuration
    connection = os.getenv("COUCHBASE_CONNECTION", "couchbase://192.168.0.213")
    username = os.getenv("COUCHBASE_USERNAME", "admin")
    password = os.getenv("COUCHBASE_PASSWORD", "admin123")
    bucket_name = os.getenv("COUCHBASE_BUCKET", "foo")
    scope_name = os.getenv("COUCHBASE_SCOPE", "bar")
    collection_name = os.getenv("COUCHBASE_COLLECTION", "learnings")
    search_index_name = os.getenv("COUCHBASE_SEARCH_INDEX", "learnings")

    print("🔍 Creating Couchbase Search Index for RAG")
    print("=" * 50)
    print(f"Connection: {connection}")
    print(f"Username: {username}")
    print(f"Bucket: {bucket_name}")
    print(f"Scope: {scope_name}")
    print(f"Collection: {collection_name}")
    print(f"Search Index: {search_index_name}")
    print()

    # Extract host from connection string
    host = connection.replace("couchbase://", "").replace("couchbases://", "")

    # Search index definition for vector search
    index_definition = {
        "type": "fulltext-index",
        "name": search_index_name,
        "sourceName": bucket_name,
        "sourceType": "couchbase",
        "planParams": {
            "maxPartitionsPerPIndex": 1024,
            "indexPartitions": 1
        },
        "params": {
            "doc_config": {
                "docid_prefix_delim": "",
                "docid_regexp": "",
                "mode": "scope.collection.type_field",
                "type_field": "type"
            },
            "mapping": {
                "analysis": {},
                "default_analyzer": "standard",
                "default_datetime_parser": "dateTimeOptional",
                "default_field": {
                    "dynamic": False,
                    "enabled": False
                },
                "default_mapping": {
                    "dynamic": False,
                    "enabled": False
                },
                "default_type": "_default",
                "docvalues_dynamic": False,
                "index_dynamic": False,
                "store_dynamic": False,
                "type_field": "_type",
                "types": {
                    f"{scope_name}.{collection_name}": {
                        "dynamic": False,
                        "enabled": True,
                        "properties": {
                            "learning": {
                                "dynamic": False,
                                "enabled": True,
                                "fields": [
                                    {
                                        "analyzer": "",
                                        "dims": 0,
                                        "docvalues": True,
                                        "include_in_all": True,
                                        "include_term_vectors": True,
                                        "index": True,
                                        "name": "learning",
                                        "similarity": "BM25",
                                        "store": True,
                                        "type": "text"
                                    }
                                ]
                            },
                            "example": {
                                "dynamic": False,
                                "enabled": True,
                                "fields": [
                                    {
                                        "analyzer": "",
                                        "dims": 0,
                                        "docvalues": True,
                                        "include_in_all": True,
                                        "include_term_vectors": True,
                                        "index": True,
                                        "name": "example",
                                        "similarity": "BM25",
                                        "store": True,
                                        "type": "text"
                                    }
                                ]
                            },
                            "example_embed": {
                                "dynamic": False,
                                "enabled": True,
                                "fields": [
                                    {
                                        "dims": 1536,  # OpenAI embedding dimension
                                        "index": True,
                                        "name": "example_embed",
                                        "similarity": "dot_product",
                                        "store": True,
                                        "type": "vector",
                                        "vector_index_optimized_for": "recall"
                                    }
                                ]
                            },
                            "learning_embed": {
                                "dynamic": False,
                                "enabled": True,
                                "fields": [
                                    {
                                        "dims": 1536,  # OpenAI embedding dimension
                                        "index": True,
                                        "name": "learning_embed",
                                        "similarity": "dot_product",
                                        "store": True,
                                        "type": "vector",
                                        "vector_index_optimized_for": "recall"
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            "store": {
                "indexType": "scorch",
                "segmentVersion": 15
            }
        },
        "sourceParams": {}
    }

    try:
        # Create the search index via REST API
        api_url = f"http://{host}:8094/api/index/{search_index_name}"

        print(f"🔧 Creating search index via: {api_url}")
        print("📋 Index definition:")
        print(json.dumps(index_definition, indent=2)[:500] + "...")
        print()

        response = requests.put(
            api_url,
            json=index_definition,
            auth=(username, password),
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            print("✅ Search index created successfully!")
            print()
            print("🔄 Waiting for index to be ready...")

            # Wait for index to be ready
            import time
            for i in range(30):  # Wait up to 30 seconds
                status_response = requests.get(
                    f"http://{host}:8094/api/index/{search_index_name}",
                    auth=(username, password)
                )

                if status_response.status_code == 200:
                    index_info = status_response.json()
                    if index_info.get("indexDef", {}).get("name") == search_index_name:
                        print("✅ Index is ready!")
                        break

                print(f"⏳ Waiting... ({i+1}/30)")
                time.sleep(1)
            else:
                print("⚠️ Index creation may still be in progress")

            print()
            print("🎉 Setup complete! You can now test vector search with:")
            print("python test_couchbase_connection.py")

            return True

        elif response.status_code == 400:
            error_info = response.json()
            if "already exists" in str(error_info):
                print("⚠️ Search index already exists")
                return True
            else:
                print(f"❌ Index creation failed: {error_info}")
        else:
            print(f"❌ Index creation failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Error creating search index: {e}")

        print()
        print("🔧 Manual Setup Instructions:")
        print("=" * 50)
        print("1. Open Couchbase Web UI: http://192.168.0.213:8091")
        print("2. Go to Search → Add Index")
        print("3. Set these values:")
        print(f"   - Index Name: {search_index_name}")
        print(f"   - Bucket: {bucket_name}")
        print(f"   - Scope: {scope_name}")
        print(f"   - Collection: {collection_name}")
        print("4. In the mapping section, add these fields:")
        print("   - learning (text field)")
        print("   - example (text field)")
        print("   - example_embed (vector field, 1536 dimensions, dot_product)")
        print("   - learning_embed (vector field, 1536 dimensions, dot_product)")
        print("5. Create the index and wait for it to be ready")

    return False


if __name__ == "__main__":
    success = create_search_index()
    exit(0 if success else 1)