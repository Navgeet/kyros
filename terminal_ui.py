"""
Terminal UI module for displaying agent outputs in a Claude Code-like interface.
"""

import sys
import os
import time
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
        self.current_agent_for_actions = None  # Track which agent is executing actions
        self.action_count = 0  # Count actions for the current agent
        self.status_line_shown = False  # Track if status line is currently displayed
        self.status_dot_count = 0  # Track loader animation (0-3 for 0-3 dots)
        self.last_action_line_count = 0  # Track how many lines the last action took
        self.last_status_update = 0  # Track last time status was updated for throttling
        self.current_status_type = None  # Track current operation type (Thinking/Verifying/Compacting)
        self.status_start_time = 0  # Track when status started for timeout detection
        self.STATUS_TIMEOUT = 30  # Clear status after 30 seconds of inactivity

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

    def format_delegation(self, from_agent: str, to_agent: str, message: str) -> str:
        """Format agent delegation: FromAgent -> ToAgent: message"""
        # Clean up agent names - remove "Agent" suffix
        from_clean = from_agent.replace("Agent", "")
        to_clean = to_agent.replace("Agent", "")

        # Special rename: BrowserAction -> Browser
        if to_clean == "BrowserAction":
            to_clean = "Browser"
        if from_clean == "BrowserAction":
            from_clean = "Browser"

        prefix = Fore.GREEN + Style.BRIGHT + from_clean + Style.RESET_ALL
        arrow = Fore.WHITE + Style.DIM + " -> " + Style.RESET_ALL
        agent = Fore.CYAN + Style.BRIGHT + to_clean + Style.RESET_ALL
        colon = Fore.WHITE + Style.DIM + ": " + Style.RESET_ALL
        return f"{prefix}{arrow}{agent}{colon}{message}"

    def format_action_message(self, action, agent_type: str = None, is_first: bool = False) -> str:
        """Format an action execution message"""
        # Handle both string and dict actions
        if isinstance(action, dict):
            # Format dict action nicely
            tool = action.get('tool', 'unknown')
            args = action.get('args', {})
            if args:
                # Format args compactly - truncate long values
                formatted_args = []
                for k, v in args.items():
                    v_str = str(v)
                    if len(v_str) > 50:
                        v_str = v_str[:47] + "..."
                    formatted_args.append(f'{k}={v_str}')
                args_str = ', '.join(formatted_args)
                action_str = f"{tool}({args_str})"
            else:
                action_str = f"{tool}()"
        else:
            action_str = str(action)

        # Clean up agent name - remove "Agent" suffix
        if agent_type:
            agent_type = agent_type.replace('Agent', '')
            # Special rename: BrowserAction -> Browser
            if agent_type == "BrowserAction":
                agent_type = "Browser"

        # Determine agent color - use consistent colors
        agent_colors = {
            'gui': Fore.CYAN,
            'shell': Fore.CYAN,
            'browser': Fore.CYAN,
            'browseraction': Fore.CYAN,
            'browserboss': Fore.CYAN,
            'research': Fore.CYAN,
            'xpath': Fore.CYAN,
        }

        agent_name = agent_type.lower() if agent_type else 'browser'
        color = agent_colors.get(agent_name, Fore.CYAN)

        if is_first:
            # First action shows the agent label
            prefix = color + Style.BRIGHT + agent_type + ": " + Style.RESET_ALL
        else:
            # Subsequent actions align with first
            prefix = " " * len(agent_type) + "  "

        checkmark = Fore.GREEN + " ✓" + Style.RESET_ALL
        return f"{prefix}{action_str}{checkmark}"


    def handle_event(self, event: Dict[str, Any]):
        """Handle a WebSocket event and update display"""
        event_type = event.get('type')
        data = event.get('data', {})

        if event_type == 'task_submitted':
            # Skip task submission in clean mode
            pass

        elif event_type == 'delegation':
            # Clear any status before showing delegation
            self.clear_status()
            # Show delegation: FromAgent -> ToAgent: message
            from_agent = data.get('from_agent', 'Boss')
            to_agent = data.get('agent_type', data.get('to_agent', 'Unknown'))
            message = data.get('message', '')
            print(self.format_delegation(from_agent, to_agent, message))

        elif event_type == 'llm_call_start':
            # Track which agent is calling LLM but don't show status yet
            agent_type = event.get('agent_type', data.get('purpose', ''))
            self.in_llm_call = True
            self.llm_buffer = ""
            self.current_agent_name = agent_type

            # Check if this is for compaction, verification, or regular thinking
            if 'context_compaction' in agent_type or data.get('purpose') == 'context_compaction':
                if self.current_status_type not in ["Verifying"]:
                    self.current_status_type = "Compacting"
            elif self.current_status_type not in ["Verifying", "Compacting"]:
                self.current_status_type = "Thinking"
            # Don't show status yet - wait for first chunk

        elif event_type == 'llm_content_chunk':
            # Accumulate LLM response chunks and update status animation
            chunk = data.get('content', '')
            self.llm_buffer += chunk
            # Show appropriate status based on current operation
            if self.current_status_type == "Verifying":
                self.show_status("Verifying")
            elif self.current_status_type == "Compacting":
                self.show_status("Compacting")
            elif self.current_status_type == "Thinking":
                self.show_status("Thinking")
            elif self.in_llm_call:
                self.show_status("Thinking")

        elif event_type == 'llm_call_end':
            # Clear thinking status and stop LLM call tracking
            self.in_llm_call = False
            self.llm_buffer = ""
            # Only clear status if it was Thinking (not Verifying/Compacting)
            if self.current_status_type == "Thinking":
                self.current_status_type = None
                self.clear_status()

        elif event_type == 'action_execute':
            # Clear any status before showing action
            self.clear_status()
            action = data.get('action', '')
            agent_type = event.get('agent_type', 'Browser')

            # Check if this is a new agent starting actions
            if self.current_agent_for_actions != agent_type:
                self.current_agent_for_actions = agent_type
                self.action_count = 0

            # Format and show action (format_action_message will clean up the name)
            is_first = self.action_count == 0
            self.action_count += 1
            action_output = self.format_action_message(action, agent_type, is_first)
            print(action_output)

            # Track how many lines this action took (for adding verification checkmark later)
            self.last_action_line_count = action_output.count('\n') + 1

        elif event_type == 'thought':
            # Skip thought events
            pass

        elif event_type == 'action_result':
            # Skip action results - checkmarks shown inline
            pass

        elif event_type == 'verification_start':
            # Set status type and show verifying status
            self.clear_status()  # Clear any existing status first
            self.current_status_type = "Verifying"
            self.show_status("Verifying")

        elif event_type == 'verification_update':
            # Update verifying animation
            self.current_status_type = "Verifying"
            self.show_status("Verifying")

        elif event_type == 'verification_end':
            # Clear verifying status completely
            self.current_status_type = None
            self.clear_status()
            # Check if verification was successful
            success = data.get('success', data.get('correct', False))
            if success:
                self.add_verification_checkmark()
            # Ensure status is cleared after adding checkmark
            self.clear_status()

        elif event_type == 'compaction_start':
            # Set status type and show compacting status
            self.clear_status()  # Clear any existing status
            self.current_status_type = "Compacting"
            self.show_status("Compacting")

        elif event_type == 'compaction_end':
            # Clear compacting status
            self.current_status_type = None
            self.clear_status()

        elif event_type == 'task_completed':
            # Clear any status before showing completion
            self.clear_status()
            result = event.get('result', data.get('result', ''))
            print()
            print(Fore.GREEN + Style.BRIGHT + "=" * 60)
            print("TASK COMPLETED")
            print("=" * 60 + Style.RESET_ALL)
            if result:
                print(result)
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

    def show_status(self, status_type: str):
        """Show a status line with animated loader (Thinking/Verifying/Compacting)"""
        # Throttle updates to slow down animation (200ms between updates)
        current_time = time.time()
        if current_time - self.last_status_update < 0.2:
            return
        self.last_status_update = current_time

        # Update current status type only if not already set (preserve from start events)
        if self.current_status_type is None:
            self.current_status_type = status_type.replace('\n', '')
            self.status_start_time = current_time

        # Check for timeout - if status has been showing for too long, clear it
        if self.status_line_shown and (current_time - self.status_start_time) > self.STATUS_TIMEOUT:
            self.clear_status()
            return

        # Clear previous status line if shown (goes back 2 lines: blank + status)
        if self.status_line_shown:
            sys.stdout.write('\033[F')  # Move cursor up one line (status)
            sys.stdout.write('\033[K')  # Clear line
            sys.stdout.write('\033[F')  # Move cursor up one line (blank)
            sys.stdout.write('\033[K')  # Clear line

        # Cycle through 0-3 dots
        self.status_dot_count = (self.status_dot_count + 1) % 4
        dots = "." * self.status_dot_count

        # Format status message (remove \n from status_type if present)
        clean_status = status_type.replace('\n', '')
        # Print blank line then status
        print()  # Blank line for spacing
        status_msg = Fore.YELLOW + Style.DIM + f"{clean_status}{dots}" + Style.RESET_ALL
        print(status_msg)
        sys.stdout.flush()

        self.status_line_shown = True

    def clear_status(self):
        """Clear the status line"""
        if self.status_line_shown:
            sys.stdout.write('\033[F')  # Move cursor up one line (status)
            sys.stdout.write('\033[K')  # Clear line
            sys.stdout.write('\033[F')  # Move cursor up one line (blank)
            sys.stdout.write('\033[K')  # Clear line
            sys.stdout.flush()
            self.status_line_shown = False
            self.status_dot_count = 0
            self.current_status_type = None
            self.status_start_time = 0  # Reset timeout tracking

    def add_verification_checkmark(self):
        """Add a second checkmark to the last action line to indicate successful verification"""
        if self.last_action_line_count > 0:
            # Move cursor up to the last action line
            for _ in range(self.last_action_line_count):
                sys.stdout.write('\033[F')

            # Move to end of line and add second checkmark
            sys.stdout.write('\033[999C')  # Move to far right
            sys.stdout.write('\b\b\b')  # Move back 3 characters
            sys.stdout.write(Fore.GREEN + " ✓✓" + Style.RESET_ALL)

            # Move cursor back down
            for _ in range(self.last_action_line_count):
                sys.stdout.write('\n')

            sys.stdout.flush()


# Create a global instance
terminal_ui = TerminalUI()
