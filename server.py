#!/usr/bin/env python

import asyncio
import base64
from functools import partial
import json
import os
from websockets.asyncio.server import serve
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_ollama.llms import OllamaLLM
from langchain_ollama import ChatOllama




client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "args": [ os.path.dirname(os.path.abspath(__file__)) + "/math_server.py"],
            "transport": "stdio",
        },
    }
)

from langchain_core.prompts import PromptTemplate

template = '''Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

prompt = PromptTemplate.from_template(template)

async def handler(agent, websocket):
    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
            except Exception:
                print("Received non-JSON message")
                continue

            if "prompt" in msg:
                prompt = msg.get("prompt", "")
                context = msg.get("context", {})
                img_b64 = context.get("screen", "")
                if img_b64:
                    print(f"Received screenshot in context ({len(img_b64)} bytes base64)")
                    # Optionally, save the screenshot:
                    # img_bytes = base64.b64decode(img_b64)
                    # with open("screenshot.png", "wb") as f:
                    #     f.write(img_bytes)
                print(f"Chat received: {prompt}")

                resp = await agent.ainvoke({"messages": [prompt]})
                await websocket.send(resp["messages"][-1].text())
            else:
                print("Unknown message type")
    except Exception as e:
        print(f"Chat connection closed: {e}")



async def main():
    tools = await client.get_tools()
    llm = ChatOllama(model="qwen3:30b-a3b")
    agent = create_react_agent(llm, tools)
    async with serve(partial(handler, agent), "localhost", 8765):
        print("Server listening on ws://localhost:8765 ")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())