import os
from typing import List, Dict, Any, Optional, Callable
from openai import OpenAI
from anthropic import Anthropic
from abc import ABC, abstractmethod
import uuid
import config
import json
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all agents"""

    # Class variable for LLM log file path
    _llm_log_file = "logs/llm_calls.log"

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        websocket_callback: Optional[Callable] = None,
        agent_name: str = None,
        config_dict: Dict[str, Any] = None
    ):
        """Initialize the agent

        Args:
            agent_id: Unique identifier for the agent instance
            api_key: API key (overrides config if provided)
            base_url: API base URL (overrides config if provided)
            model: Model name (overrides config if provided)
            websocket_callback: Callback for WebSocket updates
            agent_name: Name of agent in config (e.g., 'boss', 'gui', 'shell', 'research')
            config_dict: Pre-loaded config dictionary (if not provided, will load from config.yaml)
        """
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_name = agent_name or self.__class__.__name__

        # Load config if agent_name is provided
        if agent_name:
            agent_config = config.get_agent_config(agent_name, config_dict)
            self.api_key = api_key or agent_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
            self.base_url = base_url or agent_config.get("base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = model or agent_config.get("model")
            self.temperature = agent_config.get("temperature", 0.5)
            self.max_tokens = agent_config.get("max_tokens", 1000)
            self.api_provider = agent_config.get("api_provider", "openai")
        else:
            # Fallback to old behavior
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = model
            self.temperature = 0.5
            self.max_tokens = 1000
            self.api_provider = "openai"

        self.websocket_callback = websocket_callback

        # Initialize appropriate client based on API provider
        if self.api_provider == "anthropic":
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        pass

    @abstractmethod
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response"""
        pass

    def send_llm_update(self, event_type: str, data: Dict[str, Any]):
        """Send LLM call update via WebSocket"""
        if self.websocket_callback:
            self.websocket_callback({
                "type": event_type,
                "agent_id": self.agent_id,
                "agent_type": self.__class__.__name__,
                "data": data
            })

    def _elide_image_data(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove image data from messages for display purposes"""
        elided_messages = []
        for msg in messages:
            msg_copy = msg.copy()
            if isinstance(msg_copy.get("content"), list):
                # Handle multi-part content (text + images)
                elided_content = []
                for item in msg_copy["content"]:
                    if isinstance(item, dict):
                        if item.get("type") == "image_url":
                            # Replace image data with placeholder
                            elided_content.append({
                                "type": "image_url",
                                "image_url": {"url": "[IMAGE_DATA_ELIDED]"}
                            })
                        else:
                            elided_content.append(item)
                    else:
                        elided_content.append(item)
                msg_copy["content"] = elided_content
            elided_messages.append(msg_copy)
        return elided_messages

    def _log_llm_call(self, log_data: Dict[str, Any]):
        """Log LLM call to file"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                **log_data
            }

            with open(self._llm_log_file, 'a') as f:
                f.write(json.dumps(log_entry, indent=2))
                f.write("\n" + "="*80 + "\n")
        except Exception as e:
            # Silently fail to avoid disrupting agent operation
            print(f"Warning: Failed to log LLM call: {e}")

    def _convert_to_anthropic_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style messages to Anthropic format"""
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                # Skip system messages, they're handled separately
                continue

            role = msg.get("role")
            content = msg.get("content")

            if isinstance(content, list):
                # Handle multi-part content (text + images)
                anthropic_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            anthropic_content.append({
                                "type": "text",
                                "text": item.get("text", "")
                            })
                        elif item.get("type") == "image_url":
                            # Convert base64 image to Anthropic format
                            url = item.get("image_url", {}).get("url", "")
                            if url.startswith("data:image"):
                                # Extract media type and base64 data
                                parts = url.split(";base64,")
                                if len(parts) == 2:
                                    media_type = parts[0].split(":")[1]
                                    base64_data = parts[1]
                                    anthropic_content.append({
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": base64_data
                                        }
                                    })
                anthropic_messages.append({
                    "role": role,
                    "content": anthropic_content
                })
            else:
                # Simple text content
                anthropic_messages.append({
                    "role": role,
                    "content": content
                })

        return anthropic_messages

    def call_llm(
        self,
        messages: List[Dict[str, Any]],
        system: str = None,
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = True
    ) -> str:
        """Make an LLM call and stream the response"""
        # Use instance defaults if not provided
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        # Prepare messages
        llm_messages = messages.copy()
        if system and self.api_provider != "anthropic":
            llm_messages.insert(0, {"role": "system", "content": system})

        # Log input
        self._log_llm_call({
            "event": "input",
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": self._elide_image_data(llm_messages)
        })

        # Send start event with elided image data
        self.send_llm_update("llm_call_start", {
            "messages": self._elide_image_data(llm_messages),
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens
        })

        response_text = ""
        reasoning_text = ""

        if self.api_provider == "anthropic":
            # Use Anthropic SDK
            anthropic_messages = self._convert_to_anthropic_format(llm_messages)

            if stream:
                with self.client.messages.stream(
                    model=self.model,
                    messages=anthropic_messages,
                    system=system or "",
                    temperature=temperature,
                    max_tokens=max_tokens
                ) as response:
                    for text in response.text_stream:
                        response_text += text
                        self.send_llm_update("llm_content_chunk", {
                            "content": text
                        })
            else:
                response = self.client.messages.create(
                    model=self.model,
                    messages=anthropic_messages,
                    system=system or "",
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response_text = response.content[0].text
        else:
            # Use OpenAI SDK
            if stream:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=llm_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )

                for chunk in response:
                    # Skip empty chunks
                    if not chunk.choices:
                        continue

                    # Handle reasoning content
                    if hasattr(chunk.choices[0].delta, 'model_extra') and chunk.choices[0].delta.model_extra:
                        reasoning_content = chunk.choices[0].delta.model_extra.get('reasoning_content')
                        if reasoning_content:
                            reasoning_text += reasoning_content
                            self.send_llm_update("llm_reasoning_chunk", {
                                "content": reasoning_content
                            })

                    # Handle regular content
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        self.send_llm_update("llm_content_chunk", {
                            "content": content
                        })
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=llm_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                response_text = response.choices[0].message.content

        # Log output
        self._log_llm_call({
            "event": "output",
            "response": response_text,
            "reasoning": reasoning_text
        })

        # Send end event
        self.send_llm_update("llm_call_end", {
            "response": response_text,
            "reasoning": reasoning_text
        })

        return response_text
