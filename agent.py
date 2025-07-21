#!/usr/bin/env python3

import argparse
from planner import Planner
from executor import Executor

class AIAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.planner = Planner(ollama_url)
        self.executor = Executor()
    
    def run_task(self, user_input: str) -> bool:
        """Run a single task with the given user input."""
        print(f"📝 Task: {user_input}")
        print()
        
        # Plan phase
        print("🧠 Planning...")
        tasks = self.planner.generate_plan(user_input)
        
        print("📋 Generated plan:")
        self._print_tasks(tasks)
        print()
        
        # Execute phase
        print("⚙️  Executing...")
        success = self.executor.execute_plan(tasks)
        
        if success:
            print("🎉 Task completed successfully!")
        else:
            print("❌ Task failed!")
        
        return success
    
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
    
    def run_interactive(self):
        """Run the agent in interactive mode - continuous loop."""
        print("🤖 AI Agent starting in interactive mode...")
        print("Type 'quit', 'exit', or 'q' to stop.")
        print()
        
        while True:
            try:
                user_input = input("Enter task: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q', '']:
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
        agent.run_interactive()

if __name__ == "__main__":
    main()