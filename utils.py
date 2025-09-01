import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
import os

history_file = os.path.expanduser("~/.kyros_history")
session = PromptSession(history=FileHistory(history_file))

async def input():
    """Get input from the user with history support, ensuring it is not empty."""
    style = Style.from_dict({
        "prompt": "ansigreen bold",
    })
    msg = ""
    while msg.strip() == "":  # don't send empty input
        msg = await session.prompt_async([("class:prompt", "> ")], style=style, multiline=False, complete_while_typing=False, enable_system_prompt=False)
    return msg
