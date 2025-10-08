"""
Service layer for LangGraph Supervised Planning Agent
Contains business logic for planning, RAG, and utilities
"""

import json
import requests
import pyautogui
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from io import BytesIO

# Import existing planning modules
import sys
sys.path.append('..')
from generate_text_plan import generate_text_plan_internlm
from refine_plan import refine_plan_internlm
from plan_to_code import plan_to_code_internlm

from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions, SearchOptions
import couchbase.search as search
from couchbase.vector_search import VectorQuery, VectorSearch

from config import LangGraphAgentConfig
from state import AgentState


class PlanningService:
    """Service for text plan and code generation"""

    def __init__(self, config: LangGraphAgentConfig):
        self.config = config

    async def generate_text_plan(self, user_request: str, session: Optional[AgentState] = None) -> str:
        """Generate text plan using existing function with RAG integration."""
        try:
            # Generate initial plan
            initial_plan = generate_text_plan_internlm(
                user_request,
                self.config.api_url,
                self.config.api_key
            )

            # RAG refinement if session provided
            if session:
                rag_service = RAGService(self.config)
                embedding = await rag_service.generate_embedding(user_request)
                if embedding:
                    learning_objects = await rag_service.search_learning_objects(embedding)
                    if learning_objects:
                        refined_plan = await self._refine_plan_with_rag(
                            initial_plan,
                            learning_objects,
                            user_request
                        )
                        return refined_plan

            return initial_plan

        except Exception as e:
            print(f"Error generating text plan: {e}")
            return f"Error generating plan: {e}"

    async def improve_text_plan(self, original_plan: str, feedback: str, user_request: str) -> str:
        """Improve text plan based on feedback."""
        try:
            return refine_plan_internlm(
                original_plan,
                feedback,
                user_request,
                self.config.api_url,
                self.config.api_key
            )
        except Exception as e:
            print(f"Error improving text plan: {e}")
            return original_plan

    async def generate_code(self, text_plan: str, user_request: str) -> str:
        """Generate code from text plan."""
        try:
            return plan_to_code_internlm(
                text_plan,
                user_request,
                self.config.api_url,
                self.config.api_key
            )
        except Exception as e:
            print(f"Error generating code: {e}")
            return f"# Error generating code: {e}"

    async def improve_code(self, original_code: str, feedback: str, text_plan: str) -> str:
        """Improve code based on feedback."""
        try:
            # This would use a similar pattern to improve_text_plan
            # For now, returning original code as placeholder
            print(f"Code improvement requested: {feedback}")
            return original_code
        except Exception as e:
            print(f"Error improving code: {e}")
            return original_code

    async def _refine_plan_with_rag(self, initial_plan: str, learning_objects: List[Dict],
                                   user_request: str) -> str:
        """Refine plan with RAG results."""
        try:
            # Extract relevant information from learning objects
            context = "\n".join([
                f"Learning: {obj.get('content', '')}"
                for obj in learning_objects[:5]  # Limit to top 5
            ])

            # Use existing refine function with RAG context as feedback
            refined_plan = refine_plan_internlm(
                initial_plan,
                f"Consider these relevant learnings:\n{context}",
                user_request,
                self.config.api_url,
                self.config.api_key
            )

            return refined_plan

        except Exception as e:
            print(f"Error refining plan with RAG: {e}")
            return initial_plan


