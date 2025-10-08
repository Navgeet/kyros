#!/usr/bin/env python3
"""
Terminal-based Conversation Analysis Agent with Feedback-Improvement Loop

This agent analyzes conversations from saved sessions and generates learnings
from the feedback provided. It follows a similar feedback-improvement pattern
as agent_v2.py but operates in terminal mode.

Usage:
    python conversation_analysis_agent.py <session_id>
    python conversation_analysis_agent.py --list  # List available sessions
"""

import sys
import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests


class ConversationAnalysisAgent:
    """Terminal-based agent to analyze conversations and generate learnings from feedback."""

    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url or os.getenv("INTERNLM_API_URL", "http://localhost:23333")
        self.api_key = api_key or os.getenv("INTERNLM_API_KEY")

        # Directories
        self.conversations_dir = Path("v2/conversations")
        self.analysis_dir = Path("analysis_results")
        self.analysis_dir.mkdir(exist_ok=True)

        # Current analysis state
        self.session_data = None
        self.current_analysis = ""
        self.improvement_cycle = 0
        self.analysis_history = []

    def list_available_sessions(self) -> List[str]:
        """List all available conversation sessions."""
        if not self.conversations_dir.exists():
            return []

        session_files = list(self.conversations_dir.glob("*.json"))
        sessions = []

        for file_path in session_files:
            session_id = file_path.stem
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    created_at = data.get('created_at', 'Unknown')
                    user_request = data.get('user_request', 'No request')[:50]
                    message_count = len(data.get('conversation_history', []))

                sessions.append({
                    'id': session_id,
                    'file': file_path.name,
                    'created': created_at,
                    'request': user_request,
                    'messages': message_count
                })
            except Exception as e:
                print(f"⚠️  Warning: Could not read session {session_id}: {e}")

        return sessions

    def load_session(self, session_id: str) -> bool:
        """Load conversation data for the given session."""
        session_file = self.conversations_dir / f"{session_id}.json"

        if not session_file.exists():
            print(f"❌ Session file not found: {session_file}")
            return False

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                self.session_data = json.load(f)

            print(f"✅ Loaded session: {session_id}")
            print(f"📅 Created: {self.session_data.get('created_at', 'Unknown')}")
            print(f"👤 User request: {self.session_data.get('user_request', 'No request')}")
            print(f"💬 Messages: {len(self.session_data.get('conversation_history', []))}")
            print(f"📝 Has text plan: {bool(self.session_data.get('text_plan'))}")
            print(f"🐍 Has code: {bool(self.session_data.get('python_code'))}")

            return True

        except Exception as e:
            print(f"❌ Error loading session: {e}")
            return False

    def extract_feedback_instances(self) -> List[Dict[str, Any]]:
        """Extract all feedback instances from the conversation."""
        feedback_instances = []
        conversation = self.session_data.get('conversation_history', [])

        for i, message in enumerate(conversation):
            if message.get('from') == 'user':
                # Look for feedback patterns
                content = message.get('content', '').lower()

                # Check if this is feedback (not initial request)
                if i > 0 and any(keyword in content for keyword in [
                    'feedback', 'improve', 'change', 'better', 'fix', 'wrong',
                    'instead', 'rather', 'modify', 'adjust', 'update', 'revise'
                ]):
                    # Find the previous system response (what they're giving feedback on)
                    previous_system_content = None
                    for j in range(i-1, -1, -1):
                        if conversation[j].get('from') == 'system':
                            previous_system_content = conversation[j].get('content', '')
                            break

                    feedback_instances.append({
                        'feedback_message': message.get('content', ''),
                        'timestamp': message.get('timestamp', ''),
                        'previous_system_content': previous_system_content,
                        'context_index': i,
                        'screenshot': message.get('screenshot')
                    })

        return feedback_instances

    def generate_initial_analysis(self) -> str:
        """Generate initial analysis of the conversation and feedback patterns."""
        if not self.session_data:
            return "❌ No session data loaded."

        print("🔍 Analyzing conversation and feedback patterns...")

        feedback_instances = self.extract_feedback_instances()
        conversation = self.session_data.get('conversation_history', [])

        analysis_prompt = f"""
Using the given conversation snapshot generate a set of learnings that should be used to automatically improve future responses without user feedback.
Generate as many learnings as required (but no duplicates). Each learning should include a summary and example(s) from the conversation.
Only generate learnings using user feedback, don't make up stuff.

CONVERSATION:
{json.dumps(conversation)}
"""

        try:
            analysis = self._call_llm_api(analysis_prompt)
            self.current_analysis = analysis
            self.analysis_history.append({
                'cycle': 0,
                'type': 'initial_analysis',
                'content': analysis,
                'timestamp': datetime.now().isoformat()
            })
            return analysis
        except Exception as e:
            return f"❌ Error generating analysis: {e}"

    def _format_conversation_summary(self, conversation: List[Dict]) -> str:
        """Format a summary of the conversation flow."""
        summary = []
        for i, msg in enumerate(conversation[:10]):  # First 10 messages
            sender = msg.get('from', 'unknown')
            content = msg.get('content', '')[:100]
            summary.append(f"{i+1}. {sender.upper()}: {content}...")

        if len(conversation) > 10:
            summary.append(f"... and {len(conversation) - 10} more messages")

        return '\n'.join(summary)

    def _format_feedback_analysis(self, feedback_instances: List[Dict]) -> str:
        """Format the feedback analysis section."""
        if not feedback_instances:
            return "No explicit feedback instances detected in the conversation."

        analysis = []
        for i, feedback in enumerate(feedback_instances, 1):
            analysis.append(f"""
Feedback Instance #{i}:
- User Feedback: {feedback['feedback_message'][:200]}...
- Context: Responding to system content about {feedback['previous_system_content'][:100] if feedback['previous_system_content'] else 'Unknown'}...
- Timestamp: {feedback['timestamp']}
""")

        return '\n'.join(analysis)

    def improve_analysis_with_feedback(self, user_feedback: str) -> str:
        """Improve the analysis based on user feedback."""
        self.improvement_cycle += 1

        print(f"🔄 Improvement cycle {self.improvement_cycle}: Refining analysis based on feedback...")

        improvement_prompt = f"""
You are refining a conversation analysis based on user feedback.

ORIGINAL ANALYSIS:
{self.current_analysis}

USER FEEDBACK:
{user_feedback}

IMPROVEMENT REQUEST:
The user has provided feedback on the analysis above. Please improve the analysis by:
1. Addressing the specific points raised in the feedback
2. Adding more depth or detail where requested
3. Correcting any misunderstandings or errors
4. Incorporating the user's perspective and insights

Provide an improved version of the analysis that addresses the feedback while maintaining the original structure and comprehensive coverage.

Focus on being more specific, actionable, and aligned with what the user is looking for.
"""

        try:
            improved_analysis = self._call_llm_api(improvement_prompt)
            self.current_analysis = improved_analysis
            self.analysis_history.append({
                'cycle': self.improvement_cycle,
                'type': 'improvement',
                'feedback': user_feedback,
                'content': improved_analysis,
                'timestamp': datetime.now().isoformat()
            })
            return improved_analysis
        except Exception as e:
            return f"❌ Error improving analysis: {e}"

    def _call_llm_api(self, prompt: str) -> str:
        """Call the LLM API to generate responses."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": "internvl3.5-241b-a28b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.3  # Lower temperature for more consistent analysis
        }

        response = requests.post(
            f"{self.api_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")

        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    def save_analysis_results(self) -> str:
        """Save the analysis results to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{self.session_data['session_id']}_{timestamp}.json"
        filepath = self.analysis_dir / filename

        analysis_data = {
            'session_id': self.session_data['session_id'],
            'analyzed_at': datetime.now().isoformat(),
            'session_metadata': {
                'created_at': self.session_data.get('created_at'),
                'user_request': self.session_data.get('user_request'),
                'message_count': len(self.session_data.get('conversation_history', [])),
                'has_text_plan': bool(self.session_data.get('text_plan')),
                'has_code': bool(self.session_data.get('python_code'))
            },
            'feedback_instances': self.extract_feedback_instances(),
            'improvement_cycles': self.improvement_cycle,
            'analysis_history': self.analysis_history,
            'final_analysis': self.current_analysis,
            'agent_version': "conversation_analysis_v1.0"
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def run_interactive_analysis(self, session_id: str):
        """Run the interactive analysis session."""
        print("=" * 70)
        print("🔬 CONVERSATION ANALYSIS AGENT")
        print("=" * 70)
        print("I analyze conversations and generate learnings from feedback patterns.")
        print("Type 'help' for commands, 'quit' to exit.")
        print("=" * 70)

        # Load session
        if not self.load_session(session_id):
            return

        print("\n" + "="*50)
        print("🔍 GENERATING INITIAL ANALYSIS")
        print("="*50)

        # Generate initial analysis
        initial_analysis = self.generate_initial_analysis()
        print("\n" + "="*50)
        print("📊 INITIAL ANALYSIS RESULTS")
        print("="*50)
        print(initial_analysis)

        # Interactive feedback loop
        print("\n" + "="*50)
        print("💬 FEEDBACK & IMPROVEMENT LOOP")
        print("="*50)
        print("Provide feedback on the analysis to improve it, or type commands:")
        print("• 'approve' - Accept the current analysis")
        print("• 'save' - Save analysis results to file")
        print("• 'history' - Show improvement history")
        print("• 'help' - Show all commands")
        print("• 'quit' - Exit the program")

        while True:
            try:
                print(f"\n[Cycle {self.improvement_cycle}] 👤 Your feedback: ", end="")
                user_input = input().strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n🔬 Analysis session ended. Results are available for saving.")
                    break

                elif user_input.lower() in ['approve', 'accept', 'done']:
                    print("✅ Analysis approved! Saving results...")
                    filepath = self.save_analysis_results()
                    print(f"💾 Analysis saved to: {filepath}")
                    break

                elif user_input.lower() == 'save':
                    filepath = self.save_analysis_results()
                    print(f"💾 Analysis saved to: {filepath}")
                    continue

                elif user_input.lower() == 'history':
                    self._show_improvement_history()
                    continue

                elif user_input.lower() == 'help':
                    self._show_help()
                    continue

                else:
                    # Treat as feedback for improvement
                    print("\n🔄 Processing your feedback...")
                    improved_analysis = self.improve_analysis_with_feedback(user_input)

                    print("\n" + "="*50)
                    print(f"📊 IMPROVED ANALYSIS (Cycle {self.improvement_cycle})")
                    print("="*50)
                    print(improved_analysis)

            except KeyboardInterrupt:
                print("\n\n🔬 Analysis interrupted. Use 'save' to save current progress.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def _show_improvement_history(self):
        """Show the history of analysis improvements."""
        print("\n" + "="*40)
        print("📈 IMPROVEMENT HISTORY")
        print("="*40)

        if not self.analysis_history:
            print("No improvements made yet.")
            return

        for entry in self.analysis_history:
            print(f"\nCycle {entry['cycle']} ({entry['type']}):")
            print(f"Timestamp: {entry['timestamp']}")
            if 'feedback' in entry:
                print(f"Feedback: {entry['feedback'][:100]}...")
            print(f"Analysis preview: {entry['content'][:150]}...")
            print("-" * 40)

    def _show_help(self):
        """Show help information."""
        print("\n" + "="*40)
        print("📖 HELP - AVAILABLE COMMANDS")
        print("="*40)
        print("• approve/accept/done - Accept current analysis and save")
        print("• save - Save current analysis results")
        print("• history - Show improvement history")
        print("• help - Show this help message")
        print("• quit/exit/q - Exit the program")
        print("\nOr provide feedback to improve the analysis:")
        print("• 'Focus more on the technical aspects'")
        print("• 'Add more specific examples'")
        print("• 'Analyze the emotional tone of interactions'")
        print("• etc.")
        print("="*40)


def main():
    """Main function to run the conversation analysis agent."""
    parser = argparse.ArgumentParser(
        description="Analyze conversations and generate learnings from feedback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python conversation_analysis_agent.py abc12345
  python conversation_analysis_agent.py --list
  python conversation_analysis_agent.py --session abc12345 --api-url http://localhost:23333
        """
    )

    parser.add_argument('session_id', nargs='?', help='Session ID to analyze')
    parser.add_argument('--list', action='store_true', help='List available sessions')
    parser.add_argument('--session', help='Session ID to analyze (alternative to positional arg)')
    parser.add_argument('--api-url', help='API URL for the LLM service')
    parser.add_argument('--api-key', help='API key for authentication')

    args = parser.parse_args()

    # Create the agent
    agent = ConversationAnalysisAgent(api_url=args.api_url, api_key=args.api_key)

    # Handle list command
    if args.list:
        print("📋 Available conversation sessions:")
        print("="*70)
        sessions = agent.list_available_sessions()

        if not sessions:
            print("No conversation sessions found in the 'conversations' directory.")
            return

        for session in sessions:
            print(f"🆔 {session['id']}")
            print(f"   📅 Created: {session['created']}")
            print(f"   👤 Request: {session['request']}...")
            print(f"   💬 Messages: {session['messages']}")
            print(f"   📁 File: {session['file']}")
            print("-" * 50)

        print(f"\nTo analyze a session: python {sys.argv[0]} <session_id>")
        return

    # Determine session ID
    session_id = args.session_id or args.session
    if not session_id:
        print("❌ Error: Session ID is required.")
        print(f"Usage: python {sys.argv[0]} <session_id>")
        print(f"       python {sys.argv[0]} --list")
        sys.exit(1)

    # Check API configuration
    if not agent.api_key:
        print("⚠️  Warning: No API key found. Set INTERNLM_API_KEY environment variable.")
        print("The agent will attempt to use the API without authentication.")

    # Run the analysis
    try:
        agent.run_interactive_analysis(session_id)
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
