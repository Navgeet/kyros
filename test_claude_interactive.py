#!/usr/bin/env python3
"""
Standalone script to test Claude Code in interactive mode.
"""
import subprocess
import sys
import time
import fcntl
import os
import select

class ClaudeInteractiveTester:
    def __init__(self, claude_path="claude"):
        self.claude_path = claude_path
        self.process = None

    def start_session(self):
        """Start an interactive Claude Code session."""
        try:
            print(f"🚀 Starting Claude Code interactive session...")
            print(f"Command: {self.claude_path} --print")

            self.process = subprocess.Popen(
                [self.claude_path, "--print"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )

            print(f"✅ Process started with PID: {self.process.pid}")

            # Wait a moment for process to initialize
            time.sleep(1)

            # Check if process is still running
            if self.process.poll() is not None:
                stderr = self.process.stderr.read()
                print(f"❌ Process exited immediately with code {self.process.returncode}")
                print(f"stderr: {stderr}")
                return False

            print(f"✅ Claude Code session started successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to start Claude Code: {e}")
            return False

    def send_message(self, message):
        """Send a message to Claude and get response."""
        if not self.process:
            print("❌ No active session")
            return None

        try:
            print(f"\n📤 Sending: {message}")
            print("-" * 50)

            # Send message
            self.process.stdin.write(message + "\n")
            self.process.stdin.flush()

            # Read response with timeout
            response = self._read_response(timeout=30)

            print("-" * 50)
            print(f"📥 Received ({len(response.splitlines())} lines):")
            print(response)
            print("-" * 50)

            return response

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None

    def _read_response(self, timeout=30):
        """Read response from Claude with timeout."""
        response_lines = []
        start_time = time.time()

        # Make stdout non-blocking
        fd = self.process.stdout.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        while time.time() - start_time < timeout:
            try:
                # Use select to check if data is available
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)

                if ready:
                    line = self.process.stdout.readline()
                    if line:
                        line = line.rstrip()
                        response_lines.append(line)
                        print(f"📥 Line: {line}")

                        # Check for various end conditions
                        if (line.strip() == "```" and len(response_lines) > 1) or \
                           (len(response_lines) > 100):  # Safety limit
                            break
                else:
                    # No data available, short sleep
                    time.sleep(0.1)

                    # Check if we have some response and no new data for a while
                    if response_lines and time.time() - start_time > 5:
                        # If we have content and haven't received new data for 5s, break
                        break

            except IOError:
                # No data available
                time.sleep(0.1)

            # Check if process died
            if self.process.poll() is not None:
                print(f"❌ Process died with return code: {self.process.returncode}")
                stderr = self.process.stderr.read()
                if stderr:
                    print(f"stderr: {stderr}")
                break

        # Restore blocking mode
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)

        return "\n".join(response_lines)

    def cleanup(self):
        """Clean up the session."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
            print("🧹 Session cleaned up")

def main():
    """Main test function."""
    tester = ClaudeInteractiveTester()

    try:
        # Start session
        if not tester.start_session():
            return 1

        # Test messages
        test_messages = [
            "Hello, can you hear me?",
            "What is 2 + 2?",
            "Generate Python code to print 'Hello World'",
            "Please read the screenshot at /tmp/test.png and describe it"
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"\n{'='*60}")
            print(f"TEST {i}/{len(test_messages)}")
            print(f"{'='*60}")

            response = tester.send_message(message)

            if response is None:
                print("❌ Failed to get response")
                break

            # Wait between messages
            if i < len(test_messages):
                print("\nWaiting 2 seconds before next test...")
                time.sleep(2)

        print(f"\n{'='*60}")
        print("ALL TESTS COMPLETED")
        print(f"{'='*60}")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")

    finally:
        tester.cleanup()

    return 0

if __name__ == "__main__":
    sys.exit(main())