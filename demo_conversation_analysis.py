#!/usr/bin/env python3
"""
Demo script for the Conversation Analysis Agent

This script creates sample conversation data and demonstrates how to use
the conversation analysis agent to extract learnings from feedback.
"""

import json
import os
from datetime import datetime
from pathlib import Path


def create_sample_conversation():
    """Create a sample conversation session for demonstration."""
    conversations_dir = Path("conversations")
    conversations_dir.mkdir(exist_ok=True)

    sample_session = {
        "session_id": "demo123",
        "created_at": "2024-01-15T10:30:00",
        "last_activity": "2024-01-15T11:15:00",
        "user_request": "Help me create a Python script to organize my files by date",
        "text_plan": "1. Get all files in directory\n2. Extract creation dates\n3. Create date-based folders\n4. Move files to appropriate folders",
        "python_code": "import os\nimport shutil\nfrom datetime import datetime\n\ndef organize_files():\n    # Implementation here\n    pass",
        "conversation_history": [
            {
                "from": "user",
                "content": "Help me create a Python script to organize my files by date",
                "timestamp": "2024-01-15T10:30:00"
            },
            {
                "from": "system",
                "content": "I'll help you create a script to organize files by date. Here's my plan:\n1. Get all files in directory\n2. Extract creation dates\n3. Create date-based folders\n4. Move files to appropriate folders",
                "timestamp": "2024-01-15T10:31:00"
            },
            {
                "from": "user",
                "content": "text_plan_approved",
                "timestamp": "2024-01-15T10:32:00"
            },
            {
                "from": "system",
                "content": "import os\nimport shutil\nfrom datetime import datetime\n\ndef organize_files():\n    for file in os.listdir('.'):\n        if os.path.isfile(file):\n            date = datetime.fromtimestamp(os.path.getctime(file))\n            folder = date.strftime('%Y-%m')\n            os.makedirs(folder, exist_ok=True)\n            shutil.move(file, os.path.join(folder, file))",
                "timestamp": "2024-01-15T10:35:00"
            },
            {
                "from": "user",
                "content": "This code is too aggressive - it moves ALL files including important system files. Please improve it to be safer and only move specific file types like documents and images.",
                "timestamp": "2024-01-15T10:38:00"
            },
            {
                "from": "system",
                "content": "You're absolutely right! Here's a much safer version that only moves specific file types:\n\nimport os\nimport shutil\nfrom datetime import datetime\n\ndef organize_files(source_dir='.', file_types=None):\n    if file_types is None:\n        file_types = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.txt']\n    \n    for file in os.listdir(source_dir):\n        if os.path.isfile(file) and any(file.lower().endswith(ext) for ext in file_types):\n            date = datetime.fromtimestamp(os.path.getctime(file))\n            folder = date.strftime('%Y-%m')\n            os.makedirs(folder, exist_ok=True)\n            shutil.move(file, os.path.join(folder, file))\n            print(f'Moved {file} to {folder}/')",
                "timestamp": "2024-01-15T10:42:00"
            },
            {
                "from": "user",
                "content": "code_approved",
                "timestamp": "2024-01-15T10:45:00"
            }
        ],
        "metadata": {
            "agent_version": "2.0.0",
            "total_messages": 6,
            "has_text_plan": True,
            "has_code": True,
            "saved_at": datetime.now().isoformat()
        }
    }

    # Save the sample session
    session_file = conversations_dir / "demo123.json"
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(sample_session, f, indent=2, ensure_ascii=False)

    print(f"✅ Created sample conversation session: {session_file}")
    return "demo123"


