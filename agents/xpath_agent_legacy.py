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

You are an XPath Verification Agent that analyzes XPath expressions and element information to determine if the XPath is suitable.

# Your Task

You will be given:
- An XPath expression
- Element information (tag, class, id, text, role, etc.)
- Verification results (uniqueness, validity)

You need to decide if this XPath is suitable or if we should try the parent element.

# Decision Criteria

An XPath is suitable if:
- It is unique (verification passed)
- The element is interactive (button, link, input, etc.) OR semantically meaningful
- The element is not too generic (e.g., not just a div with no semantic meaning)

An XPath is NOT suitable if:
- It's a generic container (div, span) with no semantic meaning
- It's not the actual interactive element the user intended
- There's likely a better parent element that is interactive

# Response Format

If the XPath is suitable:
```json
{
  "thought": "Explanation of why this XPath is good",
  "suitable": true,
  "xpath": "the_xpath_here"
}
```

If we should try the parent element:
```json
{
  "thought": "Explanation of why we should try parent",
  "suitable": false,
  "try_parent": true
}
```

If we've gone too far up (e.g., reached body/html):
```json
{
  "thought": "Explanation of why we should stop",
  "suitable": true,
  "xpath": "the_best_xpath_we_found"
}
```
"""

    def set_page(self, page: Page):
        """Set the browser page to work with"""
        self.page = page

    async def _get_xpath_at_mouse_position(self) -> Dict[str, Any]:
        """Get XPath of element at current mouse position by simulating a click"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page"
                }

            # Step 1: Install a click listener to capture the element
            await self.page.evaluate("""
                () => {
                    // Remove any existing click listener
                    if (window.__xpath_click_handler__) {
                        document.removeEventListener('click', window.__xpath_click_handler__, true);
                    }

                    // Create new click handler
                    window.__xpath_click_handler__ = (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();

                        // Store the clicked element
                        window.__xpath_current_element__ = e.target;

                        // Remove the listener immediately after capturing
                        document.removeEventListener('click', window.__xpath_click_handler__, true);
                    };

                    // Add click listener with capture phase to intercept before any other handlers
                    document.addEventListener('click', window.__xpath_click_handler__, true);
                }
            """)

            # Step 2: Simulate a mouse click at current position
            # This will trigger the click event and capture the element
            import pyautogui
            pyautogui.click()

            # Step 3: Wait a bit for the click to register
            await asyncio.sleep(0.1)

            # Step 4: Extract the element info and highlight it
            xpath_script = """
            () => {
              const el = window.__xpath_current_element__;
              if (!el) return null;

              // Remove any existing highlight boxes
              const existingBoxes = document.querySelectorAll('.xpath-highlight-box');
              existingBoxes.forEach(box => box.remove());

              // Create highlight box
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

              // Position highlight on element
              const rect = el.getBoundingClientRect();
              highlightBox.style.width = rect.width + 'px';
              highlightBox.style.height = rect.height + 'px';
              highlightBox.style.left = rect.left + window.scrollX + 'px';
              highlightBox.style.top = rect.top + window.scrollY + 'px';

              // Generate XPath
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
            }
            """

            result = await self.page.evaluate(xpath_script)

            if result is None:
                return {
                    "success": False,
                    "error": "No element found at mouse position"
                }

            return {
                "success": True,
                "message": "Element highlighted and XPath extracted",
                "xpath": result.get("xpath"),
                "element": result.get("element")
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
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
            () => {
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
            }
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
            () => {
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
            }
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

    async def verify_xpath(self, xpath: str, element_info: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that the XPath is unique and points to the correct element using screenshot"""
        try:
            if not self.page:
                return {
                    "valid": False,
                    "reason": "No active browser page",
                    "screenshot": None
                }

            # First, do basic XPath validation
            verification_script = """
            (xpath) => {
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
            }
            """

            basic_result = await self.page.evaluate(verification_script, xpath)

            # Take a screenshot showing the highlighted element
            import base64
            screenshot_bytes = await self.page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            screenshot_data = f"data:image/png;base64,{screenshot_b64}"

            return {
                "valid": basic_result.get("valid", False),
                "reason": basic_result.get("reason", "Unknown"),
                "isInteractive": basic_result.get("isInteractive", False),
                "screenshot": screenshot_data
            }

        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error during verification: {str(e)}",
                "screenshot": None
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
            max_iterations = message.get("max_iterations", 10)
            iteration = 0
            history: List[Dict[str, Any]] = []

            # Step 1: Get element at mouse position by simulating click (no LLM needed)
            print(f"Getting element at mouse position (will simulate click)...")
            initial_result = await self._get_xpath_at_mouse_position()
            if not initial_result.get("success"):
                return {
                    "success": False,
                    "error": initial_result.get("error", "Failed to get initial element"),
                    "iterations": 0,
                    "history": []
                }

            xpath = initial_result.get("xpath")
            element_info = initial_result.get("element")

            # Verify the xpath with screenshot
            verification_result = await self.verify_xpath(xpath, element_info)
            verification_text = f"✓ Valid: {verification_result['reason']}. Interactive: {verification_result.get('isInteractive', False)}" if verification_result['valid'] else f"✗ Invalid: {verification_result['reason']}"
            print(f"Initial element: {element_info.get('tagName')} - {verification_text}")

            # Send initial state update
            self.send_llm_update("xpath_found", {
                "xpath": xpath,
                "element": element_info,
                "verification": verification_text,
                "screenshot": verification_result.get("screenshot")
            })

            history.append({
                "action": "get_initial_element",
                "xpath": xpath,
                "element": element_info,
                "verification": verification_text,
                "screenshot": verification_result.get("screenshot")
            })

            # Now iterate, asking LLM if this xpath is suitable or if we should try parent
            best_xpath = xpath  # Keep track of best xpath found

            while iteration < max_iterations:
                iteration += 1

                # Build context for LLM verification with screenshot
                context_text = f"""# Current Element Analysis

XPath: {xpath}
Element Info:
- Tag: {element_info.get('tagName')}
- ID: {element_info.get('id', 'none')}
- Class: {element_info.get('className', 'none')}
- Text: {element_info.get('text', 'none')}
- Type: {element_info.get('type', 'none')}
- Role: {element_info.get('role', 'none')}
- Aria Label: {element_info.get('ariaLabel', 'none')}

Verification: {verification_text}

The screenshot shows the element highlighted in blue. Is this XPath suitable, or should we try the parent element?
"""

                # Include screenshot in the message
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": context_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": verification_result.get("screenshot")
                                }
                            }
                        ]
                    }
                ]

                # Ask LLM to verify
                response = self.call_llm(
                    messages=messages,
                    system=self.get_system_prompt()
                )

                # Parse response
                try:
                    cleaned_response = strip_json_code_blocks(response)
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse LLM response: {e}")
                    print(f"Response was: {response}")
                    # If we can't parse, return the best xpath we have
                    return {
                        "success": True,
                        "xpath": best_xpath,
                        "iterations": iteration,
                        "history": history,
                        "note": "LLM response parse error, returning best xpath found"
                    }

                # Send thought update
                thought = response_data.get("thought", "")
                print(f"LLM decision: {thought}")

                self.send_llm_update("thought", {
                    "thought": thought,
                    "iteration": iteration
                })

                # Check if suitable
                if response_data.get("suitable", False):
                    final_xpath = response_data.get("xpath", xpath)
                    print(f"✓ XPath accepted: {final_xpath}")

                    history.append({
                        "action": "llm_verification",
                        "thought": thought,
                        "decision": "suitable",
                        "final_xpath": final_xpath
                    })

                    return {
                        "success": True,
                        "xpath": final_xpath,
                        "iterations": iteration,
                        "history": history
                    }

                # Try parent element
                if response_data.get("try_parent", False):
                    print("Trying parent element...")

                    parent_result = await self._try_parent_element()

                    if not parent_result.get("success"):
                        # Can't go further up, return current xpath
                        print(f"✓ Cannot go further up, returning: {best_xpath}")
                        history.append({
                            "action": "try_parent",
                            "thought": thought,
                            "result": "no_parent",
                            "final_xpath": best_xpath
                        })
                        return {
                            "success": True,
                            "xpath": best_xpath,
                            "iterations": iteration,
                            "history": history
                        }

                    # Update current element
                    xpath = parent_result.get("xpath")
                    element_info = parent_result.get("element")
                    verification_result = await self.verify_xpath(xpath, element_info)
                    verification_text = f"✓ Valid: {verification_result['reason']}. Interactive: {verification_result.get('isInteractive', False)}" if verification_result['valid'] else f"✗ Invalid: {verification_result['reason']}"

                    print(f"Parent element: {element_info.get('tagName')} - {verification_text}")

                    # Update best_xpath if this one is valid
                    if verification_result['valid']:
                        best_xpath = xpath

                    # Send update
                    self.send_llm_update("xpath_found", {
                        "xpath": xpath,
                        "element": element_info,
                        "verification": verification_text,
                        "screenshot": verification_result.get("screenshot")
                    })

                    history.append({
                        "action": "try_parent",
                        "thought": thought,
                        "xpath": xpath,
                        "element": element_info,
                        "verification": verification_text,
                        "screenshot": verification_result.get("screenshot")
                    })

                    continue

                # If we get here, something unexpected happened
                print(f"Unexpected LLM response, returning best xpath: {best_xpath}")
                return {
                    "success": True,
                    "xpath": best_xpath,
                    "iterations": iteration,
                    "history": history,
                    "note": "Unexpected LLM response format"
                }

            # Max iterations reached
            print(f"Max iterations reached, returning best xpath: {best_xpath}")
            return {
                "success": True,
                "xpath": best_xpath,
                "iterations": iteration,
                "history": history,
                "note": "Max iterations reached"
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
