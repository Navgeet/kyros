import os
import json
from typing import List, Dict, Any, Optional, Callable
from agents.base_agent import BaseAgent
import config as config_module
from utils import strip_json_code_blocks


class ResearchAgent(BaseAgent):
    """Research agent that uses Tavily to research information"""

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        base_url: str = None,
        websocket_callback: Optional[Callable] = None,
        tavily_api_key: str = None,
        config_dict: Dict[str, Any] = None
    ):
        super().__init__(
            agent_id=agent_id,
            api_key=api_key,
            base_url=base_url,
            websocket_callback=websocket_callback,
            agent_name="research",
            config_dict=config_dict
        )
        # Load Tavily API key from config or environment
        if tavily_api_key:
            self.tavily_api_key = tavily_api_key
        elif config_dict:
            self.tavily_api_key = config_module.get_tavily_api_key(config_dict)
        else:
            self.tavily_api_key = os.environ.get("TAVILY_API_KEY")

    def get_system_prompt(self) -> str:
        """Get the system prompt for the research agent"""
        return """# Identity

You are a Research Agent. Your job is to research information using web search and synthesize findings.

# Tools

- search(query): Search the web using Tavily and return relevant results

# Rules

- Respond with a JSON object containing your thought process and search query
- Analyze search results and determine if more searches are needed
- Synthesize information from multiple sources
- When you have enough information, set "done" to true

# Response Format

For searching:
```json
{
  "thought": "Your reasoning about what to search for",
  "action": "search",
  "query": "search query",
  "done": false
}
```

When research is complete:
```json
{
  "thought": "Research completed",
  "action": "complete",
  "done": true,
  "summary": "Comprehensive summary of findings with sources"
}
```
"""

    def search_tavily(self, query: str) -> Dict[str, Any]:
        """Search using Tavily API"""
        try:
            from tavily import TavilyClient

            if not self.tavily_api_key:
                return {
                    "success": False,
                    "error": "Tavily API key not configured"
                }

            client = TavilyClient(api_key=self.tavily_api_key)
            response = client.search(query, max_results=5)

            return {
                "success": True,
                "results": response.get("results", []),
                "query": query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and conduct research"""
        task = message.get("content", "")
        max_iterations = message.get("max_iterations", 10)
        iteration = 0
        search_history: List[Dict[str, Any]] = []

        while iteration < max_iterations:
            iteration += 1

            # Build context for LLM
            context_parts = [f"# Task\n\n{task}"]

            if search_history:
                context_parts.append("\n# Previous Searches")
                for i, item in enumerate(search_history, 1):
                    context_parts.append(f"\n## Search {i}: {item['query']}")
                    if item.get('results'):
                        context_parts.append("Results:")
                        for j, result in enumerate(item['results'][:3], 1):
                            context_parts.append(f"{j}. {result.get('title', 'N/A')}")
                            context_parts.append(f"   {result.get('content', 'N/A')[:200]}...")
                            context_parts.append(f"   Source: {result.get('url', 'N/A')}")

            messages = [
                {
                    "role": "user",
                    "content": "\n".join(context_parts)
                }
            ]

            # Generate next action
            response = self.call_llm(
                messages=messages,
                system=self.get_system_prompt()
            )

            # Parse response
            try:
                cleaned_response = strip_json_code_blocks(response)
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If not valid JSON, treat as error
                return {
                    "success": False,
                    "error": "Invalid response format",
                    "iterations": iteration,
                    "history": search_history
                }

            # Send thought update
            self.send_llm_update("thought", {
                "thought": response_data.get("thought", ""),
                "iteration": iteration
            })

            # Check if done
            if response_data.get("done", False):
                return {
                    "success": True,
                    "summary": response_data.get("summary", "Research completed"),
                    "iterations": iteration,
                    "history": search_history
                }

            # Execute search
            action = response_data.get("action")
            if action == "search":
                query = response_data.get("query")
                if not query:
                    return {
                        "success": False,
                        "error": "No query provided",
                        "iterations": iteration,
                        "history": search_history
                    }

                # Send search update
                self.send_llm_update("search_start", {
                    "query": query,
                    "iteration": iteration
                })

                # Execute search
                search_result = self.search_tavily(query)

                # Send search result
                self.send_llm_update("search_result", {
                    "result": search_result
                })

                # Add to history
                search_history.append({
                    "query": query,
                    "results": search_result.get("results", []),
                    "success": search_result.get("success", False),
                    "error": search_result.get("error"),
                    "thought": response_data.get("thought", "")
                })
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "iterations": iteration,
                    "history": search_history
                }

        return {
            "success": False,
            "error": "Max iterations reached",
            "iterations": iteration,
            "history": search_history
        }
