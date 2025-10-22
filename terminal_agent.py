"""
Terminal Agent - Standalone CLI interface without WebSocket dependency
"""

import asyncio
import sys
import os
from typing import Dict, Any, Optional, List
from agents.boss_agent import BossAgent
from terminal_ui import terminal_ui
import config
import readline
import atexit
import json
import time


class TerminalAgent:
    """Standalone terminal agent for CLI interaction"""

    def __init__(self):
        self.boss_agent: Optional[BossAgent] = None
        self.config = None
        self.history_file = os.path.expanduser("~/.kyros_history")
        self.max_history = 1000
        self._setup_history()
        self._setup_readline()

    def _setup_history(self):
        """Setup command history"""
        # Load history from file
        if os.path.exists(self.history_file):
            try:
                readline.read_history_file(self.history_file)
            except Exception as e:
                print(f"Warning: Could not load history: {e}")

        # Limit history size
        readline.set_history_length(self.max_history)

        # Save history on exit
        atexit.register(self._save_history)

    def _save_history(self):
        """Save command history to file"""
        try:
            readline.write_history_file(self.history_file)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")

    def _setup_readline(self):
        """Setup readline for better prompt experience"""
        # Enable tab completion
        readline.parse_and_bind("tab: complete")

        # Enable Ctrl+R for reverse search
        readline.parse_and_bind("\\C-r: reverse-search-history")

        # Enable Ctrl+S for forward search
        readline.parse_and_bind("\\C-s: forward-search-history")

    async def initialize(self):
        """Initialize the terminal agent and boss agent"""
        # Load configuration
        try:
            self.config = config.load_config()
            # terminal_ui.show_info("Configuration loaded successfully")
        except Exception as e:
            terminal_ui.show_info(f"Using environment variables (config.yaml not found)")
            self.config = None

        # Create a callback that sends events to terminal UI
        def terminal_callback(message: Dict[str, Any]):
            """Callback for agent events"""
            terminal_ui.handle_event(message)

        # Create boss agent without WebSocket
        self.boss_agent = BossAgent(
            websocket_callback=terminal_callback,
            config_dict=self.config
        )

    async def process_task(self, task: str) -> Dict[str, Any]:
        """Process a single task"""
        try:
            time.sleep(3)

            if not self.boss_agent:
                await self.initialize()

            # Send task event
            terminal_ui.handle_event({
                'type': 'task_submitted',
                'task': task
            })

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
                        result = action.get("message", "Task completed")
                        terminal_ui.handle_event({
                            'type': 'task_completed',
                            'result': result
                        })
                        return {
                            "success": True,
                            "result": result,
                            "iterations": iteration
                        }

                    elif action_type == "message":
                        # Boss is asking user for feedback
                        user_message = action.get("message", "")
                        wait_for_response = action.get("wait_for_response", True)

                        # Broadcast to UI
                        terminal_ui.handle_event({
                            'type': 'user_prompt',
                            'data': {
                                "message": user_message,
                                "thought": response.get("thought", ""),
                                "wait_for_response": wait_for_response
                            }
                        })

                        if wait_for_response:
                            # Prompt user in terminal
                            user_response = terminal_ui.prompt_user(user_message)

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
                            terminal_ui.handle_event({
                                'type': 'user_response',
                                'data': {
                                    "message": user_response
                                }
                            })

                    elif action_type == "respond":
                        # Boss is responding to user
                        terminal_ui.handle_event({
                            'type': 'boss_response',
                            'data': {
                                "message": action.get("message", ""),
                                "thought": response.get("thought", "")
                            }
                        })

                    elif action_type == "delegate":
                        # Boss is delegating to a subagent
                        agent_type = action.get("agent")
                        agent_message = action.get("message", "")

                        try:
                            # Get or create the subagent
                            agent = self.boss_agent.get_or_create_agent(agent_type)

                            # Send delegation broadcast
                            terminal_ui.handle_event({
                                'type': 'delegation',
                                'data': {
                                    "agent_type": agent_type,
                                    "agent_id": agent.agent_id,
                                    "message": agent_message,
                                    "thought": response.get("thought", "")
                                }
                            })

                            # Process message with subagent
                            import inspect
                            if inspect.iscoroutinefunction(agent.process_message):
                                subagent_response = await agent.process_message({
                                    "content": agent_message
                                })
                            else:
                                subagent_response = agent.process_message({
                                    "content": agent_message
                                })

                            # Add subagent response to message for next iteration
                            if "agent_responses" not in message:
                                message["agent_responses"] = []

                            message["agent_responses"].append({
                                "agent_type": agent_type,
                                "response": subagent_response
                            })

                        except Exception as e:
                            terminal_ui.show_error(f"Failed to delegate to {agent_type}: {e}")
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
                    terminal_ui.show_error(f"Failed to process iteration {iteration}: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "success": False,
                        "error": f"Error in iteration {iteration}: {str(e)}",
                        "iterations": iteration
                    }

            terminal_ui.show_error("Max iterations reached")
            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": iteration
            }

        except Exception as e:
            terminal_ui.show_error(f"Failed to process task: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "iterations": 0
            }

    async def run_interactive(self):
        """Run in interactive prompt mode"""
        terminal_ui.print_banner()

        # Show help message
        print("Welcome to Kyros! Type your task and press Enter.")
        print("Commands:")
        print("  /help    - Show this help message")
        print("  /clear   - Clear the screen")
        print("  /history - Show command history")
        print("  /exit    - Exit the program")
        print("  Ctrl+R   - Search command history")
        print()

        await self.initialize()

        while True:
            try:
                # Get user input with prompt
                from colorama import Fore, Style
                user_input = input(Fore.GREEN + Style.BRIGHT + "kyros> " + Style.RESET_ALL).strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.startswith('/'):
                    await self._handle_command(user_input)
                    continue

                # Process as a task
                print()  # Add newline before task output
                await self.process_task(user_input)
                print()  # Add newline after task output

            except KeyboardInterrupt:
                print("\n\nUse /exit to quit or Ctrl+D")
                continue
            except EOFError:
                print("\n\nGoodbye!")
                sys.exit(0)
            except Exception as e:
                terminal_ui.show_error(f"Unexpected error: {e}")
                import traceback
                traceback.print_exc()

    async def _handle_command(self, command: str):
        """Handle special commands"""
        cmd = command.lower().strip()

        if cmd == '/help':
            print("\nCommands:")
            print("  /help    - Show this help message")
            print("  /clear   - Clear the screen")
            print("  /history - Show command history")
            print("  /exit    - Exit the program")
            print("  Ctrl+R   - Search command history")
            print()

        elif cmd == '/clear':
            terminal_ui.clear_screen()

        elif cmd == '/history':
            print("\nCommand History:")
            history_len = readline.get_current_history_length()
            for i in range(1, history_len + 1):
                item = readline.get_history_item(i)
                if item:
                    print(f"  {i}: {item}")
            print()

        elif cmd == '/exit':
            print("\nGoodbye!")
            sys.exit(0)

        else:
            print(f"\nUnknown command: {command}")
            print("Type /help for available commands")
            print()


async def main():
    """Main entry point for terminal agent"""
    agent = TerminalAgent()
    await agent.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
