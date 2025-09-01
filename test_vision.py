#!/usr/bin/env python3

import argparse
import base64
import json
import math
import os
import random
import requests
import string
from PIL import Image


IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200

VIDEO_MIN_PIXELS = 128 * 28 * 28
VIDEO_MAX_PIXELS = 768 * 28 * 28
FRAME_FACTOR = 2
FPS = 2.0
FPS_MIN_FRAMES = 4
FPS_MAX_FRAMES = 768

def round_by_factor(number: int, factor: int) -> int:
    """Returns the closest integer to 'number' that is divisible by 'factor'."""
    return round(number / factor) * factor

def ceil_by_factor(number: int, factor: int) -> int:
    """Returns the smallest integer greater than or equal to 'number' that is divisible by 'factor'."""
    return math.ceil(number / factor) * factor

def floor_by_factor(number: int, factor: int) -> int:
    """Returns the largest integer less than or equal to 'number' that is divisible by 'factor'."""
    return math.floor(number / factor) * factor

def smart_resize(
    height: int, width: int, factor: int = IMAGE_FACTOR, min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS
) -> tuple[int, int]:
    """
    Rescales the image so that the following conditions are met:

    1. Both dimensions (height and width) are divisible by 'factor'.

    2. The total number of pixels is within the range ['min_pixels', 'max_pixels'].

    3. The aspect ratio of the image is maintained as closely as possible.
    """
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"absolute aspect ratio must be smaller than {MAX_RATIO}, got {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar


