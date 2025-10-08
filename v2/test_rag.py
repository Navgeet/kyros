#!/usr/bin/env python3
"""
Test RAG functionality with a specific plan file.
Generates embeddings, searches for relevant learning objects, and shows refinement results.
"""

import argparse
import asyncio
import os
import sys
from datetime import timedelta
from typing import List, Dict, Optional

import requests
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions, SearchOptions
import couchbase.search as search
from couchbase.vector_search import VectorQuery, VectorSearch

# Add parent directory to path to import from refine_plan
sys.path.append('..')
from refine_plan import refine_plan_internlm


class RAGTester:
    """Test RAG functionality with plan files."""

    def __init__(self):
        # RAG configuration (same as agent_v2.py)
        self.embedding_url = "http://192.168.0.213:11434/api/embeddings"
        self.embedding_model = "dengcao/Qwen3-Embedding-8B:Q4_K_M"
        self.couchbase_connection = os.getenv("COUCHBASE_CONNECTION", "couchbase://192.168.0.213")
        self.couchbase_username = os.getenv("COUCHBASE_USERNAME", "admin")
        self.couchbase_password = os.getenv("COUCHBASE_PASSWORD", "admin123")
        self.couchbase_bucket = os.getenv("COUCHBASE_BUCKET", "foo")
        self.couchbase_scope = os.getenv("COUCHBASE_SCOPE", "bar")
        self.couchbase_collection = os.getenv("COUCHBASE_COLLECTION", "learnings")
        self.couchbase_search_index = os.getenv("COUCHBASE_SEARCH_INDEX", "learnings")

        # InternLM configuration
        self.api_url = os.getenv("INTERNLM_API_URL", "http://localhost:23333")
        self.api_key = os.getenv("INTERNLM_API_KEY")

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using Ollama API."""
        try:
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }

            print(f"🧠 Generating embedding for text ({len(text)} chars)...")

            loop = asyncio.get_event_loop()

            def make_request():
                response = requests.post(self.embedding_url, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                return result.get("embedding", [])

            embedding = await loop.run_in_executor(None, make_request)

            if embedding:
                print(f"✅ Generated embedding (dimension: {len(embedding)})")
                return embedding
            else:
                print("❌ Failed to generate embedding")
                return None

        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return None

    async def search_learning_objects(self, embedding: List[float]) -> List[Dict]:
        """Search for learning objects in Couchbase using vector similarity."""
        if not embedding:
            print("⚠️ No embedding provided for search")
            return []

        print(f"🔗 Connecting to Couchbase at {self.couchbase_connection}...")

        # Connect to Couchbase
        auth = PasswordAuthenticator(self.couchbase_username, self.couchbase_password)
        options = ClusterOptions(auth)
        options.apply_profile("wan_development")
        cluster = Cluster(self.couchbase_connection, options)

        # Wait for connection to be ready
        cluster.wait_until_ready(timeout=timedelta(seconds=10))
        print("✅ Connected to Couchbase cluster")

        # Get bucket and scope
        bucket = cluster.bucket(self.couchbase_bucket)
        scope = bucket.scope(self.couchbase_scope)

        loop = asyncio.get_event_loop()

        def execute_vector_search():
            print(f"🔍 Executing combined vector search on index '{self.couchbase_search_index}'...")

            # Create multiple vector queries for both embedding fields
            vector_queries = [
                VectorQuery.create('example_embed', embedding, num_candidates=5, boost=0.5),
                VectorQuery.create('learning_embed', embedding, num_candidates=5, boost=0.5)
            ]

            # Combine into single search request
            search_req = search.SearchRequest.create(VectorSearch(vector_queries))

            # Execute combined search
            result = scope.search(
                self.couchbase_search_index,
                search_req,
                SearchOptions(limit=10, fields=["learning", "example"])
            )

            learning_objects = []
            for row in result.rows():
                row_data = row.fields
                if row_data and "learning" in row_data and "example" in row_data:
                    if row_data["learning"] and row_data["example"]:  # Check for None values
                        # Avoid duplicates based on learning content
                        if not any(obj["learning"] == row_data["learning"] for obj in learning_objects):
                            learning_objects.append({
                                "learning": row_data["learning"],
                                "example": row_data["example"],
                                "score": row.score if hasattr(row, 'score') else 0.0
                            })

            print(f"📚 Found {len(learning_objects)} learning objects via combined vector search")
            print(f"Total search results: {result.metadata().metrics().total_rows()}")
            return learning_objects

        return await loop.run_in_executor(None, execute_vector_search)

    async def refine_plan_with_rag(self, initial_plan: str, learning_objects: List[Dict], user_request: str = "") -> str:
        """Refine the initial plan using RAG-retrieved learning objects."""
        try:
            # Prepare the learnings context
            learnings_text = "\n".join([
                f"Learning: {obj['learning']}\nExample: {obj['example']}\n"
                for obj in learning_objects
            ])

            # Create a refinement prompt that includes the learnings
            refinement_prompt = f"""Original user request: {user_request}

