#!/usr/bin/env python3

import argparse
from PIL import Image, ImageDraw, ImageFont
import sys
import os


def draw_point(image_path, x, y, output_path=None, color='red', size=5, label=None):
    """
    Draw a point on an image.
    
    Args:
        image_path: Path to the input image
        x, y: Coordinates of the point
        output_path: Path to save the output image (default: adds '_point' to input filename)
        color: Color of the point (default: 'red')
        size: Size of the point (default: 5)
        label: Optional label text to display next to the point
    
    Returns:
        Path to the output image
    """
    try:
        # Load the image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Draw the point as a circle
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=color,
            outline=color
        )
        
        # Add label if provided
        if label:
            try:
                font = ImageFont.load_default()
                text_x = x + size + 5
                text_y = y - 10
                
                # Draw text background for better visibility
                bbox = draw.textbbox((text_x, text_y), label, font=font)
                draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill='white', outline=color)
                draw.text((text_x, text_y), label, fill=color, font=font)
            except Exception as e:
                print(f"Warning: Could not add label: {e}")
        
        # Generate output path if not provided
        if output_path is None:
            base_name, ext = os.path.splitext(image_path)
            output_path = f"{base_name}_point{ext}"
        
        # Save the result
        image.save(output_path)
        print(f"Point drawn and saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"Error drawing point: {e}")
        return None


def draw_bbox(image_path, x1, y1, x2, y2, output_path=None, color='red', thickness=3, label=None):
    """
    Draw a bounding box on an image.
    
    Args:
        image_path: Path to the input image
        x1, y1: Top-left coordinates of the bounding box
        x2, y2: Bottom-right coordinates of the bounding box
        output_path: Path to save the output image (default: adds '_bbox' to input filename)
        color: Color of the bounding box (default: 'red')
        thickness: Thickness of the bounding box lines (default: 3)
        label: Optional label text to display above the bounding box
    
    Returns:
        Path to the output image
    """
    try:
        # Load the image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Ensure coordinates are in correct order
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Draw the bounding box rectangle
        for i in range(thickness):
            draw.rectangle(
                [x1 - i, y1 - i, x2 + i, y2 + i],
                outline=color,
                fill=None
            )
        
        # Add label if provided
        if label:
            try:
                # Try to load a font
                font = ImageFont.load_default()
                # Calculate text position (above the box)
                text_x = x1
                text_y = max(0, y1 - 20)
                
                # Draw text background for better visibility
                bbox = draw.textbbox((text_x, text_y), label, font=font)
                draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill='white', outline=color)
                draw.text((text_x, text_y), label, fill=color, font=font)
            except Exception as e:
                print(f"Warning: Could not add label: {e}")
        
        # Generate output path if not provided
        if output_path is None:
            base_name, ext = os.path.splitext(image_path)
            output_path = f"{base_name}_bbox{ext}"
        
        # Save the result
        image.save(output_path)
        print(f"Bounding box drawn and saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"Error drawing bounding box: {e}")
        return None


def parse_coordinates(coord_str):
    """Parse coordinate string like '(12,34)' or '12,34' into x,y tuple"""
    coord_str = coord_str.strip('()')
    parts = coord_str.split(',')
    if len(parts) != 2:
        raise ValueError(f"Invalid coordinate format: {coord_str}")
    return float(parts[0].strip()), float(parts[1].strip())


def parse_bbox_coordinates(bbox_str):
    """Parse bbox coordinate string like '(12,34,56,78)' or '12,34,56,78' into x1,y1,x2,y2 tuple"""
    bbox_str = bbox_str.strip('()')
    parts = bbox_str.split(',')
    if len(parts) != 4:
        raise ValueError(f"Invalid bbox format: {bbox_str}")
    return float(parts[0].strip()), float(parts[1].strip()), float(parts[2].strip()), float(parts[3].strip())


def main():
    parser = argparse.ArgumentParser(description='Draw points or bounding boxes on an image')
    parser.add_argument('image_path', help='Path to the input image')
    
    # Mutually exclusive group for drawing mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--point', type=str, help='Draw a point at coordinates (x,y)')
    mode_group.add_argument('--bbox', type=str, help='Draw a bounding box with coordinates (x1,y1,x2,y2)')
    
    # For backward compatibility, also accept positional bbox coordinates
    parser.add_argument('x1', nargs='?', type=int, help='X coordinate of top-left corner (legacy mode)')
    parser.add_argument('y1', nargs='?', type=int, help='Y coordinate of top-left corner (legacy mode)')
    parser.add_argument('x2', nargs='?', type=int, help='X coordinate of bottom-right corner (legacy mode)')
    parser.add_argument('y2', nargs='?', type=int, help='Y coordinate of bottom-right corner (legacy mode)')
    
    parser.add_argument('--relative', action='store_true', help='Treat coordinates as relative (0.0-1.0) and convert to absolute')
    parser.add_argument('-o', '--output', help='Output image path (default: adds _bbox or _point to input filename)')
    parser.add_argument('-c', '--color', default='red', help='Color of the drawing (default: red)')
    parser.add_argument('-t', '--thickness', type=int, default=3, help='Thickness of the bounding box lines (default: 3)')
    parser.add_argument('-s', '--size', type=int, default=5, help='Size of the point (default: 5)')
    parser.add_argument('-l', '--label', help='Optional label text to display')
    
    args = parser.parse_args()
    
    # Check if input image exists
    if not os.path.exists(args.image_path):
        print(f"Error: Image file '{args.image_path}' not found")
        sys.exit(1)
    
    # Get image dimensions for relative coordinate conversion
    if args.relative:
        try:
            image = Image.open(args.image_path)
            width, height = image.size
        except Exception as e:
            print(f"Error loading image to get dimensions: {e}")
            sys.exit(1)
    
    result = None
    
    # Handle point drawing
    if args.point:
        try:
            x, y = parse_coordinates(args.point)
            
            if args.relative:
                x = x * width
                y = y * height
            
            result = draw_point(
                args.image_path,
                int(x), int(y),
                args.output, args.color, args.size, args.label
            )
        except ValueError as e:
            print(f"Error parsing point coordinates: {e}")
            sys.exit(1)
    
    # Handle bbox drawing
    elif args.bbox:
        try:
            x1, y1, x2, y2 = parse_bbox_coordinates(args.bbox)
            
            if args.relative:
                x1 = x1 * width
                y1 = y1 * height
                x2 = x2 * width
                y2 = y2 * height
            
            result = draw_bbox(
                args.image_path,
                int(x1), int(y1), int(x2), int(y2),
                args.output, args.color, args.thickness, args.label
            )
        except ValueError as e:
            print(f"Error parsing bbox coordinates: {e}")
            sys.exit(1)
    
    # Legacy mode - positional arguments for bbox
    elif all(arg is not None for arg in [args.x1, args.y1, args.x2, args.y2]):
        x1, y1, x2, y2 = args.x1, args.y1, args.x2, args.y2
        
        if args.relative:
            x1 = x1 * width
            y1 = y1 * height
            x2 = x2 * width
            y2 = y2 * height
        
        result = draw_bbox(
            args.image_path,
            int(x1), int(y1), int(x2), int(y2),
            args.output, args.color, args.thickness, args.label
        )
    else:
        print("Error: You must specify either --point, --bbox, or provide positional bbox coordinates")
        sys.exit(1)
    
    if result:
        print(f"Success! Drawing completed.")
        sys.exit(0)
    else:
        print("Failed to draw on image.")
        sys.exit(1)


if __name__ == "__main__":
    main()