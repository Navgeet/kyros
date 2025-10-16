#!/usr/bin/env python3
"""
Test script to get XPath of element under mouse cursor
This is useful for testing xpath-based interactions in the browser action agent

Usage:
1. Run this script
2. Position your mouse over the element you want to identify
3. Wait for the countdown (5 seconds by default)
4. The script will capture the element under the cursor and print its XPath

You can also use this to test clicking elements by xpath.
"""

import sys
import time
import asyncio
from playwright.async_api import async_playwright
import pyautogui

# Disable PyAutoGUI's failsafe
pyautogui.FAILSAFE = False


async def get_xpath_at_position(page, x, y):
    """Get the XPath of the element at the given screen coordinates"""
    # JavaScript to find element at coordinates and generate XPath
    js_code = """
    (coords) => {
        const element = document.elementFromPoint(coords.x, coords.y);
        if (!element) return null;

        // Function to generate XPath for an element
        function getXPath(element) {
            if (element.id !== '') {
                return '//*[@id="' + element.id + '"]';
            }
            if (element === document.body) {
                return '/html/body';
            }

            let ix = 0;
            const siblings = element.parentNode.childNodes;
            for (let i = 0; i < siblings.length; i++) {
                const sibling = siblings[i];
                if (sibling === element) {
                    const parentPath = getXPath(element.parentNode);
                    const tagName = element.tagName.toLowerCase();
                    return parentPath + '/' + tagName + '[' + (ix + 1) + ']';
                }
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                    ix++;
                }
            }
        }

        return {
            xpath: getXPath(element),
            tag: element.tagName.toLowerCase(),
            id: element.id || null,
            class: element.className || null,
            text: element.textContent ? element.textContent.trim().substring(0, 100) : null,
            value: element.value || null,
            type: element.type || null,
            name: element.name || null,
            href: element.href || null
        };
    }
    """

    # Get viewport offset (in case browser is not at 0,0)
    viewport_info = await page.evaluate("""
        () => {
            const rect = document.body.getBoundingClientRect();
            return {
                scrollX: window.scrollX,
                scrollY: window.scrollY
            };
        }
    """)

    # Adjust coordinates relative to the page content
    # This is a simplified version - in reality you'd need to account for browser chrome
    page_x = x
    page_y = y - 100  # Rough estimate for browser toolbar height

    result = await page.evaluate(js_code, {"x": page_x, "y": page_y})
    return result


async def test_xpath_from_cursor(url=None, countdown=5, click_test=False):
    """
    Main test function

    Args:
        url: URL to open (if None, uses current active page)
        countdown: Seconds to wait before capturing element
        click_test: If True, will also test clicking the element
    """
    async with async_playwright() as p:
        # Launch browser
        print("Launching browser...")
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

        # Navigate to URL if provided
        if url:
            print(f"Navigating to {url}...")
            await page.goto(url)
            await asyncio.sleep(2)  # Wait for page to load
        else:
            print("No URL provided. Browser opened - manually navigate to your desired page.")
            print("Waiting 10 seconds for you to navigate...")
            await asyncio.sleep(10)

        # Countdown
        print(f"\nPosition your mouse over the element you want to identify...")
        for i in range(countdown, 0, -1):
            print(f"Capturing in {i}...", end='\r')
            await asyncio.sleep(1)
        print("\nCapturing element!              ")

        # Get mouse position
        mouse_x, mouse_y = pyautogui.position()
        print(f"\nMouse position: ({mouse_x}, {mouse_y})")

        # Get element info
        element_info = await get_xpath_at_position(page, mouse_x, mouse_y)

        if element_info:
            print("\n" + "="*60)
            print("ELEMENT INFORMATION")
            print("="*60)
            print(f"XPath:  {element_info['xpath']}")
            print(f"Tag:    {element_info['tag']}")
            if element_info['id']:
                print(f"ID:     {element_info['id']}")
            if element_info['class']:
                print(f"Class:  {element_info['class']}")
            if element_info['name']:
                print(f"Name:   {element_info['name']}")
            if element_info['type']:
                print(f"Type:   {element_info['type']}")
            if element_info['href']:
                print(f"Href:   {element_info['href']}")
            if element_info['text']:
                print(f"Text:   {element_info['text']}")
            if element_info['value']:
                print(f"Value:  {element_info['value']}")
            print("="*60)

            # Test clicking if requested
            if click_test:
                print("\nTesting click on this element...")
                xpath = element_info['xpath']
                try:
                    element = await page.query_selector(f"xpath={xpath}")
                    if element:
                        await element.click()
                        print("✓ Click successful!")
                        await asyncio.sleep(2)
                    else:
                        print("✗ Element not found by XPath")
                except Exception as e:
                    print(f"✗ Click failed: {e}")
        else:
            print("✗ No element found at cursor position")

        # Keep browser open for a bit
        print("\nBrowser will close in 5 seconds...")
        await asyncio.sleep(5)

        await browser.close()


def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Get XPath of element under mouse cursor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Open Google and identify element after 5 second countdown
  python test_xpath.py --url https://www.google.com

  # Use shorter countdown
  python test_xpath.py --url https://www.google.com --countdown 3

  # Test clicking the element
  python test_xpath.py --url https://www.google.com --click

  # Open browser and manually navigate
  python test_xpath.py
        """
    )

    parser.add_argument(
        '--url',
        type=str,
        help='URL to open in browser (if not provided, you must manually navigate)'
    )

    parser.add_argument(
        '--countdown',
        type=int,
        default=5,
        help='Countdown in seconds before capturing element (default: 5)'
    )

    parser.add_argument(
        '--click',
        action='store_true',
        help='Test clicking the element after identifying it'
    )

    args = parser.parse_args()

    try:
        asyncio.run(test_xpath_from_cursor(
            url=args.url,
            countdown=args.countdown,
            click_test=args.click
        ))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
