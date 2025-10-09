import sys
import argparse
import asyncio
from typing import Dict, Any
from agents.boss_agent import BossAgent
from websocket_server import WebSocketServer
import config
import time


class MultiAgentOrchestrator:
    """Main orchestrator for the multi-agent system"""

    def __init__(self, websocket_server: WebSocketServer):
        self.websocket_server = websocket_server
        self.boss_agent = None
        self.config = None

    async def initialize(self):
        """Initialize the orchestrator and boss agent"""
        # Load configuration
        try:
            self.config = config.load_config()
            print("Configuration loaded successfully")
        except Exception as e:
            print(f"Warning: Failed to load config.yaml, using environment variables: {e}")
            self.config = None

        # Create websocket callback
        ws_callback = self.websocket_server.create_websocket_callback()

        # Create boss agent
        self.boss_agent = BossAgent(
            websocket_callback=ws_callback,
            config_dict=self.config
        )

    async def process_task(self, task: str) -> Dict[str, Any]:
        """Process a task using the boss agent"""
        try:
            if not self.boss_agent:
                await self.initialize()

            # Send task to boss agent
            message = {
                "content": task,
                "agent_responses": []
            }

            max_iterations = 20
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                try:
                    # Process message with boss agent
                    response = self.boss_agent.process_message(message)

                    action = response.get("action", {})
                    action_type = action.get("type")

                    if action_type == "exit":
                        # Task complete
                        return {
                            "success": True,
                            "result": action.get("message", "Task completed"),
                            "iterations": iteration
                        }

                    elif action_type == "message":
                        # Boss is asking user for feedback
                        user_message = action.get("message", "")
                        wait_for_response = action.get("wait_for_response", True)

                        # Broadcast to UI
                        await self.websocket_server.broadcast({
                            "type": "user_prompt",
                            "data": {
                                "message": user_message,
                                "thought": response.get("thought", ""),
                                "wait_for_response": wait_for_response
                            }
                        })

                        if wait_for_response:
                            # Prompt user in terminal
                            print(f"\n{'='*60}")
                            print(f"BOSS AGENT: {user_message}")
                            print(f"{'='*60}")
                            user_response = input("Your response: ").strip()

                            time.sleep(5)

                            # Add user response to message for next iteration
                            if not user_response:
                                user_response = "No response provided"

                            # Add to agent responses
                            if "agent_responses" not in message:
                                message["agent_responses"] = []

                            message["agent_responses"].append({
                                "agent_type": "User",
                                "agent_id": "user",
                                "response": {
                                    "success": True,
                                    "message": user_response
                                }
                            })

                            # Broadcast user response
                            await self.websocket_server.broadcast({
                                "type": "user_response",
                                "data": {
                                    "message": user_response
                                }
                            })

                    elif action_type == "respond":
                        # Boss is responding to user
                        await self.websocket_server.broadcast({
                            "type": "boss_response",
                            "data": {
                                "message": action.get("message", ""),
                                "thought": response.get("thought", "")
                            }
                        })

                    elif action_type == "delegate":
                        # Boss is delegating to a subagent
                        agent_type = action.get("agent")
                        agent_message = action.get("message", "")

                        try:
                            # Get or create the subagent (single instance per type)
                            agent = self.boss_agent.get_or_create_agent(agent_type)

                            # Send delegation broadcast
                            await self.websocket_server.broadcast({
                                "type": "delegation",
                                "data": {
                                    "agent_type": agent_type,
                                    "agent_id": agent.agent_id,
                                    "message": agent_message,
                                    "thought": response.get("thought", "")
                                }
                            })

                            # Process message with subagent
                            subagent_response = agent.process_message({
                                "content": agent_message
                            })

                            # Add subagent response to message for next iteration
                            if "agent_responses" not in message:
                                message["agent_responses"] = []

                            message["agent_responses"].append({
                                "agent_type": agent_type,
                                # "agent_id": agent.agent_id,
                                "response": subagent_response
                            })

                        except Exception as e:
                            print(f"ERROR: Failed to delegate to {agent_type}: {e}")
                            import traceback
                            traceback.print_exc()
                            # Continue to next iteration with error info
                            if "agent_responses" not in message:
                                message["agent_responses"] = []
                            message["agent_responses"].append({
                                "agent_type": agent_type,
                                "agent_id": "unknown",
                                "response": {
                                    "success": False,
                                    "error": str(e)
                                }
                            })

                except Exception as e:
                    print(f"ERROR: Failed to process iteration {iteration}: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "success": False,
                        "error": f"Error in iteration {iteration}: {str(e)}",
                        "iterations": iteration
                    }

            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": iteration
            }

        except Exception as e:
            print(f"ERROR: Failed to process task: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "iterations": 0
            }


async def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Computer-Use System")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket server port")
    parser.add_argument("--task", type=str, default=None, help="Task to execute (if not using web interface)")

    args = parser.parse_args()

    # Create WebSocket server
    ws_server = WebSocketServer(host=args.host, port=args.port)

    # Create orchestrator
    orchestrator = MultiAgentOrchestrator(ws_server)

    # Start WebSocket server
    await ws_server.start()

    print(f"WebSocket server: ws://{args.host}:{args.port}")
    print(f"Open the frontend to submit tasks, or use --task flag to run a task directly")

    # If a task was provided via CLI, execute it
    if args.task:
        print(f"\nExecuting task: {args.task}")
        result = await orchestrator.process_task(args.task)
        print(f"\nResult: {result}")
        return

    # Otherwise, keep running and wait for tasks from the web interface
    try:
        # Set up the task handler to use our orchestrator
        from aiohttp import web

        async def task_handler(request):
            try:
                time.sleep(2)

                data = await request.json()
                task = data.get('task')

                if not task:
                    return web.json_response({'error': 'No task provided'}, status=400)

                # Broadcast task submission
                await ws_server.broadcast({
                    'type': 'task_submitted',
                    'data': {'task': task}
                })

                # Process task with orchestrator
                result = await orchestrator.process_task(task)

                # Broadcast completion
                await ws_server.broadcast({
                    'type': 'task_completed',
                    'data': result
                })

                return web.json_response({
                    'success': True,
                    'result': result
                })

            except Exception as e:
                print(f"ERROR: Task handler failed: {e}")
                import traceback
                traceback.print_exc()
                return web.json_response({'error': str(e)}, status=500)

        # Set the custom task handler
        ws_server.set_task_handler(task_handler)

        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
