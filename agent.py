#!/usr/bin/env python3

import argparse
import asyncio
from planner import Planner
from executor import Executor
from utils import input

class AIAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.planner = Planner(ollama_url)
        self.executor = Executor()
    
    def run_task(self, user_input: str, max_retries: int = 3) -> bool:
        """Run a single task with the given user input."""
        print(f"📝 Task: {user_input}")
        print()
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"🔄 Retrying task (attempt {attempt + 1}/{max_retries})...")
                print()
            
            # Plan phase
            print("🧠 Planning...")
            tasks = self.planner.generate_plan(user_input)
            
            if not tasks:
                print("❌ Failed to generate plan!")
                continue
            
            print("📋 Generated plan:")
            self._print_tasks(tasks)
            print()
            
            # Execute phase
            print("⚙️  Executing...")
            success = self.executor.execute_plan(tasks)
            
            if success:
                print("🎉 Task completed successfully!")
                return True
            else:
                print(f"❌ Task execution failed (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    print("🔄 Going back to planning...")
                    print()
        
        print("❌ Task failed after all retry attempts!")
        return False
    
    def _print_tasks(self, tasks, indent=0):
        """Print tasks with their subtasks in a hierarchical format."""
        for task in tasks:
            prefix = "  " * indent
            deps_str = ""
            if task.dependencies:
                dep_names = [dep.name for dep in task.dependencies]
                deps_str = f" (depends on: {', '.join(dep_names)})"
            
            print(f"{prefix}{task.name}{deps_str}")
            
            if task.subtasks:
                self._print_tasks(task.subtasks, indent + 1)
    
    async def run_interactive(self):
        """Run the agent in interactive mode - continuous loop."""
        print("🤖 AI Agent starting in interactive mode...")
        print("Type 'quit', 'exit', or 'q' to stop.")
        print()
        
        while True:
            try:
                user_input = await input()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                print()
                self.run_task(user_input)
                print("-" * 50)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print()

def main():
    parser = argparse.ArgumentParser(description='AI Agent with planning and execution')
    parser.add_argument('--task', type=str, 
                       help='Single task to execute (if not provided, runs in interactive mode)')
    parser.add_argument('--ollama-url', type=str, 
                       default='http://localhost:11434',
                       help='Ollama server URL')
    
    args = parser.parse_args()
    
    agent = AIAgent(args.ollama_url)
    
    if args.task:
        # Single task mode
        agent.run_task(args.task)
    else:
        # Interactive mode
        asyncio.run(agent.run_interactive())

if __name__ == "__main__":
    main()