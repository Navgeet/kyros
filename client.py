#!/usr/bin/env python
import asyncio
import io
import base64
import json
import pyautogui
from websockets.asyncio.client import connect
from termcolor import colored, cprint


def capture_screen_b64():
    """Capture a screenshot and return as base64 encoded PNG string."""
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
    return img_b64


async def chat_loop():
    async with connect("ws://localhost:8765/chat") as websocket:
        while True:
            try:
                prompt = colored("> ", "green", attrs=["bold"])
                print(prompt, end="")
                msg = input()
            except KeyboardInterrupt:
                break

            # msg {"prompt": "text", "context": {"screen": "<base64_encoded_image>"}}
            mouse_x, mouse_y = pyautogui.position()
            message = {
                "prompt": msg,
                "context": {
                    # "screen": capture_screen_b64(),
                    "mouse": {
                        "x": mouse_x,
                        "y": mouse_y
                    }
                }
            }
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            print("")
            # Extract text between <think> and </think> and print in grey
            start_tag = "<think>"
            end_tag = "</think>"
            start = response.find(start_tag)
            end = response.find(end_tag, start + len(start_tag))
            if start != -1 and end != -1:
                think_text = response[start + len(start_tag):end].strip()
                cprint(think_text, "grey")
                print("")
                # Remove the thinking part from the response
                response = response[:start] + response[end + len(end_tag):]
            print(response.strip())
            print("")
            

async def main():
    await chat_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")