"""Entry point for the example usage script."""

from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import the example
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

def main():
    """Main entry point for the example script."""
    # Import and run the example
    example_path = parent_dir / "example_usage.py"

    if example_path.exists():
        # Execute the example script
        with open(example_path) as f:
            example_code = f.read()

        # Replace the if __name__ == "__main__" check and execute
        example_code = example_code.replace('if __name__ == "__main__":\n    main()', 'main()')
        exec(example_code)
    else:
        print(f"Example script not found at {example_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()