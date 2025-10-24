import asyncio
import json
import base64
import re
from typing import Dict, Any, Optional, Callable, List
from agents.base_agent import BaseAgent
from playwright.async_api import Page
from utils import strip_json_code_blocks


class XPathAgent(BaseAgent):
    """XPath agent that generates XPath expressions from HTML source and query using LLM"""

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        base_url: str = None,
        websocket_callback: Optional[Callable] = None,
        config_dict: Dict[str, Any] = None,
        browser_action_agent = None
    ):
        # Initialize with XPath config for generation (uses Claude)
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
        self.browser_action_agent = browser_action_agent

        # Create a separate client for verification (uses Qwen via Novita)
        self._init_verification_client()

    def _init_verification_client(self):
        """Initialize verification client using GUI agent config (Qwen via Novita)"""
        import config
        from openai import OpenAI

        # Get GUI agent config for verification (uses Qwen)
        gui_config = config.get_agent_config("gui", self.config_dict)

        self.verification_api_key = gui_config.get("api_key")
        self.verification_base_url = gui_config.get("base_url")
        self.verification_model = gui_config.get("model")
        self.verification_temperature = gui_config.get("temperature", 0.6)
        self.verification_max_tokens = gui_config.get("max_tokens", 30000)

        # Create OpenAI client for Qwen/Novita
        self.verification_client = OpenAI(
            api_key=self.verification_api_key,
            base_url=self.verification_base_url
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the XPath agent"""
        return """# Identity

You are an XPath Generation Agent that creates XPath expressions from HTML source code.

# Your Task

You will be given:
- HTML source code of a page (cleaned, without <head>, <script> tags)
- A query describing which element to find (e.g., "find xpath for submit button")

You need to generate an XPath expression that uniquely identifies the target element.

# XPath Generation Guidelines

1. Prefer readable, maintainable XPath expressions
2. Use semantic attributes when available (id, name, type, role, aria-label)
3. Avoid overly specific positional selectors unless necessary
4. Ensure the XPath is unique
5. Consider multiple candidates and choose the most reliable one

# Response Format

Respond with JSON containing your thought process and the XPath:

```json
{
  "thought": "Explanation of your reasoning and element analysis",
  "xpath": "//button[@type='submit']",
  "alternatives": ["//input[@value='Submit']", "//button[contains(text(), 'Submit')]"],
  "confidence": "high"
}
```

Confidence levels:
- "high": Element has clear semantic attributes or unique identifiers
- "medium": Element can be identified but may need visual confirmation
- "low": Element is ambiguous or may have multiple matches

# Examples

Query: "find xpath for email input field"
```json
{
  "thought": "Looking for an input element for email. Found input with type='email' and id='email-input', which is semantically correct and has a unique ID.",
  "xpath": "//input[@id='email-input']",
  "alternatives": ["//input[@type='email']", "//input[@name='email']"],
  "confidence": "high"
}
```

Query: "find xpath for login button"
```json
{
  "thought": "Found a button with text 'Log In' and class 'login-btn'. The button text is distinctive and the class suggests it's the primary login button.",
  "xpath": "//button[contains(@class, 'login-btn')]",
  "alternatives": ["//button[contains(text(), 'Log In')]", "//button[@type='submit']"],
  "confidence": "medium"
}
```
"""

    def clean_html(self, html: str) -> str:
        """Clean HTML by removing head, script, and style tags"""
        # Remove head tag and its contents
        html = re.sub(r'<head\b[^>]*>.*?</head>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove script tags and their contents
        html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove style tags and their contents
        html = re.sub(r'<style\b[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL).strip()

        return html

    def set_page(self, page: Page):
        """Set the browser page to work with"""
        self.page = page

    async def get_page_html(self) -> str:
        """Get the HTML source of the current page"""
        # Get page from browser_action_agent if not set
        if not self.page and self.browser_action_agent:
            self.page = self.browser_action_agent.get_page()

        if not self.page:
            error_msg = "No browser page available. Make sure a browser is launched first (use BrowserActionAgent to launch a browser)."
            raise ValueError(error_msg)

        html = await self.page.content()
        return self.clean_html(html)

    async def highlight_and_screenshot(self, xpath: str) -> Dict[str, Any]:
        """Highlight element by XPath and take screenshot"""
        try:
            if not self.page:
                return {
                    "success": False,
                    "error": "No active browser page",
                    "screenshot": None
                }

            # Highlight the element
            highlight_script = """
            (xpath) => {
              try {
                // Remove any existing highlight boxes
                const existingBoxes = document.querySelectorAll('.xpath-highlight-box');
                existingBoxes.forEach(box => box.remove());

                // Evaluate XPath
                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = result.singleNodeValue;

                if (!element) {
                  return { found: false, count: 0 };
                }

                // Count how many elements match
                const countResult = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                const count = countResult.snapshotLength;

                // Store the element globally
                window.__xpath_current_element__ = element;

                // Create highlight box
                const highlightBox = document.createElement('div');
                highlightBox.className = 'xpath-highlight-box';
                Object.assign(highlightBox.style, {
                  position: 'absolute',
                  background: 'rgba(0,123,255,0.15)',
                  border: '3px solid red',
                  borderRadius: '4px',
                  pointerEvents: 'none',
                  zIndex: '2147483647',
                  boxSizing: 'border-box'
                });
                document.body.appendChild(highlightBox);

                // Position highlight on element
                const rect = element.getBoundingClientRect();
                highlightBox.style.width = rect.width + 'px';
                highlightBox.style.height = rect.height + 'px';
                highlightBox.style.left = rect.left + window.scrollX + 'px';
                highlightBox.style.top = rect.top + window.scrollY + 'px';

                // Scroll element into view if needed
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });

                return {
                  found: true,
                  count: count,
                  tagName: element.tagName,
                  id: element.id || '',
                  className: element.className || '',
                  text: element.textContent ? element.textContent.substring(0, 100) : ''
                };
              } catch (e) {
                return { found: false, error: e.message };
              }
            }
            """

            highlight_result = await self.page.evaluate(highlight_script, xpath)

            if not highlight_result.get("found"):
                return {
                    "success": False,
                    "error": highlight_result.get("error", "Element not found"),
                    "screenshot": None,
                    "count": highlight_result.get("count", 0)
                }

            # Wait a bit for scrolling
            await asyncio.sleep(0.3)

            # Take screenshot
            screenshot_bytes = await self.page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            screenshot_data = f"data:image/png;base64,{screenshot_b64}"

            return {
                "success": True,
                "screenshot": screenshot_data,
                "element_info": {
                    "tagName": highlight_result.get("tagName"),
                    "id": highlight_result.get("id"),
                    "className": highlight_result.get("className"),
                    "text": highlight_result.get("text")
                },
                "count": highlight_result.get("count", 1)
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "screenshot": None
            }

    async def remove_highlight(self):
        """Remove highlight from the page"""
        try:
            if not self.page:
                return

            remove_script = """
            () => {
                const existingBoxes = document.querySelectorAll('.xpath-highlight-box');
                existingBoxes.forEach(box => box.remove());
            }
            """
            await self.page.evaluate(remove_script)
        except Exception as e:
            pass  # Silently ignore highlight removal failures

    async def verify_xpath_with_llm(self, xpath: str, query: str, screenshot: str, element_info: Dict[str, Any], count: int) -> Dict[str, Any]:
        """Verify the XPath using Qwen LLM with screenshot"""
        context = f"""# XPath Verification