Initial plan:
{initial_plan}

Relevant learnings from previous experiences:
{learnings_text}

Please refine the initial plan by incorporating insights from the relevant learnings above. Only make improvements that are clearly beneficial based on the learnings. Keep the core structure and intent of the original plan."""

            print("🔄 Refining plan with learned knowledge...")

            # Use the existing refine_plan_internlm function
            loop = asyncio.get_event_loop()
            refined_plan = await loop.run_in_executor(
                None,
                refine_plan_internlm,
                refinement_prompt,
                self.api_url,
                self.api_key,
                True,  # include_screenshot
                False,  # stream
                None   # screenshot_file
            )

            return refined_plan

        except Exception as e:
            print(f"❌ Error refining plan with RAG: {e}")
            return initial_plan

    async def test_rag_with_plan(self, plan_file: str, user_request: str = ""):
        """Test the complete RAG workflow with a plan file."""

        print("🎯 RAG Testing Script")
        print("=" * 60)
        print(f"Plan file: {plan_file}")
        print(f"User request: {user_request if user_request else 'Not specified'}")
        print()

        # Read the plan file
        try:
            with open(plan_file, 'r', encoding='utf-8') as f:
                initial_plan = f.read().strip()
        except Exception as e:
            print(f"❌ Error reading plan file: {e}")
            return False

        if not initial_plan:
            print("❌ Plan file is empty")
            return False

        print(f"📋 Initial Plan ({len(initial_plan)} chars):")
        print("-" * 40)
        print(initial_plan)
        print("-" * 40)
        print()

        # Step 1: Generate embedding for the plan
        plan_embedding = await self.generate_embedding(initial_plan)
        if not plan_embedding:
            print("❌ Failed to generate plan embedding")
            return False

        # Step 2: Search for relevant learning objects
        learning_objects = await self.search_learning_objects(plan_embedding)

        if not learning_objects:
            print("📝 No relevant learning objects found")
            print("✅ RAG test completed (no refinement applied)")
            return True

        # Display found learning objects
        print("📚 Relevant Learning Objects:")
        print("-" * 40)
        for i, obj in enumerate(learning_objects[:5]):  # Show top 5
            score = obj.get('score', 0.0)
            print(f"{i+1}. Score: {score:.4f}")
            print(f"   Learning: {obj['learning'][:200]}{'...' if len(obj['learning']) > 200 else ''}")
            print(f"   Example: {obj['example'][:200]}{'...' if len(obj['example']) > 200 else ''}")
            print()

        # Step 3: Refine plan using learned knowledge
        refined_plan = await self.refine_plan_with_rag(initial_plan, learning_objects, user_request)

        print("📝 Refined Plan:")
        print("-" * 40)
        print(refined_plan)
        print("-" * 40)
        print()

        # Step 4: Show comparison
        print("🔄 RAG Impact Analysis:")
        print("-" * 40)
        print(f"Initial plan length: {len(initial_plan)} chars")
        print(f"Refined plan length: {len(refined_plan)} chars")
        print(f"Learning objects used: {len(learning_objects)}")
        print(f"Change ratio: {len(refined_plan)/len(initial_plan):.2f}x")

        # Simple change detection
        if refined_plan.strip() != initial_plan.strip():
            print("✅ Plan was refined based on RAG knowledge")
        else:
            print("⚠️ Plan remained unchanged")

        print()
        print("✅ RAG test completed successfully!")
        return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test RAG functionality with a plan file")
    parser.add_argument("plan_file", help="Path to the plan text file")
    parser.add_argument("--user-request", "-u", default="",
                       help="Original user request (optional, for context)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")

    args = parser.parse_args()

    # Check if plan file exists
    if not os.path.exists(args.plan_file):
        print(f"❌ Plan file not found: {args.plan_file}")
        return 1

    # Create and run RAG tester
    tester = RAGTester()

    try:
        success = asyncio.run(tester.test_rag_with_plan(args.plan_file, args.user_request))
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())