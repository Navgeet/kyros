#!/usr/bin/env python3

import argparse
from tools import Tools

def test_internlm_api():
    """Test the InternLM API implementation"""
    
    parser = argparse.ArgumentParser(description='Test InternLM vision API')
    parser.add_argument('--api-url', type=str, default='http://localhost:23333',
                       help='InternLM API server URL (default: http://localhost:23333)')
    parser.add_argument('--api-key', type=str, 
                       help='API key for InternLM (optional)')
    parser.add_argument('--model', type=str, default='internlm-chat',
                       help='Model name to use (default: internlm-chat)')
    parser.add_argument('--image', type=str,
                       help='Path to image file (optional, uses screenshot if not provided)')
    parser.add_argument('--query', type=str, 
                       default='Describe what you see in this image',
                       help='Query to send to vision model')
    
    args = parser.parse_args()
    
    print("Testing InternLM Vision API...")
    print(f"API URL: {args.api_url}")
    print(f"Model: {args.model}")
    print(f"Query: {args.query}")
    if args.image:
        print(f"Image: {args.image}")
    else:
        print("Using screenshot")
    print("-" * 50)
    
    try:
        # Test the InternLM API
        result = Tools.query_vision_model(
            query=args.query,
            image_path=args.image,
            api_type="internlm",
            api_url=args.api_url,
            api_key=args.api_key,
            model=args.model
        )
        
        print("Response received:")
        print("=" * 50)
        print(result)
        print("=" * 50)
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_internlm_api()
    exit(0 if success else 1)