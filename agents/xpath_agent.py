import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from agents.base_agent import BaseAgent
from playwright.async_api import Page
from utils import strip_json_code_blocks


class XPathAgent(BaseAgent):
    """XPath agent that finds and validates XPath for elements at given coordinates"""

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
            agent_name="xpath",
            config_dict=config_dict
        )
        self.config_dict = config_dict
        self.page: Optional[Page] = None

    def get_system_prompt(self) -> str:
        """Get the system prompt for the XPath agent"""
        return """# Identity

You are an XPath Agent that finds XPath expressions for elements at given coordinates.

# Available Tools

- get_xpath(): Get XPath of element at the current coordinates and highlight it
- try_parent_element(): Try to get XPath of the parent element (call this if verification indicates the current element is not suitable)
- exit(message, exitCode): Exit the agent when finished with the final XPath

# Rules

- Respond with a JSON object containing your thought process and the action to execute
- First, get the XPath at the given coordinates
- After each action, you will receive verification feedback about whether the element is correct
- If the element is not suitable (e.g., too generic, not interactive), try parent elements
- Ensure the XPath is legible and unique based on verification feedback
- When a good XPath is found (verified as valid), call exit with the XPath

# Response Format

```json
{
  "thought": "Your reasoning about what to do next",
  "action": {
    "tool": "tool_name",
    "args": {
      "arg1": "value1"
    }
  }
}
```

When the task is complete, respond with:
```json
{
  "thought": "Found valid XPath",
  "action": {
    "tool": "exit",
    "args": {
      "message": "xpath_expression_here",
      "exitCode": 0
    }
  }
}
```
"""

    def set_page(self, page: Page):
        """Set the browser page to work with"""
        self.page = page

    async def _get_xpath_at_coords(self, x: int, y: int) -> Dict[str, Any]:
        """Get XPath of element at coordinates and highlight it"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            # Inject the XPath inspector script
            xpath_script = """
            (function() {
              // Remove any existing highlight boxes
              const existingBoxes = document.querySelectorAll('.xpath-highlight-box');
              existingBoxes.forEach(box => box.remove());

              const highlightBox = document.createElement('div');
              highlightBox.className = 'xpath-highlight-box';
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
                if (el.id) return `//*[@id="${el.id}"]`;
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

              // Store the current element globally so we can access it later
              window.__xpath_current_element__ = document.elementFromPoint(arguments[0], arguments[1]);
              const el = window.__xpath_current_element__;

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
                  text: el.textContent.substring(0, 100),
                  type: el.type || '',
                  role: el.getAttribute('role') || '',
                  ariaLabel: el.getAttribute('aria-label') || ''
                }
              };
            })();
            """

            result = await self.page.evaluate(xpath_script, x, y)

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

    async def _get_xpath(self) -> Dict[str, Any]:
        """Get XPath of current element (after initial coords or parent move)"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            xpath_script = """
            (function() {
              const el = window.__xpath_current_element__;
              if (!el) return null;

              function getXPath(el) {
                if (!el || el.nodeType !== 1) return '';
                if (el.id) return `//*[@id="${el.id}"]`;
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

              const xpath = getXPath(el);
              return {
                xpath: xpath,
                element: {
                  tagName: el.tagName,
                  id: el.id,
                  className: el.className,
                  text: el.textContent.substring(0, 100),
                  type: el.type || '',
                  role: el.getAttribute('role') || '',
                  ariaLabel: el.getAttribute('aria-label') || ''
                }
              };
            })();
            """

            result = await self.page.evaluate(xpath_script)

            if result is None:
                return {
                    "success": False,
                    "error": "No current element found"
                }

            return {
                "success": True,
                "message": "XPath extracted from current element",
                "xpath": result.get("xpath"),
                "element": result.get("element")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _try_parent_element(self) -> Dict[str, Any]:
        """Try to get XPath of the parent element"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            xpath_script = """
            (function() {
              const el = window.__xpath_current_element__;
              if (!el || !el.parentNode || el.parentNode.nodeType !== 1) {
                return null;
              }

              // Move to parent
              window.__xpath_current_element__ = el.parentNode;
              const parent = window.__xpath_current_element__;

              // Update highlight
              const highlightBox = document.querySelector('.xpath-highlight-box');
              if (highlightBox) {
                const rect = parent.getBoundingClientRect();
                highlightBox.style.width = rect.width + 'px';
                highlightBox.style.height = rect.height + 'px';
                highlightBox.style.left = rect.left + window.scrollX + 'px';
                highlightBox.style.top = rect.top + window.scrollY + 'px';
              }

              function getXPath(el) {
                if (!el || el.nodeType !== 1) return '';
                if (el.id) return `//*[@id="${el.id}"]`;
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

              const xpath = getXPath(parent);
              return {
                xpath: xpath,
                element: {
                  tagName: parent.tagName,
                  id: parent.id,
                  className: parent.className,
                  text: parent.textContent.substring(0, 100),
                  type: parent.type || '',
                  role: parent.getAttribute('role') || '',
                  ariaLabel: parent.getAttribute('aria-label') || ''
                }
              };
            })();
            """

            result = await self.page.evaluate(xpath_script)

            if result is None:
                return {
                    "success": False,
                    "error": "No parent element found or already at root"
                }

            return {
                "success": True,
                "message": "Moved to parent element and extracted XPath",
                "xpath": result.get("xpath"),
                "element": result.get("element")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def verify_xpath(self, xpath: str, element_info: Dict[str, Any]) -> str:
        """Verify that the XPath is unique and points to the correct element"""
        try:
            if not self.page:
                return "Error: No active browser page"

            verification_script = """
            (function(xpath) {
              try {
                const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                const count = result.snapshotLength;

                if (count === 0) {
                  return {
                    valid: false,
                    reason: "XPath does not match any elements"
                  };
                }

                if (count > 1) {
                  return {
                    valid: false,
                    reason: `XPath matches ${count} elements, not unique`
                  };
                }

                const element = result.snapshotItem(0);
                const currentElement = window.__xpath_current_element__;

                if (element !== currentElement) {
                  return {
                    valid: false,
                    reason: "XPath points to a different element than expected"
                  };
                }

                // Check if element is interactive
                const tagName = element.tagName.toLowerCase();
                const isInteractive = ['a', 'button', 'input', 'select', 'textarea'].includes(tagName) ||
                                     element.onclick !== null ||
                                     element.hasAttribute('onclick') ||
                                     element.getAttribute('role') === 'button';

                return {
                  valid: true,
                  isInteractive: isInteractive,
                  reason: `XPath is unique and correct. Element: ${element.tagName}${element.id ? '#' + element.id : ''}${element.className ? '.' + element.className.split(' ').join('.') : ''}`
                };
              } catch (e) {
                return {
                  valid: false,
                  reason: `Error evaluating XPath: ${e.message}`
                };
              }
            })();
            """

            result = await self.page.evaluate(verification_script, xpath)

            if result.get("valid"):
                return f"✓ Valid: {result.get('reason')}. Interactive: {result.get('isInteractive', False)}"
            else:
                return f"✗ Invalid: {result.get('reason')}"

        except Exception as e:
            return f"Error during verification: {str(e)}"

    def _exit(self, message: str, exitCode: int = 0) -> Dict[str, Any]:
        """Exit the agent"""
        return {
            "success": True,
            "exit": True,
            "message": message,
            "exitCode": exitCode
        }

    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action"""
        tool = action.get("tool")
        args = action.get("args", {})

        try:
            if tool == "get_xpath":
                return await self._get_xpath()
            elif tool == "try_parent_element":
                return await self._try_parent_element()
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
        """Process a message and find XPath"""
        try:
            # Try to get the running event loop
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we need to schedule the coroutine
            # We'll use asyncio.ensure_future and block until it completes
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._process_message_async(message))
                )
                return future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            return asyncio.run(self._process_message_async(message))

    async def _process_message_async(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of process_message"""
        try:
            x = message.get("x")
            y = message.get("y")

            if x is None or y is None:
                return {
                    "success": False,
                    "error": "Missing x or y coordinates"
                }

            max_iterations = message.get("max_iterations", 10)
            iteration = 0
            history: List[Dict[str, Any]] = []

            # Initial context - get element at coordinates
            initial_result = await self._get_xpath_at_coords(x, y)
            if not initial_result.get("success"):
                return {
                    "success": False,
                    "error": initial_result.get("error", "Failed to get initial element"),
                    "iterations": 0,
                    "history": []
                }

            # Initial verification
            xpath = initial_result.get("xpath")
            element_info = initial_result.get("element")
            verification = await self.verify_xpath(xpath, element_info)

            # Send initial state update
            self.send_llm_update("xpath_found", {
                "xpath": xpath,
                "element": element_info,
                "verification": verification
            })

            history.append({
                "action": {"tool": "get_xpath_at_coords", "args": {"x": x, "y": y}},
                "result": initial_result,
                "verification": verification
            })

            # Task description
            task = f"Find and validate XPath for element at coordinates ({x}, {y}). Initial element found: {element_info.get('tagName')} with xpath: {xpath}"

            while iteration < max_iterations:
                iteration += 1

                # Build context for LLM
                context_parts = [f"# Task\n\n{task}"]

                if history:
                    context_parts.append("\n# Action History")
                    for i, item in enumerate(history, 1):
                        context_parts.append(f"\n{i}. Action: {item['action']}")
                        context_parts.append(f"   Result: {item['result']}")
                        context_parts.append(f"   Verification: {item['verification']}")

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
                    return {
                        "success": False,
                        "error": "Invalid response format",
                        "iterations": iteration,
                        "history": history
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
                        "history": history
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

                # Check if exit action
                if exec_result.get("exit", False):
                    history.append({
                        "action": action,
                        "result": exec_result,
                        "thought": response_data.get("thought", ""),
                        "verification": None
                    })
                    return {
                        "success": True,
                        "xpath": exec_result.get("message", ""),
                        "iterations": iteration,
                        "history": history
                    }

                # Verify the result if we got an xpath
                verification = None
                if exec_result.get("success") and exec_result.get("xpath"):
                    xpath = exec_result.get("xpath")
                    element_info = exec_result.get("element")
                    verification = await self.verify_xpath(xpath, element_info)

                    # Send verification update
                    self.send_llm_update("xpath_verification", {
                        "verification": verification
                    })

                # Add to history
                history.append({
                    "action": action,
                    "result": exec_result,
                    "thought": response_data.get("thought", ""),
                    "verification": verification
                })

            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": iteration,
                "history": history
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "iterations": 0,
                "history": []
            }
