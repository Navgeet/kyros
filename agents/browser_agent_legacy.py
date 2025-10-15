import asyncio
import json
from typing import List, Dict, Any, Optional, Callable
from agents.base_agent import BaseAgent
from utils import strip_json_code_blocks, compact_context, count_words
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserAgent(BaseAgent):
    """Browser agent that uses Playwright to automate browser interactions"""

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        base_url: str = None,
        websocket_callback: Optional[Callable] = None,
        config_dict: Dict[str, Any] = None
    ):
        super().__init__(
            agent_id=agent_id,
            api_key=api_key,
            base_url=base_url,
            websocket_callback=websocket_callback,
            agent_name="browser",
            config_dict=config_dict
        )
        self.history: List[Dict[str, Any]] = []
        self.config_dict = config_dict
        self.compacted_context: str = ""
        self.step_count: int = 0

        # Browser state
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self.current_context_name: Optional[str] = None
        self.current_page_name: Optional[str] = None

    def get_system_prompt(self) -> str:
        """Get the system prompt for the browser agent"""
        return """# Identity

You are a Browser Agent that automates browser interactions using Playwright.
Your job is to execute the given task by performing step-by-step actions.

# Available Tools

- launch(name): Launch a new browser (name can be "chromium" or "firefox", defaults to "chromium")
- navigate(url): Navigate current page to the given URL
- click(selector): Click on an element matching the CSS selector
- type(selector, text): Type text into an element
- get_xpath(x, y): Get XPath of element at screen coordinates and highlight it
- close(): Close the current browser
- wait(seconds): Wait for specified seconds
- exit(message, exitCode): Exit the agent when finished

# Rules

- Respond with a JSON object containing your thought process and the action to execute
- Break down complex tasks into simple, atomic actions
- Always verify your actions by taking screenshots when needed
- When the task is complete, call exit with an appropriate message

# Response Format

```json
{
  "thought": "Your reasoning about what to do next",
  "action": {
    "tool": "tool_name",
    "args": {
      "arg1": "value1",
      "arg2": "value2"
    }
  }
}
```

When the task is complete, respond with:
```json
{
  "thought": "Task completed successfully",
  "action": {
    "tool": "exit",
    "args": {
      "message": "Completion message",
      "exitCode": 0
    }
  }
}
```
"""

    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a browser action"""
        tool = action.get("tool")
        args = action.get("args", {})

        try:
            if tool == "launch":
                return await self._launch(**args)
            elif tool == "navigate":
                return await self._navigate(**args)
            elif tool == "click":
                return await self._click(**args)
            elif tool == "type":
                return await self._type(**args)
            elif tool == "screenshot":
                return await self._screenshot(**args)
            elif tool == "get_xpath":
                return await self._get_xpath(**args)
            elif tool == "close":
                return await self._close()
            elif tool == "wait":
                return await self._wait(**args)
            elif tool == "exit":
                return self._exit(**args)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _launch(self, name: str = "chromium") -> Dict[str, Any]:
        """Launch a new browser (chromium or firefox)"""
        try:
            if self.playwright is None:
                self.playwright = await async_playwright().start()

            # Select browser based on name (chromium is default)
            if name == "firefox":
                self.browser = await self.playwright.firefox.launch(headless=False)
            else:
                # Default to chromium for any other value
                name = "chromium"
                self.browser = await self.playwright.chromium.launch(headless=False)

            # Create context without fixed viewport (will use actual window size)
            self.contexts[name] = await self.browser.new_context(no_viewport=True)
            self.pages[name] = await self.contexts[name].new_page()
            self.current_context_name = name
            self.current_page_name = name

            return {
                "success": True,
                "message": f"{name.capitalize()} browser launched successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        try:
            if not self.current_page_name or self.current_page_name not in self.pages:
                return {
                    "success": False,
                    "error": "No active browser page. Please launch a browser first."
                }

            page = self.pages[self.current_page_name]
            response = await page.goto(url)

            # Check if status code indicates an error (404 or other errors)
            status_code = response.status if response else None

            if status_code == 404:
                return {
                    "success": False,
                    "error": f"Page not found (404): {url}",
                    "status_code": status_code,
                    "url": page.url
                }
            elif status_code and status_code >= 400:
                return {
                    "success": False,
                    "error": f"HTTP error {status_code}: {url}",
                    "status_code": status_code,
                    "url": page.url
                }

            return {
                "success": True,
                "message": f"Navigated to {url}",
                "status_code": status_code,
                "url": page.url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _click(self, selector: str) -> Dict[str, Any]:
        """Click an element"""
        try:
            if not self.current_page_name or self.current_page_name not in self.pages:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            page = self.pages[self.current_page_name]
            await page.click(selector)

            return {
                "success": True,
                "message": f"Clicked element: {selector}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _type(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element"""
        try:
            if not self.current_page_name or self.current_page_name not in self.pages:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            page = self.pages[self.current_page_name]
            await page.fill(selector, text)

            return {
                "success": True,
                "message": f"Typed text into {selector}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _screenshot(self) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if not self.current_page_name or self.current_page_name not in self.pages:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            page = self.pages[self.current_page_name]
            screenshot_bytes = await page.screenshot()

            # Convert to base64 for transmission
            import base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            return {
                "success": True,
                "message": "Screenshot captured",
                "screenshot": f"data:image/png;base64,{screenshot_b64}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_xpath(self, x: int, y: int) -> Dict[str, Any]:
        """Get XPath of element at coordinates and highlight it"""
        try:
            if not self.current_page_name or self.current_page_name not in self.pages:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            page = self.pages[self.current_page_name]

            # Inject the XPath inspector script
            xpath_script = """
            (function() {
              const highlightBox = document.createElement('div');
              Object.assign(highlightBox.style, {
                position: 'absolute',
                background: 'rgba(0,123,255,0.15)',
                border: '2px solid rgba(0,123,255,0.9)',
                borderRadius: '4px',
                pointerEvents: 'none',
                zIndex: '2147483647',
                boxSizing: 'border-box'
              });
              document.body.appendChild(highlightBox);

              function getXPath(el) {
                if (!el || el.nodeType !== 1) return '';
                if (el.id) return `id("${el.id}")`;
                const parts = [];
                for (; el && el.nodeType === 1; el = el.parentNode) {
                  const name = el.localName.toLowerCase();
                  let index = 1;
                  for (let sib = el.previousSibling; sib; sib = sib.previousSibling) {
                    if (sib.nodeType === 1 && sib.localName.toLowerCase() === name) index++;
                  }
                  parts.unshift(`${name}[${index}]`);
                }
                return '/' + parts.join('/');
              }

              const el = document.elementFromPoint(arguments[0], arguments[1]);
              if (!el) return null;

              const rect = el.getBoundingClientRect();
              highlightBox.style.width = rect.width + 'px';
              highlightBox.style.height = rect.height + 'px';
              highlightBox.style.left = rect.left + window.scrollX + 'px';
              highlightBox.style.top = rect.top + window.scrollY + 'px';

              const xpath = getXPath(el);
              return {
                xpath: xpath,
                element: {
                  tagName: el.tagName,
                  id: el.id,
                  className: el.className,
                  text: el.textContent.substring(0, 100)
                }
              };
            })();
            """

            result = await page.evaluate(xpath_script, x, y)

            if result is None:
                return {
                    "success": False,
                    "error": f"No element found at coordinates ({x}, {y})"
                }

            return {
                "success": True,
                "message": "Element highlighted and XPath extracted",
                "xpath": result.get("xpath"),
                "element": result.get("element")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _close(self) -> Dict[str, Any]:
        """Close the browser"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.contexts.clear()
                self.pages.clear()
                self.current_context_name = None
                self.current_page_name = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            return {
                "success": True,
                "message": "Browser closed successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _wait(self, seconds: float) -> Dict[str, Any]:
        """Wait for specified seconds"""
        try:
            await asyncio.sleep(seconds)
            return {
                "success": True,
                "message": f"Waited for {seconds} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _exit(self, message: str, exitCode: int = 0) -> Dict[str, Any]:
        """Exit the agent"""
        return {
            "success": True,
            "exit": True,
            "message": message,
            "exitCode": exitCode
        }

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and execute browser actions"""
        # Run async processing in event loop
        return asyncio.run(self._process_message_async(message))

    async def _process_message_async(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of process_message"""
        try:
            task = message.get("content", "")
            max_iterations = message.get("max_iterations", 20)
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                self.step_count += 1

                try:
                    # Get compaction config
                    compaction_config = self.config_dict.get('compaction', {}) if self.config_dict else {}
                    trigger_steps = compaction_config.get('trigger', {}).get('steps', 5)
                    trigger_words = compaction_config.get('trigger', {}).get('words', 1000)

                    # Check if compaction is needed
                    context_text = str(self.history)
                    word_count = count_words(context_text)

                    if self.step_count >= trigger_steps or word_count >= trigger_words:
                        # Compact the context
                        self.compacted_context = compact_context(
                            self.history,
                            task,
                            self.config_dict,
                            self.websocket_callback,
                            self.agent_id,
                            self.agent_name
                        )
                        # Clear history after compaction
                        self.history = []
                        self.step_count = 0

                    # Build context for LLM
                    context_parts = [f"# Task\n\n{task}"]

                    if self.compacted_context:
                        context_parts.append(f"\n# Previous Actions (compacted)\n{self.compacted_context}")

                    if self.history:
                        context_parts.append("\n# Action History")
                        for i, item in enumerate(self.history[-10:], 1):
                            context_parts.append(f"\n{i}. Action: {item['action']}")
                            context_parts.append(f"   Result: {item['result']}")

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
                        print(f"ERROR: BrowserAgent received invalid JSON response: {response}")
                        return {
                            "success": False,
                            "error": "Invalid response format",
                            "iterations": iteration,
                            "history": self.history
                        }

                    # Send thought update
                    self.send_llm_update("thought", {
                        "thought": response_data.get("thought", ""),
                        "iteration": iteration
                    })

                    # Execute action
                    action = response_data.get("action")
                    if not action:
                        return {
                            "success": False,
                            "error": "No action provided",
                            "iterations": iteration,
                            "history": self.history
                        }

                    # Send action execute update
                    self.send_llm_update("action_execute", {
                        "action": action,
                        "iteration": iteration
                    })

                    # Execute action
                    exec_result = await self.execute_action(action)

                    # Send execution result
                    self.send_llm_update("action_result", {
                        "result": exec_result
                    })

                    # Add to history
                    self.history.append({
                        "action": action,
                        "result": exec_result,
                        "thought": response_data.get("thought", "")
                    })

                    # Check if exit action
                    if exec_result.get("exit", False):
                        # Clean up browser resources
                        await self._close()
                        return {
                            "success": True,
                            "result": exec_result.get("message", "Task completed"),
                            "iterations": iteration,
                            "history": self.history
                        }

                except Exception as e:
                    print(f"ERROR: BrowserAgent iteration {iteration} failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "success": False,
                        "error": f"Error in iteration {iteration}: {str(e)}",
                        "iterations": iteration,
                        "history": self.history
                    }

            # Clean up on max iterations
            await self._close()

            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": iteration,
                "history": self.history
            }

        except Exception as e:
            print(f"ERROR: BrowserAgent failed to process message: {e}")
            import traceback
            traceback.print_exc()

            # Ensure cleanup
            try:
                await self._close()
            except:
                pass

            return {
                "success": False,
                "error": str(e),
                "iterations": 0,
                "history": self.history
            }