def test_vision_model(image_path: str, prompt: str, ollama_url: str = "http://localhost:11434", model: str = "llama3.2-vision:11b"):
    """Test vision model with a given image and prompt."""
    
    try:
        # Load, resize, and encode the image
        print(f"Loading image: {image_path}")
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            print(f"Original image size: {original_width}x{original_height}")
            
            # Calculate optimal resize dimensions
            new_height, new_width = smart_resize(original_height, original_width)
            
            # Ensure long edge is less than 1000px while maintaining factor of 28
            max_dimension = max(new_height, new_width)
            if max_dimension >= 1000:
                # Find the largest multiple of 28 that's less than 1000
                max_allowed = floor_by_factor(999, IMAGE_FACTOR)
                scale_factor = max_allowed / max_dimension
                new_width = round_by_factor(int(new_width * scale_factor), IMAGE_FACTOR)
                new_height = round_by_factor(int(new_height * scale_factor), IMAGE_FACTOR)
            
            print(f"Resizing to: {new_width}x{new_height}")
            
            # Resize the image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save resized image to random path under /tmp
            random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            tmp_path = f"/tmp/resized_{random_name}.png"
            resized_img.save(tmp_path)
            print(f"Resized image saved to: {tmp_path}")
            
            # Convert to bytes and encode
            from io import BytesIO
            img_bytes = BytesIO()
            resized_img.save(img_bytes, format=img.format if img.format else 'PNG')
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        
        print(f"Image resized and encoded (size: {len(img_base64)} chars)")
        print(f"Using Ollama URL: {ollama_url}")
        print(f"Model: {model}")
        print(f"Prompt: {prompt}")
        print("-" * 50)
        
        # Determine API endpoint and payload format based on model
        if "llama3.2-vision" in model:
            # Use chat API for llama3.2-vision
            api_url = f"{ollama_url}/api/chat"
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [img_base64]
                    }
                ],
                "stream": False
            }
        else:
            # Use generate API for other models like qwen2.5vl
            api_url = f"{ollama_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [img_base64],
                "stream": False
            }
        
        print("Sending request to vision model...")
        response = requests.post(api_url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            # Handle different response formats
            if "llama3.2-vision" in model:
                # Chat API returns message in different format
                message = result.get('message', {})
                answer = message.get('content', '').strip()
            else:
                # Generate API format
                answer = result.get('response', '').strip()
            
            print("Vision model response:")
            print("=" * 50)
            print(answer)
            print("=" * 50)
            
            # Return both answer and processed dimensions for coordinate calculation
            return answer, (new_width, new_height)
        else:
            error_msg = f"Ollama API error: {response.status_code} - {response.text}"
            print(f"Error: {error_msg}")
            return None, None
            
    except FileNotFoundError:
        print(f"Error: Image file not found: {image_path}")
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def transform_coordinates(model_coords: tuple, model_width: int, model_height: int, real_width: int, real_height: int) -> tuple:
    """
    Transform coordinates from model output dimensions to real image dimensions.
    
    Args:
        model_coords: (x, y) coordinates from model output
        model_width: Width of the processed image sent to model
        model_height: Height of the processed image sent to model  
        real_width: Width of the original/real image
        real_height: Height of the original/real image
    
    Returns:
        (x, y) coordinates scaled to real image dimensions
    """
    model_x, model_y = model_coords
    real_x = int(model_x * real_width / model_width)
    real_y = int(model_y * real_height / model_height)
    return real_x, real_y


def calculate_real_coordinates(image_path: str, model_bbox: list, processed_size: tuple = None, factor: int = IMAGE_FACTOR) -> tuple:
    """
    Calculate real screen coordinates from model bbox output using UI-TARS approach.
    
    Args:
        image_path: Path to original image
        model_bbox: [x1, y1, x2, y2] bbox from model
        processed_size: Actual processed dimensions (width, height) if known
        factor: Resize factor used by model (default: 28)
    
    Returns:
        Tuple of (real_bbox, original_size, processed_size)
    """
    try:
        # Load original image to get real dimensions
        with Image.open(image_path) as img:
            original_width, original_height = img.size
        
        # Use actual processed size if provided, otherwise calculate
        if processed_size:
            processed_width, processed_height = processed_size
        else:
            processed_height, processed_width = smart_resize(original_height, original_width, factor)
        
        # Transform coordinates from processed size back to original size
        x1, y1, x2, y2 = model_bbox
        
        real_x1, real_y1 = transform_coordinates((x1, y1), processed_width, processed_height, original_width, original_height)
        real_x2, real_y2 = transform_coordinates((x2, y2), processed_width, processed_height, original_width, original_height)
        
        real_bbox = [real_x1, real_y1, real_x2, real_y2]
        
        return real_bbox, (original_width, original_height), (processed_width, processed_height)
        
    except Exception as e:
        print(f"Error calculating real coordinates: {e}")
        return None, None, None


def parse_bbox_output(output: str, image_path: str = None, processed_size: tuple = None):
    """Parse JSON bbox output and print real coordinates."""
    try:
        # Look for JSON content in the output
        json_start = output.find('[')
        json_end = output.rfind(']') + 1
        
        if json_start == -1 or json_end <= json_start:
            print("No JSON bbox data found in output")
            return
        
        json_str = output[json_start:json_end]
        parsed_data = json.loads(json_str)
        
        # Get image dimensions if image path provided
        img_width, img_height = None, None
        if image_path and os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    img_width, img_height = img.size
            except Exception as e:
                print(f"Could not read image dimensions: {e}")
        
        print("\nParsed bbox information:")
        print("=" * 40)
        
        for i, item in enumerate(parsed_data):
            if 'bbox_2d' in item:
                bbox = item['bbox_2d']
                label = item.get('label', 'unknown')
                
                print(f"Object {i+1}: {label}")
                print(f"  Model bbox coordinates: {bbox}")
                print(f"  x1: {bbox[0]}, y1: {bbox[1]}")
                print(f"  x2: {bbox[2]}, y2: {bbox[3]}")
                print(f"  Width: {bbox[2] - bbox[0]}")
                print(f"  Height: {bbox[3] - bbox[1]}")
                
                # Calculate real coordinates using UI-TARS approach
                if image_path:
                    real_bbox, original_size, actual_processed_size = calculate_real_coordinates(image_path, bbox, processed_size)
                    
                    if real_bbox:
                        print(f"  Original image size: {original_size[0]}x{original_size[1]}")
                        print(f"  Processed image size: {actual_processed_size[0]}x{actual_processed_size[1]}")
                        print(f"  REAL coordinates: [{real_bbox[0]}, {real_bbox[1]}, {real_bbox[2]}, {real_bbox[3]}]")
                        print(f"  Real center point: ({(real_bbox[0] + real_bbox[2]) // 2}, {(real_bbox[1] + real_bbox[3]) // 2})")
                
                if img_width and img_height:
                    print(f"  Image dimensions: {img_width}x{img_height}")
                    print(f"  Relative position: ({bbox[0]/img_width:.3f}, {bbox[1]/img_height:.3f}) to ({bbox[2]/img_width:.3f}, {bbox[3]/img_height:.3f})")
                
                print("-" * 30)
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None
    except Exception as e:
        print(f"Error processing bbox output: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test vision model with image and prompt')
    parser.add_argument('image', type=str, help='Path to the image file')
    parser.add_argument('prompt', type=str, help='Prompt to send to the vision model')
    parser.add_argument('--ollama-url', type=str, 
                       default=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                       help='Ollama server URL (default: http://localhost:11434)')
    parser.add_argument('--model', type=str, 
                       default="llama3.2-vision:11b",
                       help='Vision model to use (default: llama3.2-vision:11b)')
    parser.add_argument('--parse-bbox', action='store_true',
                       help='Parse and display bbox coordinates from JSON output')
    
    args = parser.parse_args()
    
    # Test the vision model
    result, processed_size = test_vision_model(args.image, args.prompt, args.ollama_url, args.model)
    
    if result is None:
        exit(1)
    
    # Parse bbox output if requested
    if args.parse_bbox:
        parse_bbox_output(result, args.image, processed_size)

if __name__ == "__main__":
    main()