class RAGService:
    """Service for Retrieval Augmented Generation functionality"""

    def __init__(self, config: LangGraphAgentConfig):
        self.config = config
        self._cluster = None

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for RAG."""
        try:
            response = requests.post(
                self.config.embedding_url,
                json={
                    "model": self.config.embedding_model,
                    "prompt": text
                }
            )
            if response.status_code == 200:
                return response.json().get("embedding")
        except Exception as e:
            print(f"Error generating embedding: {e}")
        return None

    async def search_learning_objects(self, embedding: List[float]) -> List[Dict]:
        """Search for relevant learning objects using vector search."""
        try:
            # Initialize Couchbase connection if needed
            if not self._cluster:
                self._init_couchbase()

            if not self._cluster:
                return []

            # Perform vector search
            bucket = self._cluster.bucket(self.config.couchbase_bucket)
            scope = bucket.scope(self.config.couchbase_scope)
            collection = scope.collection(self.config.couchbase_collection)

            # Create vector query
            vector_query = VectorQuery(
                field_name="embedding",
                vector=embedding,
                num_candidates=10
            )

            vector_search = VectorSearch.from_vector_query(vector_query)
            search_options = SearchOptions(
                vector_search=vector_search,
                fields=["content", "metadata"]
            )

            # Execute search
            result = scope.search(
                self.config.couchbase_search_index,
                query=search.MatchAllQuery(),
                options=search_options
            )

            # Process results
            learning_objects = []
            for row in result.rows():
                learning_objects.append({
                    "content": row.fields.get("content", ""),
                    "metadata": row.fields.get("metadata", {}),
                    "score": row.score
                })

            return learning_objects

        except Exception as e:
            print(f"Error searching learning objects: {e}")
            return []

    def _init_couchbase(self):
        """Initialize Couchbase connection."""
        try:
            auth = PasswordAuthenticator(
                self.config.couchbase_username,
                self.config.couchbase_password
            )
            self._cluster = Cluster(self.config.couchbase_connection, ClusterOptions(auth))
        except Exception as e:
            print(f"Error initializing Couchbase: {e}")
            self._cluster = None


class UtilityService:
    """Service for utility functions like screenshots, file management"""

    def __init__(self, config: LangGraphAgentConfig):
        self.config = config
        self.screenshots_dir = Path("screenshots")
        self.conversations_dir = Path("conversations")
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.screenshots_dir.mkdir(exist_ok=True)
        self.conversations_dir.mkdir(exist_ok=True)

    async def capture_screenshot(self) -> Optional[str]:
        """Capture screenshot and save to file."""
        try:
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            screenshot.save(filepath)
            return filename
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    def save_conversation_history(self, session_id: str, conversation_history: List[Dict]):
        """Save conversation history to file."""
        try:
            filename = f"conversation_{session_id}.json"
            filepath = self.conversations_dir / filename

            with open(filepath, 'w') as f:
                json.dump({
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "conversation": conversation_history
                }, f, indent=2)

        except Exception as e:
            print(f"Error saving conversation: {e}")

    def load_conversation_history(self, session_id: str) -> Optional[List[Dict]]:
        """Load conversation history from file."""
        try:
            filename = f"conversation_{session_id}.json"
            filepath = self.conversations_dir / filename

            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    return data.get("conversation", [])

        except Exception as e:
            print(f"Error loading conversation: {e}")

        return None

    def get_html_interface(self) -> str:
        """Return HTML interface for the agent."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LangGraph Supervised Planning Agent V3</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { text-align: center; margin-bottom: 30px; }
                .info { background: #f5f5f5; padding: 20px; border-radius: 8px; }
                .endpoint { margin: 10px 0; }
                code { background: #e1e1e1; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 LangGraph Supervised Planning Agent V3</h1>
                <p>Human-in-the-loop planning with structured workflows</p>
            </div>

            <div class="info">
                <h2>🔌 Connection Information</h2>
                <div class="endpoint">
                    <strong>WebSocket:</strong> <code>ws://localhost:8001/ws</code>
                </div>
                <div class="endpoint">
                    <strong>Health Check:</strong> <code>/health</code>
                </div>
                <div class="endpoint">
                    <strong>Sessions:</strong> <code>/sessions</code>
                </div>
            </div>

            <div class="info">
                <h2>📋 Workflow Phases</h2>
                <ol>
                    <li><strong>Greeting:</strong> Initial user request</li>
                    <li><strong>Text Plan Generation:</strong> Create high-level plan</li>
                    <li><strong>Text Plan Approval:</strong> Human review and feedback</li>
                    <li><strong>Code Generation:</strong> Convert plan to executable code</li>
                    <li><strong>Code Approval:</strong> Final human review</li>
                    <li><strong>Completion:</strong> Task finished</li>
                </ol>
            </div>
        </body>
        </html>
        """


class WebSocketManager:
    """Manages WebSocket connections and messaging"""

    def __init__(self):
        from fastapi import WebSocket
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket):
        """Accept and register new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except RuntimeError:
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all active connections"""
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)