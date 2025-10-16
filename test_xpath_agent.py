#!/usr/bin/env python3
"""
Test script for XPathAgent

This script tests the xpath agent's ability to find and validate XPath expressions
for elements at given coordinates. You can test it by positioning the mouse over
an element and running the script.

Usage:
    # Test with mouse at current position
    python test_xpath_agent.py

    # Test with specific coordinates
    python test_xpath_agent.py --x 500 --y 300

    # Test with countdown to position mouse
    python test_xpath_agent.py --countdown 5

    # Test on a specific URL
    python test_xpath_agent.py --url https://www.google.com --countdown 5
"""

import asyncio
import pyautogui
import argparse
from playwright.async_api import async_playwright
from agents.xpath_agent import XPathAgent
import config

# Disable PyAutoGUI's failsafe
pyautogui.FAILSAFE = False


async def test_xpath_agent_with_coords(url=None, countdown=0, max_iterations=10):
    """
    Test the XPathAgent at current mouse position

    Args:
        url: URL to open (optional)
        countdown: Seconds to wait before capturing element
        max_iterations: Maximum number of iterations for the agent
    """
    # Load config
    config_dict = config.load_config()

    # Create xpath agent
    agent = XPathAgent(config_dict=config_dict)

    # Launch browser
    print("Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions'
            ]
        )

        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        # Set the page for the agent
        agent.set_page(page)

        # Navigate to URL if provided
        if url:
            print(f"Navigating to {url}...")
            await page.goto(url)
            await asyncio.sleep(2)  # Wait for page to load
        else:
            print("No URL provided. Opening blank page.")
            print("You can manually navigate to your desired page.")
            await asyncio.sleep(3)

        # Countdown if requested
        if countdown > 0:
            print(f"\nPosition your mouse over the element you want to get XPath for...")
            print("The agent will simulate a click to identify the element.")
            for i in range(countdown, 0, -1):
                print(f"Clicking in {i}...", end='\r')
                await asyncio.sleep(1)
            print("\nCapturing!              ")

        # Create message for xpath agent
        message = {
            "max_iterations": max_iterations
        }

        print("\n" + "=" * 80)
        print("Starting XPathAgent...")
        print("=" * 80)

        # Process message (call async method directly since we're in async context)
        result = await agent._process_message_async(message)

        print("\n" + "=" * 80)
        print("XPathAgent Test Complete!")
        print("=" * 80)
        print(f"\nSuccess: {result.get('success')}")
        print(f"Iterations: {result.get('iterations')}")

        if result.get('error'):
            print(f"Error: {result.get('error')}")

        if result.get('xpath'):
            print(f"\n{'='*80}")
            print(f"FINAL XPATH:")
            print(f"{'='*80}")
            print(f"{result.get('xpath')}")
            print(f"{'='*80}")

        print("\n\nHistory:")
        for i, item in enumerate(result.get('history', []), 1):
            print(f"\n{i}. Thought: {item.get('thought')}")
            print(f"   Action: {item.get('action')}")

            exec_result = item.get('result', {})
            if exec_result.get('xpath'):
                print(f"   XPath: {exec_result.get('xpath')}")
                print(f"   Element: {exec_result.get('element')}")
            else:
                print(f"   Result: {exec_result}")

            if item.get('verification'):
                print(f"   Verification: {item.get('verification')}")

        # Keep browser open for a bit to see the highlight
        print("\n\nBrowser will close in 10 seconds (you can see the highlighted element)...")
        await asyncio.sleep(10)

        await browser.close()


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Test XPathAgent to find XPath of element at coordinates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default 5 second countdown
  python test_xpath_agent.py

  # Test on Google with countdown
  python test_xpath_agent.py --url https://www.google.com --countdown 5

  # Test with shorter countdown
  python test_xpath_agent.py --url https://www.google.com --countdown 3
        """
    )

    parser.add_argument(
        '--url',
        type=str,
        help='URL to open in browser (optional)'
    )

    parser.add_argument(
        '--countdown',
        type=int,
        default=5,
        help='Countdown in seconds before capturing element (default: 5)'
    )

    parser.add_argument(
        '--max-iterations',
        type=int,
        default=10,
        help='Maximum iterations for the agent (default: 10)'
    )

    args = parser.parse_args()

    try:
        asyncio.run(test_xpath_agent_with_coords(
            url=args.url,
            countdown=args.countdown,
            max_iterations=args.max_iterations
        ))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
