"""
Configuration management for LangGraph Supervised Planning Agent
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LangGraphAgentConfig:
    """Configuration for LangGraph Agent"""
    # Server configuration
    host: str = "localhost"
    port: int = 8001

    # API configuration
    api_url: str = "http://localhost:23333"
    api_key: Optional[str] = None

    # RAG configuration
    embedding_url: str = "http://192.168.0.213:11434/api/embeddings"
    embedding_model: str = "dengcao/Qwen3-Embedding-8B:Q4_K_M"

    # Couchbase configuration
    couchbase_connection: str = "couchbase://192.168.0.213"
    couchbase_username: str = "admin"
    couchbase_password: str = "admin123"
    couchbase_bucket: str = "foo"
    couchbase_scope: str = "bar"
    couchbase_collection: str = "learnings"
    couchbase_search_index: str = "learnings"

    # Session configuration
    session_timeout_hours: int = 24

    @classmethod
    def from_env(cls) -> "LangGraphAgentConfig":
        """Create configuration from environment variables"""
        return cls(
            host=os.getenv("AGENT_HOST", "localhost"),
            port=int(os.getenv("AGENT_PORT", "8000")),
            api_url=os.getenv("INTERNLM_API_URL", "https://chat.intern-ai.org.cn/api"),
            api_key=os.getenv("INTERNLM_API_KEY"),
            embedding_url=os.getenv("EMBEDDING_URL", "http://192.168.0.213:11434/api/embeddings"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "dengcao/Qwen3-Embedding-8B:Q4_K_M"),
            couchbase_connection=os.getenv("COUCHBASE_CONNECTION", "couchbase://192.168.0.213"),
            couchbase_username=os.getenv("COUCHBASE_USERNAME", "admin"),
            couchbase_password=os.getenv("COUCHBASE_PASSWORD", "admin123"),
            couchbase_bucket=os.getenv("COUCHBASE_BUCKET", "foo"),
            couchbase_scope=os.getenv("COUCHBASE_SCOPE", "bar"),
            couchbase_collection=os.getenv("COUCHBASE_COLLECTION", "learnings"),
            couchbase_search_index=os.getenv("COUCHBASE_SEARCH_INDEX", "learnings"),
            session_timeout_hours=int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
        )

    def validate(self) -> None:
        """Validate configuration"""
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")

        if self.session_timeout_hours < 1:
            raise ValueError(f"Invalid session timeout: {self.session_timeout_hours}")

        if not self.api_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid API URL: {self.api_url}")