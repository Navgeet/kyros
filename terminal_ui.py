"""
Terminal UI module for displaying agent outputs in a Claude Code-like interface.
"""

import sys
import os
from typing import Dict, Any, Optional
from colorama import init, Fore, Style, Back
import textwrap

# Initialize colorama for cross-platform color support
init(autoreset=True)

ASCII_ART = """
╦╔═ ╦ ╦ ╦═╗ ╔═╗ ╔═╗
╠╩╗ ╚╦╝ ╠╦╝ ║ ║ ╚═╗
╩ ╩  ╩  ╩╚═ ╚═╝ ╚═╝
"""

class TerminalUI:
    """Manages terminal output formatting for agent system"""

    def __init__(self):
        self.current_boss_output = ""
        self.current_subagent_output = ""
        self.current_subagent_type = ""
        self.lines_written = 0
        self.in_llm_call = False
        self.llm_buffer = ""
        self.current_agent_name = ""
        self.streaming_mode = True  # Enable streaming with in-place updates

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_banner(self):
        """Print ASCII art banner"""
        self.clear_screen()
        print(Fore.CYAN + Style.BRIGHT + ASCII_ART)
        # print(Fore.WHITE + Style.BRIGHT + "Kyros Agent System")
        # print(Fore.WHITE + Style.DIM + "Multi-agent orchestrator with vision capabilities")
        print()

    def clear_current_output(self):
        """Clear the current output by moving cursor up and clearing lines"""
        if self.lines_written > 0:
            # Move cursor up and clear lines
            for _ in range(self.lines_written):
                sys.stdout.write('\033[F')  # Move cursor up one line
                sys.stdout.write('\033[K')  # Clear line
            sys.stdout.flush()
            self.lines_written = 0

    def count_display_lines(self, text: str, width: int = 80) -> int:
        """Count how many lines text will take when displayed"""
        lines = 0
        for line in text.split('\n'):
            if not line:
                lines += 1
            else:
                # Account for wrapping
                lines += max(1, (len(line) + width - 1) // width)
        return lines

    def format_boss_message(self, content: str) -> str:
        """Format a boss agent message"""
        prefix = Fore.GREEN + Style.BRIGHT + "Boss: " + Style.RESET_ALL
        # Wrap text to fit terminal width
        wrapped = textwrap.fill(content, width=76, initial_indent='', subsequent_indent='      ')
        return prefix + wrapped

    def format_subagent_message(self, agent_type: str, content: str) -> str:
        """Format a sub-agent message with indentation"""
        # Determine agent color
        agent_colors = {
            'gui': Fore.BLUE,
            'shell': Fore.YELLOW,
            'browser': Fore.MAGENTA,
            'research': Fore.CYAN,
            'xpath': Fore.WHITE,
        }
        color = agent_colors.get(agent_type.lower(), Fore.WHITE)

        prefix = Fore.GREEN + "|__" + color + Style.BRIGHT + agent_type.upper() + ": " + Style.RESET_ALL

        # Check if content contains code blocks
        if '```' in content:
            lines = content.split('\n')
            formatted_lines = []
            in_code_block = False

            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    formatted_lines.append('   ' + Fore.WHITE + Style.DIM + line)
                elif in_code_block:
                    formatted_lines.append('   ' + Fore.WHITE + line)
                else:
                    if line.strip():
                        wrapped = textwrap.fill(line, width=73, initial_indent='   ', subsequent_indent='   ')
                        formatted_lines.append(wrapped)
                    else:
                        formatted_lines.append('')

            return prefix + '\n' + '\n'.join(formatted_lines)
        else:
            # Regular text wrapping
            wrapped = textwrap.fill(content, width=73, initial_indent='', subsequent_indent='   ')
            return prefix + wrapped

    def format_action_message(self, action, result: Optional[str] = None) -> str:
        """Format an action execution message"""
        # Handle both string and dict actions
        if isinstance(action, dict):
            # Format dict action nicely
            tool = action.get('tool', 'unknown')
            args = action.get('args', {})
            if args:
                action_str = f"{tool}({', '.join(f'{k}={v}' for k, v in args.items())})"
            else:
                action_str = tool
        else:
            action_str = str(action)

        msg = Fore.YELLOW + "   → " + Style.RESET_ALL + action_str
        if result:
            msg += Fore.GREEN + " ✓" + Style.RESET_ALL
        return msg


    def handle_event(self, event: Dict[str, Any]):
        """Handle a WebSocket event and update display"""
        event_type = event.get('type')
        data = event.get('data', {})

        if event_type == 'task_submitted':
            task = event.get('task', data.get('task', ''))
            print(Fore.CYAN + Style.BRIGHT + f"\n{'='*60}")
            print(f"TASK: {task}")
            print(f"{'='*60}\n")

        elif event_type == 'boss_response':
            content = data.get('message', data.get('content', ''))
            # Print boss response immediately without overwriting
            print(self.format_boss_message(content))
            print()  # Empty line after

        elif event_type == 'delegation':
            agent_type = data.get('agent_type', '')
            message = data.get('message', '')
            # Print delegation message immediately
            print(self.format_subagent_message(agent_type, message))
            print()  # Empty line after

        elif event_type == 'llm_call_start':
            # Get agent type from event root, not data
            agent_type = event.get('agent_type', '')
            self.in_llm_call = True
            self.llm_buffer = ""
            self.current_agent_name = agent_type

        elif event_type == 'llm_content_chunk':
            chunk = data.get('content', '')
            self.llm_buffer += chunk
            # Don't print anything during streaming, wait for end

        elif event_type == 'llm_call_end':
            # Get agent type from event root
            agent_type = event.get('agent_type', self.current_agent_name)

            # Print formatted output once at the end
            if agent_type == 'BossAgent':
                print(self.format_boss_message(self.llm_buffer))
            else:
                # Format agent type name for display
                display_type = agent_type.replace('Agent', '').replace('Boss', '')
                print(self.format_subagent_message(display_type, self.llm_buffer))

            print()  # Empty line after each message
            self.in_llm_call = False
            self.llm_buffer = ""

        elif event_type == 'action_execute':
            action = data.get('action', '')
            # Show action being executed
            print(self.format_action_message(action))

        elif event_type == 'action_result':
            result = data.get('result', {})
            success = result.get('success', False)
            if success:
                print(Fore.GREEN + "   ✓ Action completed" + Style.RESET_ALL)
            else:
                error = result.get('error', 'Unknown error')
                print(Fore.RED + f"   ✗ Action failed: {error}" + Style.RESET_ALL)

        elif event_type == 'task_completed':
            result = event.get('result', data.get('result', ''))
            print(Fore.GREEN + Style.BRIGHT + f"\n{'='*60}")
            print(f"TASK COMPLETED")
            print(f"{'='*60}\n")
            if result:
                print(Fore.WHITE + result)
                print()

    def prompt_user(self, prompt_text: str) -> str:
        """Display a prompt and get user input"""
        # Clear any current output first
        if self.lines_written > 0:
            print()  # Add newline before prompt
            self.lines_written = 0

        print(Fore.YELLOW + Style.BRIGHT + "\n" + prompt_text)
        user_input = input(Fore.CYAN + "Your response: " + Style.RESET_ALL).strip()
        return user_input

    def show_error(self, error_msg: str):
        """Display an error message"""
        print(Fore.RED + Style.BRIGHT + "\n✗ Error: " + Style.RESET_ALL + error_msg)

    def show_info(self, info_msg: str):
        """Display an info message"""
        print(Fore.BLUE + Style.BRIGHT + "\nℹ " + Style.RESET_ALL + info_msg)


# Create a global instance
terminal_ui = TerminalUI()