Query: "{query}"
Generated XPath: {xpath}

Element found:
- Tag: {element_info.get('tagName', 'N/A')}
- ID: {element_info.get('id', 'N/A')}
- Class: {element_info.get('className', 'N/A')}
- Text: {element_info.get('text', 'N/A')}
- Match count: {count} element(s)

The screenshot shows the element highlighted with a red border. Is this the correct element for the query "{query}"?

Respond with JSON:
```json
{{
  "correct": true/false,
  "thought": "Your reasoning about whether this is the right element",
  "feedback": "If incorrect, suggest what to look for or how to improve the XPath"
}}
```
"""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": context
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": screenshot
                        }
                    }
                ]
            }
        ]

        # Send LLM call start event for verification
        self.send_llm_update("llm_call_start", {
            "agent_type": "XPathAgent"
        })

        # Use verification client (Qwen) instead of main client
        try:
            response = self.verification_client.chat.completions.create(
                model=self.verification_model,
                messages=messages,
                temperature=self.verification_temperature,
                max_tokens=self.verification_max_tokens,
                stream=False
            )
            response_text = response.choices[0].message.content

            # Send content chunk for status animation
            self.send_llm_update("llm_content_chunk", {
                "content": response_text[:100] + "..." if len(response_text) > 100 else response_text
            })

            # Send LLM call end event
            self.send_llm_update("llm_call_end", {})

            cleaned_response = strip_json_code_blocks(response_text)
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            self.send_llm_update("llm_call_end", {})
            return {
                "correct": False,
                "thought": "Failed to parse LLM response",
                "feedback": "Try again"
            }
        except Exception as e:
            self.send_llm_update("llm_call_end", {})
            return {
                "correct": False,
                "thought": f"Verification failed: {str(e)}",
                "feedback": "Try again"
            }

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of process_message"""
        try:
            query = message.get("content") or message.get("query")
            if not query:
                return {
                    "success": False,
                    "error": "Missing content parameter"
                }


            max_iterations = message.get("max_iterations", 3)
            iteration = 0
            history: List[Dict[str, Any]] = []

            # Step 1: Get HTML source
            html_source = await self.get_page_html()

            if not html_source:
                return {
                    "success": False,
                    "error": "Failed to get page HTML"
                }

            # Iteration loop: generate xpath, verify, repeat if needed
            while iteration < max_iterations:
                iteration += 1

                # Step 2: Generate XPath using Claude LLM

                context = f"""# Query
{query}

# HTML Source (cleaned)
```html
{html_source[:50000]}
```

Generate an XPath expression for the query.
"""

                # Add feedback from previous iteration if available
                if history:
                    last_entry = history[-1]
                    if not last_entry.get("verification", {}).get("correct"):
                        feedback = last_entry.get("verification", {}).get("feedback", "")
                        context += f"\n# Feedback from previous attempt\n{feedback}\n"

                messages = [
                    {
                        "role": "user",
                        "content": context
                    }
                ]

                # Use main client (Claude) for generation
                response = self.call_llm(
                    messages=messages,
                    system=self.get_system_prompt()
                )

                # Parse response
                try:
                    cleaned_response = strip_json_code_blocks(response)
                    xpath_data = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Failed to parse LLM response",
                        "iterations": iteration,
                        "history": history
                    }

                xpath = xpath_data.get("xpath")
                thought = xpath_data.get("thought", "")
                confidence = xpath_data.get("confidence", "unknown")

                # Step 3: Highlight and screenshot
                highlight_result = await self.highlight_and_screenshot(xpath)

                if not highlight_result.get("success"):
                    error = highlight_result.get("error", "Unknown error")

                    history.append({
                        "iteration": iteration,
                        "xpath": xpath,
                        "thought": thought,
                        "confidence": confidence,
                        "highlight_success": False,
                        "error": error
                    })

                    # Continue to next iteration
                    continue

                element_info = highlight_result.get("element_info", {})
                count = highlight_result.get("count", 0)
                screenshot = highlight_result.get("screenshot")

                # Step 4: Verify with LLM
                # Send verification start event
                self.send_llm_update("verification_start", {
                    "xpath": xpath,
                    "iteration": iteration
                })

                verification = await self.verify_xpath_with_llm(
                    xpath=xpath,
                    query=query,
                    screenshot=screenshot,
                    element_info=element_info,
                    count=count
                )

                # Remove highlight after verification
                await self.remove_highlight()

                is_correct = verification.get("correct", False)
                verification_thought = verification.get("thought", "")
                feedback = verification.get("feedback", "")

                # Send verification end event
                self.send_llm_update("verification_end", {
                    "xpath": xpath,
                    "correct": is_correct,
                    "success": is_correct,
                    "iteration": iteration
                })

                history.append({
                    "iteration": iteration,
                    "xpath": xpath,
                    "thought": thought,
                    "confidence": confidence,
                    "highlight_success": True,
                    "element_info": element_info,
                    "count": count,
                    "screenshot": screenshot,
                    "verification": verification
                })

                # If correct, return success
                if is_correct:
                    return {
                        "success": True,
                        "xpath": xpath,
                        "iterations": iteration
                    }

                # If not correct, continue to next iteration with feedback

            # Max iterations reached

            # Return the last generated xpath even if not verified
            if history:
                last_entry = history[-1]
                return {
                    "success": False,
                    "error": "Max iterations reached without verification",
                    "xpath": last_entry.get("xpath"),
                    "iterations": iteration
                }

            return {
                "success": False,
                "error": "No XPath generated",
                "iterations": iteration
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "iterations": 0
            }
