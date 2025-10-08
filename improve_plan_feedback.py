#!/usr/bin/env python3
"""
Agent script to improve plans based on user feedback through conversation.
The agent and user have a conversation, and the transcript is saved to a file.
"""

import json
import datetime
import os
import requests
from typing import List, Dict, Any


class PlanImprovementAgent:
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv('INTERNLM_API_KEY')
        self.base_url = base_url or os.getenv('INTERNLM_BASE_URL', 'https://internlm-chat.intern-ai.org.cn/puyu/api/v1')
        self.conversation_history: List[Dict[str, str]] = []
        self.current_plan = ""
        self.transcript_file = f"plan_improvement_transcript_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    def log_to_transcript(self, speaker: str, message: str):
        """Log a message to the conversation transcript file."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.transcript_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {speaker}: {message}\n")

    def get_agent_response(self, user_input: str) -> str:
        """Get agent response using InternLM API."""
        system_prompt = """You are a helpful AI agent that specializes in improving plans based on user feedback.

Your role is to:
1. Understand the user's current plan or goal
2. Listen to their feedback and concerns
3. Ask clarifying questions when needed
4. Suggest specific improvements to make the plan better
5. Iterate on the plan based on the conversation

Keep your responses conversational, helpful, and focused on plan improvement. If no plan has been shared yet, ask the user to describe their current plan or goal."""

        # Add current conversation to history
        self.conversation_history.append({"role": "user", "content": user_input})

        # Prepare messages for API call
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": "internlm2.5-latest",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
                "stream": False
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                agent_response = response_data["choices"][0]["message"]["content"].strip()
                self.conversation_history.append({"role": "assistant", "content": agent_response})
                return agent_response
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                return "I'm sorry, I encountered an API error. Please try again."

        except Exception as e:
            error_msg = f"Error getting agent response: {str(e)}"
            print(f"❌ {error_msg}")
            return "I'm sorry, I encountered an error. Please try again."

    def print_header(self):
        """Print the program header."""
        print("=" * 60)
        print("🤖 PLAN IMPROVEMENT AGENT")
        print("=" * 60)
        print("I'm here to help you improve your plans based on your feedback!")
        print("Share your plan or goal, and I'll help you make it better.")
        print("Type 'quit', 'exit', or 'bye' to end the conversation.")
        print("Type 'save' to save the current improved plan.")
        print("-" * 60)
        print(f"📝 Conversation transcript will be saved to: {self.transcript_file}")
        print("=" * 60)

    def save_plan(self):
        """Save the current improved plan to a file."""
        if not self.current_plan:
            print("❌ No plan to save yet. Continue the conversation to develop a plan.")
            return

        plan_file = f"improved_plan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write(f"Improved Plan - Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(self.current_plan)
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("This plan was improved through conversation with the Plan Improvement Agent.\n")

        print(f"✅ Plan saved to: {plan_file}")
        self.log_to_transcript("SYSTEM", f"Plan saved to {plan_file}")

    def run(self):
        """Main conversation loop."""
        self.print_header()

        # Initialize transcript file
        self.log_to_transcript("SYSTEM", "Plan Improvement Agent conversation started")

        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()

                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n🤖 Agent: Thank you for the conversation! Your transcript has been saved.")
                    self.log_to_transcript("USER", user_input)
                    self.log_to_transcript("AGENT", "Thank you for the conversation! Your transcript has been saved.")
                    self.log_to_transcript("SYSTEM", "Conversation ended")
                    break

                # Check for save command
                if user_input.lower() == 'save':
                    self.save_plan()
                    self.log_to_transcript("USER", user_input)
                    self.log_to_transcript("SYSTEM", "User requested to save plan")
                    continue

                # Skip empty input
                if not user_input:
                    continue

                # Log user input
                self.log_to_transcript("USER", user_input)

                # Get agent response
                print("\n🤖 Agent: ", end="", flush=True)
                agent_response = self.get_agent_response(user_input)
                print(agent_response)

                # Log agent response
                self.log_to_transcript("AGENT", agent_response)

                # Update current plan if the agent provides one
                if "plan:" in agent_response.lower() or "here's" in agent_response.lower():
                    self.current_plan = agent_response

            except KeyboardInterrupt:
                print("\n\n🤖 Agent: Conversation interrupted. Your transcript has been saved.")
                self.log_to_transcript("SYSTEM", "Conversation interrupted by user (Ctrl+C)")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                self.log_to_transcript("SYSTEM", f"Error occurred: {str(e)}")


def main():
    """Main function to run the plan improvement agent."""
    try:
        # Check for API key
        api_key = os.getenv('INTERNLM_API_KEY')
        if not api_key:
            print("❌ Error: INTERNLM_API_KEY environment variable not set.")
            print("Please set your InternLM API key:")
            print("export INTERNLM_API_KEY='your-api-key-here'")
            print("Optionally set custom base URL:")
            print("export INTERNLM_BASE_URL='your-base-url-here'")
            return

        # Create and run the agent
        agent = PlanImprovementAgent(api_key)
        agent.run()

    except Exception as e:
        print(f"❌ Failed to start the agent: {str(e)}")


if __name__ == "__main__":
    main()