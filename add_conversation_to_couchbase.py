#!/usr/bin/env python3

import argparse
import json
import uuid
from datetime import datetime
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions


def load_conversation_snapshot(file_path):
    """Load conversation snapshot from JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Conversation snapshot file not found: {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in conversation snapshot file: {file_path}")


def connect_to_couchbase(connection_string, username, password):
    """Connect to CouchBase cluster."""
    auth = PasswordAuthenticator(username, password)
    options = ClusterOptions(auth)
    cluster = Cluster(connection_string, options)
    return cluster


def add_conversation_to_couchbase(cluster, bucket_name, scope_name, collection_name,
                                 conversation_data, session_id=None):
    """Add conversation to CouchBase collection."""
    bucket = cluster.bucket(bucket_name)
    scope = bucket.scope(scope_name)
    collection = scope.collection(collection_name)

    if session_id is None:
        session_id = str(uuid.uuid4())

    record = {
        "session_id": session_id,
        "conversation": conversation_data['conversation_history'],
        "timestamp": datetime.utcnow().isoformat(),
        "type": "conversation_history"
    }

    document_id = f"conversation_{session_id}"

    try:
        collection.upsert(document_id, record)
        return document_id, session_id
    except Exception as e:
        raise Exception(f"Failed to insert conversation into CouchBase: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Add conversation history to CouchBase')
    parser.add_argument('--bucket', required=True, help='CouchBase bucket name')
    parser.add_argument('--scope', required=True, help='CouchBase scope name')
    parser.add_argument('--collection', required=True, help='CouchBase collection name')
    parser.add_argument('--conversation-file', required=True,
                       help='Path to conversation snapshot JSON file')
    parser.add_argument('--connection-string', default='couchbase://localhost',
                       help='CouchBase connection string (default: couchbase://localhost)')
    parser.add_argument('--username', default='admin',
                       help='CouchBase username (default: admin)')
    parser.add_argument('--password', default='password',
                       help='CouchBase password (default: password)')
    parser.add_argument('--session-id',
                       help='Custom session ID (default: auto-generated UUID)')

    args = parser.parse_args()

    try:
        # Load conversation data
        print(f"Loading conversation from {args.conversation_file}...")
        conversation_data = load_conversation_snapshot(args.conversation_file)

        # Connect to CouchBase
        print(f"Connecting to CouchBase at {args.connection_string}...")
        cluster = connect_to_couchbase(args.connection_string, args.username, args.password)

        # Add conversation to CouchBase
        print(f"Adding conversation to bucket: {args.bucket}, scope: {args.scope}, collection: {args.collection}")
        document_id, session_id = add_conversation_to_couchbase(
            cluster, args.bucket, args.scope, args.collection,
            conversation_data, args.session_id
        )

        print(f"Successfully added conversation:")
        print(f"  Document ID: {document_id}")
        print(f"  Session ID: {session_id}")
        print(f"  Messages count: {len(conversation_data) if isinstance(conversation_data, list) else 'N/A'}")

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
