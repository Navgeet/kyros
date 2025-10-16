#!/usr/bin/env python3
"""
Test script for XPathAgent (new simplified version)

This script tests the xpath agent's ability to generate XPath expressions from HTML source
and a query, then verify using screenshots.

Usage:
    # Test with a query on a URL
    python test_xpath_agent.py --url https://www.google.com --query "find xpath for search button"

    # Test with shorter countdown
    python test_xpath_agent.py --url https://www.google.com --query "find xpath for search input" --countdown 3
"""

import asyncio
import argparse
from playwright.async_api import async_playwright
from agents.xpath_agent import XPathAgent
import config


async def test_xpath_agent(url=None, query=None, max_iterations=3):
    """
    Test the XPathAgent with a query

    Args:
        url: URL to open (optional)
        query: Query describing which element to find (e.g., "find xpath for submit button")
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
            await asyncio.sleep(3)

        # Create message for xpath agent
        message = {
            "query": query,
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

            element_info = result.get('element_info', {})
            if element_info:
                print(f"\nElement Info:")
                print(f"  Tag: {element_info.get('tagName')}")
                print(f"  ID: {element_info.get('id', 'N/A')}")
                print(f"  Class: {element_info.get('className', 'N/A')}")
                print(f"  Text: {element_info.get('text', 'N/A')}")

        print("\n\nHistory:")
        for i, item in enumerate(result.get('history', []), 1):
            print(f"\n{i}. Iteration {item.get('iteration')}")
            print(f"   XPath: {item.get('xpath')}")
            print(f"   Thought: {item.get('thought')}")
            print(f"   Confidence: {item.get('confidence')}")

            if item.get('highlight_success'):
                element = item.get('element_info', {})
                print(f"   Element: {element.get('tagName')} (matches: {item.get('count')})")

                verification = item.get('verification', {})
                if verification:
                    correct = verification.get('correct', False)
                    print(f"   Verification: {'✓ Correct' if correct else '✗ Incorrect'}")
                    print(f"   Verification thought: {verification.get('thought')}")
                    if not correct:
                        print(f"   Feedback: {verification.get('feedback')}")
            else:
                print(f"   Error: {item.get('error')}")

        # Keep browser open for a bit to see the highlight
        print("\n\nBrowser will close in 10 seconds (you can see the highlighted element)...")
        await asyncio.sleep(10)

        await browser.close()


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Test XPathAgent to generate XPath from query",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find search button on Google
  python test_xpath_agent.py --url https://www.google.com --query "find xpath for search button"

  # Find search input field
  python test_xpath_agent.py --url https://www.google.com --query "find xpath for search input field"

  # Find submit button on a calculator
  python test_xpath_agent.py --url https://testsheepnz.github.io/BasicCalculator.html --query "find xpath for Add button"
        """
    )

    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='URL to open in browser'
    )

    parser.add_argument(
        '--query',
        type=str,
        required=True,
        help='Query describing which element to find (e.g., "find xpath for submit button")'
    )

    parser.add_argument(
        '--max-iterations',
        type=int,
        default=3,
        help='Maximum iterations for the agent (default: 3)'
    )

    args = parser.parse_args()

    try:
        asyncio.run(test_xpath_agent(
            url=args.url,
            query=args.query,
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
