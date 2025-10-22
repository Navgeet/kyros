#!/usr/bin/env python3
"""
Test script to demonstrate the new terminal UI
"""

import asyncio
from terminal_ui import terminal_ui

async def simulate_agent_workflow():
    """Simulate a typical agent workflow with events"""

    # Show banner
    terminal_ui.print_banner()

    # Simulate task submission
    terminal_ui.handle_event({
        'type': 'task_submitted',
        'task': 'Open Firefox and search for "Anthropic Claude"'
    })

    await asyncio.sleep(1)

    # Simulate boss thinking
    terminal_ui.handle_event({
        'type': 'llm_call_start',
        'data': {
            'agent_name': 'boss',
            'model': 'claude-sonnet-4'
        }
    })

    # Simulate streaming response
    boss_message = "I'll help you open Firefox and search for 'Anthropic Claude'. Let me delegate this to the GUI agent."
    for char in boss_message:
        terminal_ui.handle_event({
            'type': 'llm_content_chunk',
            'data': {
                'content': char,
                'agent_name': 'boss'
            }
        })
        await asyncio.sleep(0.02)

    terminal_ui.handle_event({
        'type': 'llm_call_end',
        'data': {}
    })

    await asyncio.sleep(0.5)

    # Simulate delegation to GUI agent
    terminal_ui.handle_event({
        'type': 'delegation',
        'data': {
            'agent_type': 'gui',
            'message': 'Open Firefox browser'
        }
    })

    await asyncio.sleep(1)

    # Simulate GUI agent action with code block
    gui_response = """# Opening Firefox browser
```python
tools.focus_window()
tools.hotkey('command', 'space')
tools.type('Firefox')
tools.hotkey('enter')
tools.wait(2)
```"""

    terminal_ui.handle_event({
        'type': 'llm_call_start',
        'data': {
            'agent_name': 'gui',
            'model': 'qwen-vl-max'
        }
    })

    for char in gui_response:
        terminal_ui.handle_event({
            'type': 'llm_content_chunk',
            'data': {
                'content': char,
                'agent_name': 'gui'
            }
        })
        await asyncio.sleep(0.01)

    terminal_ui.handle_event({
        'type': 'llm_call_end',
        'data': {}
    })

    await asyncio.sleep(1)

    # Simulate action execution
    terminal_ui.handle_event({
        'type': 'action_execute',
        'data': {
            'action': 'Opening Firefox'
        }
    })

    await asyncio.sleep(0.5)

    terminal_ui.handle_event({
        'type': 'action_result',
        'data': {
            'result': {
                'success': True
            }
        }
    })

    await asyncio.sleep(1)

    # Simulate task completion
    terminal_ui.handle_event({
        'type': 'task_completed',
        'result': 'Successfully opened Firefox and performed search!'
    })

if __name__ == '__main__':
    asyncio.run(simulate_agent_workflow())
