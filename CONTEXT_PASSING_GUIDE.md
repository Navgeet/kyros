# Context Passing Pattern Guide

## Overview

Agents maintain context between delegations through a simple pattern:
1. When an agent completes work, its exit message becomes context
2. On re-delegation, the previous context is prepended to the new task
3. The LLM naturally understands the state and avoids redundant work

## How It Works

### In BrowserBossAgent

```python
# Track summaries from agent completions
self.agent_summaries: Dict[str, str] = {}

# Build message with context if available
context = self.agent_summaries.get(agent_type, "")
if context:
    full_message = f"Context from previous work:\n{context}\n\nNew task: {agent_message}"
else:
    full_message = agent_message

# Send to agent (unified "content" parameter for all agents)
if hasattr(agent, '_process_message_async'):
    subagent_response = await agent._process_message_async({
        "content": full_message
    })
else:
    subagent_response = agent.process_message({
        "content": full_message
    })

# Extract and store summary from response
if subagent_response.get("exit") or "summary" in subagent_response:
    summary = subagent_response.get("message", "")
    if summary:
        self.agent_summaries[agent_type] = summary
```

## Example Workflow

### First Call
```
Boss → BrowserActionAgent: "Open https://example.com and navigate to login page"

Agent exits with message:
"Browser opened successfully. Currently on https://example.com login page."

Stored as: agent_summaries["BrowserActionAgent"] = "Browser opened successfully..."
```

### Second Call
```
Boss → BrowserActionAgent: "Click the login button and enter credentials"

Agent receives:
"Context from previous work:
Browser opened successfully. Currently on https://example.com login page.

New task: Click the login button and enter credentials"

Agent knows:
- Browser is already open
- Already on login page
- Doesn't try to launch browser again
```

## Benefits

✅ **No Code Duplication**: State handling is via LLM, not special-case code
✅ **Works for Any Agent**: Pattern applies to all agent types
✅ **Natural to LLM**: Agents understand state from context naturally
✅ **Simple**: Just passing text, easy to understand and maintain
✅ **Flexible**: Context can contain any relevant information

## Implementing in Your Agent

Just ensure your agent's exit message includes relevant state:

```python
# Good exit messages with state information
tools.exit("Browser opened and logged in to admin panel", 0)
tools.exit("XPath found: //button[@id='submit']. Element is visible.", 0)
tools.exit("Navigated to checkout page. Form fields ready for input.", 0)

# Poor exit messages (missing state)
tools.exit("Done", 0)
tools.exit("Success", 0)
```

## Testing the Pattern

To verify context is being passed:

1. Run a task that involves multiple delegations
2. Check BrowserBossAgent's `agent_summaries` dict
3. Verify summaries are accumulating
4. Check logs to see if agents reference the context

Example in debug:
```python
# In BrowserBossAgent after delegation
print(f"Stored summaries: {self.agent_summaries}")
# Output: {'BrowserActionAgent': 'Browser opened and navigated...', 'XPathAgent': '...'}
```
