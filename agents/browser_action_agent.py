import asyncio
import json
import base64
from typing import Dict, Any, Optional, Callable, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from agents.base_agent import BaseAgent
from utils import strip_json_code_blocks, save_screenshot, compact_context, count_words


class BrowserActionAgent(BaseAgent):
    """Browser action agent that manages browser and performs actions using LLM"""

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
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.history: List[Dict[str, Any]] = []
        self.config_dict = config_dict
        self.compacted_context: str = ""
        self.step_count: int = 0

    def get_system_prompt(self) -> str:
        """Get the system prompt for the browser action agent"""
        return """# Identity

You are a Browser Action Agent that automates browser interactions using Playwright.
Your job is to execute the given task by performing step-by-step actions.

# Available Tools

- launch(name): Launch a new browser (name can be "chromium" or "firefox", defaults to "chromium")
- navigate(url): Navigate current page to the given URL
- click(xpath): Click on an element by XPath
- input_text(xpath, text): Input text into an element by XPath (types character by character)
- fill(xpath, text): Fill an element with text (instant, better for long text)
- focus(xpath): Focus on an element by XPath
- press_key(xpath, key): Press a key on an element (e.g., "Enter", "Tab", "Escape")
- hover(xpath): Hover over an element by XPath
- get_text(xpath): Get text content of an element
- get_value(xpath): Get value of an input element
- wait_for_element(xpath, timeout): Wait for an element to appear (timeout in milliseconds, default 5000)
- scroll_into_view(xpath): Scroll an element into view
- screenshot(): Take a screenshot of the current page
- close(): Close the current browser
- wait(seconds): Wait for specified seconds
- exit(message, exitCode): Exit the agent when finished

# Rules

- Respond with a JSON object containing your thought process and the action to execute
- Break down complex tasks into simple, atomic actions
- Always verify your actions by observing results
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

    def get_page(self) -> Optional[Page]:
        """Get the current page"""
        return self.page

    async def _launch(self, name: str = "chromium") -> Dict[str, Any]:
        """Launch a new browser"""
        try:
            if self.playwright is None:
                self.playwright = await async_playwright().start()

            if name == "firefox":
                self.browser = await self.playwright.firefox.launch(headless=False)
            else:
                name = "chromium"
                # Add Chrome args to fix SIGTRAP in Docker
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-software-rasterizer',
                        '--disable-extensions'
                    ]
                )

            self.context = await self.browser.new_context(no_viewport=True)
            self.page = await self.context.new_page()

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
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page. Please launch a browser first."
                }

            response = await self.page.goto(url)
            status_code = response.status if response else None

            if status_code == 404:
                return {
                    "success": False,
                    "error": f"Page not found (404): {url}",
                    "status_code": status_code,
                    "url": self.page.url
                }
            elif status_code and status_code >= 400:
                return {
                    "success": False,
                    "error": f"HTTP error {status_code}: {url}",
                    "status_code": status_code,
                    "url": self.page.url
                }

            return {
                "success": True,
                "message": f"Navigated to {url}",
                "status_code": status_code,
                "url": self.page.url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _click(self, xpath: str, button: str = "left", click_count: int = 1) -> Dict[str, Any]:
        """Click on an element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            await element.click(button=button, click_count=click_count)

            return {
                "success": True,
                "message": f"Clicked element with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _input_text(self, xpath: str, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """Input text into an element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            if clear_first:
                await element.fill("")

            await element.type(text)

            return {
                "success": True,
                "message": f"Typed text into element with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _fill(self, xpath: str, text: str) -> Dict[str, Any]:
        """Fill an element with text"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            await element.fill(text)

            return {
                "success": True,
                "message": f"Filled element with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _focus(self, xpath: str) -> Dict[str, Any]:
        """Focus on an element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            await element.focus()

            return {
                "success": True,
                "message": f"Focused element with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _press_key(self, xpath: str, key: str) -> Dict[str, Any]:
        """Press a key on an element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            await element.press(key)

            return {
                "success": True,
                "message": f"Pressed key '{key}' on element with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _hover(self, xpath: str) -> Dict[str, Any]:
        """Hover over an element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            await element.hover()

            return {
                "success": True,
                "message": f"Hovered over element with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_text(self, xpath: str) -> Dict[str, Any]:
        """Get text content of an element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            text = await element.text_content()

            return {
                "success": True,
                "message": f"Got text from element with XPath: {xpath}",
                "text": text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_value(self, xpath: str) -> Dict[str, Any]:
        """Get value of an input element by XPath"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            value = await element.input_value()

            return {
                "success": True,
                "message": f"Got value from element with XPath: {xpath}",
                "value": value
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _wait_for_element(self, xpath: str, timeout: int = 5000) -> Dict[str, Any]:
        """Wait for an element to appear"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            await self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)

            return {
                "success": True,
                "message": f"Element appeared with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _scroll_into_view(self, xpath: str) -> Dict[str, Any]:
        """Scroll an element into view"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            element = await self.page.query_selector(f"xpath={xpath}")

            if not element:
                return {
                    "success": False,
                    "error": f"No element found with XPath: {xpath}"
                }

            await element.scroll_into_view_if_needed()

            return {
                "success": True,
                "message": f"Scrolled element into view with XPath: {xpath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _screenshot(self) -> Dict[str, Any]:
        """Take a screenshot of the current page"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            screenshot_bytes = await self.page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            screenshot_data = f"data:image/png;base64,{screenshot_b64}"

            filepath = save_screenshot(screenshot_data, prefix="browser")

            return {
                "success": True,
                "message": "Screenshot captured",
                "screenshot": screenshot_data,
                "filepath": filepath
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
                self.context = None
                self.page = None

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
            elif tool == "input_text":
                return await self._input_text(**args)
            elif tool == "fill":
                return await self._fill(**args)
            elif tool == "focus":
                return await self._focus(**args)
            elif tool == "press_key":
                return await self._press_key(**args)
            elif tool == "hover":
                return await self._hover(**args)
            elif tool == "get_text":
                return await self._get_text(**args)
            elif tool == "get_value":
                return await self._get_value(**args)
            elif tool == "wait_for_element":
                return await self._wait_for_element(**args)
            elif tool == "scroll_into_view":
                return await self._scroll_into_view(**args)
            elif tool == "screenshot":
                return await self._screenshot()
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

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and execute browser actions"""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._process_message_async(message))
                )
                return future.result()
        except RuntimeError:
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
                        self.compacted_context = compact_context(
                            self.history,
                            task,
                            self.config_dict,
                            self.websocket_callback,
                            self.agent_id,
                            self.agent_name
                        )
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
                        print(f"ERROR: BrowserActionAgent received invalid JSON response: {response}")
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
                        await self._close()
                        return {
                            "success": True,
                            "result": exec_result.get("message", "Task completed"),
                            "iterations": iteration,
                            "history": self.history
                        }

                except Exception as e:
                    print(f"ERROR: BrowserActionAgent iteration {iteration} failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "success": False,
                        "error": f"Error in iteration {iteration}: {str(e)}",
                        "iterations": iteration,
                        "history": self.history
                    }

            await self._close()

            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": iteration,
                "history": self.history
            }

        except Exception as e:
            print(f"ERROR: BrowserActionAgent failed to process message: {e}")
            import traceback
            traceback.print_exc()

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