def create_complex_feedback_conversation():
    """Create a more complex conversation with multiple feedback loops."""
    conversations_dir = Path("conversations")
    conversations_dir.mkdir(exist_ok=True)

    complex_session = {
        "session_id": "complex456",
        "created_at": "2024-01-15T14:00:00",
        "last_activity": "2024-01-15T15:30:00",
        "user_request": "Create a web scraper to collect product prices from e-commerce sites",
        "text_plan": "1. Use requests and BeautifulSoup\n2. Handle multiple sites with different structures\n3. Implement rate limiting and error handling\n4. Save data to CSV format\n5. Add scheduling capabilities",
        "python_code": "import requests\nfrom bs4 import BeautifulSoup\nimport csv\nimport time\n\ndef scrape_prices():\n    # Implementation with proper error handling\n    pass",
        "conversation_history": [
            {
                "from": "user",
                "content": "Create a web scraper to collect product prices from e-commerce sites",
                "timestamp": "2024-01-15T14:00:00"
            },
            {
                "from": "system",
                "content": "I'll create a web scraper for collecting product prices. Here's my plan:\n1. Use requests and BeautifulSoup for parsing\n2. Handle multiple sites\n3. Implement basic error handling\n4. Save to CSV",
                "timestamp": "2024-01-15T14:02:00"
            },
            {
                "from": "user",
                "content": "The plan needs more detail about rate limiting and respecting robots.txt. Also, we should handle different site structures more systematically.",
                "timestamp": "2024-01-15T14:05:00"
            },
            {
                "from": "system",
                "content": "You're right! Here's an improved plan:\n1. Use requests and BeautifulSoup\n2. Implement proper rate limiting (delays between requests)\n3. Check and respect robots.txt files\n4. Create site-specific parsers for different e-commerce structures\n5. Robust error handling with retries\n6. Save data to CSV with timestamps\n7. Add scheduling capabilities for regular monitoring",
                "timestamp": "2024-01-15T14:08:00"
            },
            {
                "from": "user",
                "content": "text_plan_approved",
                "timestamp": "2024-01-15T14:10:00"
            },
            {
                "from": "system",
                "content": "import requests\nfrom bs4 import BeautifulSoup\nimport csv\nimport time\nimport urllib.robotparser\nfrom urllib.parse import urljoin\n\nclass PriceScraper:\n    def __init__(self, delay=1):\n        self.delay = delay\n        self.session = requests.Session()\n    \n    def check_robots_txt(self, url):\n        robots_url = urljoin(url, '/robots.txt')\n        rp = urllib.robotparser.RobotFileParser()\n        rp.set_url(robots_url)\n        rp.read()\n        return rp.can_fetch('*', url)\n    \n    def scrape_price(self, url, price_selector):\n        if not self.check_robots_txt(url):\n            print(f'Robots.txt disallows scraping {url}')\n            return None\n        \n        time.sleep(self.delay)\n        response = self.session.get(url)\n        soup = BeautifulSoup(response.content, 'html.parser')\n        price_element = soup.select_one(price_selector)\n        return price_element.text.strip() if price_element else None",
                "timestamp": "2024-01-15T14:15:00"
            },
            {
                "from": "user",
                "content": "The code looks good but it's missing error handling for network issues and the CSV saving functionality. Also, the price parsing should handle different currency formats.",
                "timestamp": "2024-01-15T14:20:00"
            },
            {
                "from": "system",
                "content": "Excellent feedback! Here's the improved version with comprehensive error handling and CSV functionality:\n\nimport requests\nfrom bs4 import BeautifulSoup\nimport csv\nimport time\nimport urllib.robotparser\nfrom urllib.parse import urljoin\nimport re\nfrom datetime import datetime\n\nclass PriceScraper:\n    def __init__(self, delay=1, max_retries=3):\n        self.delay = delay\n        self.max_retries = max_retries\n        self.session = requests.Session()\n        self.session.headers.update({'User-Agent': 'Price Monitor Bot 1.0'})\n    \n    def check_robots_txt(self, url):\n        try:\n            robots_url = urljoin(url, '/robots.txt')\n            rp = urllib.robotparser.RobotFileParser()\n            rp.set_url(robots_url)\n            rp.read()\n            return rp.can_fetch('*', url)\n        except Exception:\n            return True  # Default to allowing if robots.txt check fails\n    \n    def parse_price(self, price_text):\n        if not price_text:\n            return None\n        # Extract numeric price from various formats\n        price_match = re.search(r'[\\d,]+\\.?\\d*', price_text.replace(',', ''))\n        return float(price_match.group()) if price_match else None\n    \n    def scrape_price(self, url, price_selector, product_name):\n        if not self.check_robots_txt(url):\n            print(f'Robots.txt disallows scraping {url}')\n            return None\n        \n        for attempt in range(self.max_retries):\n            try:\n                time.sleep(self.delay)\n                response = self.session.get(url, timeout=10)\n                response.raise_for_status()\n                \n                soup = BeautifulSoup(response.content, 'html.parser')\n                price_element = soup.select_one(price_selector)\n                \n                if price_element:\n                    price_text = price_element.text.strip()\n                    price = self.parse_price(price_text)\n                    \n                    return {\n                        'product_name': product_name,\n                        'url': url,\n                        'price': price,\n                        'raw_price_text': price_text,\n                        'timestamp': datetime.now().isoformat(),\n                        'status': 'success'\n                    }\n                else:\n                    return {'product_name': product_name, 'url': url, 'status': 'price_not_found'}\n                    \n            except requests.RequestException as e:\n                print(f'Attempt {attempt + 1} failed for {url}: {e}')\n                if attempt == self.max_retries - 1:\n                    return {'product_name': product_name, 'url': url, 'status': f'error: {e}'}\n    \n    def save_to_csv(self, data, filename='prices.csv'):\n        fieldnames = ['product_name', 'url', 'price', 'raw_price_text', 'timestamp', 'status']\n        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:\n            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)\n            writer.writeheader()\n            writer.writerows(data)",
                "timestamp": "2024-01-15T14:28:00"
            },
            {
                "from": "user",
                "content": "Perfect! This is much more robust. The error handling looks comprehensive and the price parsing should handle most formats.",
                "timestamp": "2024-01-15T14:30:00"
            },
            {
                "from": "user",
                "content": "code_approved",
                "timestamp": "2024-01-15T14:31:00"
            }
        ],
        "metadata": {
            "agent_version": "2.0.0",
            "total_messages": 9,
            "has_text_plan": True,
            "has_code": True,
            "saved_at": datetime.now().isoformat()
        }
    }

    # Save the complex session
    session_file = conversations_dir / "complex456.json"
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(complex_session, f, indent=2, ensure_ascii=False)

    print(f"✅ Created complex conversation session: {session_file}")
    return "complex456"


def main():
    """Create sample conversations and demonstrate the analysis agent."""
    print("🚀 Setting up Conversation Analysis Agent Demo")
    print("=" * 50)

    # Create sample conversations
    print("\n📝 Creating sample conversation sessions...")
    simple_session = create_sample_conversation()
    complex_session = create_complex_feedback_conversation()

    print("\n✅ Demo setup complete!")
    print("\n📋 Available demo sessions:")
    print(f"  • {simple_session} - Simple feedback example")
    print(f"  • {complex_session} - Complex feedback loops")

    print("\n🔬 To analyze a session, run:")
    print(f"  python conversation_analysis_agent.py {simple_session}")
    print(f"  python conversation_analysis_agent.py {complex_session}")

    print("\n📖 Or list all sessions:")
    print("  python conversation_analysis_agent.py --list")

    print("\n💡 The analysis agent will:")
    print("  1. Load the conversation data")
    print("  2. Extract feedback patterns")
    print("  3. Generate initial analysis")
    print("  4. Allow you to provide feedback to improve the analysis")
    print("  5. Save the final results")


if __name__ == "__main__":
    main()