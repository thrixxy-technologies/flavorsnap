#!/usr/bin/env python3
"""
Generate placeholder icons for FlavorSnap PWA
Creates simple SVG-based icons with a food theme
"""

import os
from PIL import Image, ImageDraw, ImageFont
import io

def create_icon(size, output_path):
    """Create a simple icon with the given size"""
    # Create a new image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background circle with gradient effect
    margin = size // 10
    draw.ellipse([margin, margin, size - margin, size - margin], 
                fill=(33, 150, 243, 255), outline=(255, 255, 255, 200), width=max(2, size // 50))
    
    # Simple food icon (fork and knife)
    center_x, center_y = size // 2, size // 2
    
    # Fork
    fork_width = size // 8
    fork_height = size // 2
    fork_x = center_x - fork_width
    fork_y = center_y - fork_height // 2
    
    # Fork handle
    draw.rectangle([fork_x - fork_width//4, fork_y + fork_height//2, 
                   fork_x + fork_width//4, center_y + fork_height//4], 
                  fill=(255, 255, 255, 255))
    
    # Fork prongs
    prong_width = fork_width // 3
    for i in range(3):
        x_offset = (i - 1) * prong_width
        draw.rectangle([fork_x + x_offset, fork_y, 
                       fork_x + x_offset + prong_width//2, fork_y + fork_height//3], 
                      fill=(255, 255, 255, 255))
    
    # Knife
    knife_width = size // 8
    knife_height = size // 2
    knife_x = center_x + knife_width // 2
    knife_y = center_y - knife_height // 2
    
    # Knife blade
    draw.polygon([knife_x, knife_y, 
                  knife_x + knife_width//2, knife_y + knife_height//3,
                  knife_x + knife_width//2, knife_y + knife_height//2 - knife_height//8,
                  knife_x, knife_y + knife_height//2], 
                 fill=(255, 255, 255, 255))
    
    # Knife handle
    draw.rectangle([knife_x - knife_width//4, knife_y + knife_height//2, 
                   knife_x + knife_width//4, center_y + knife_height//4], 
                  fill=(255, 255, 255, 255))
    
    # Add "FS" text for FlavorSnap
    try:
        font_size = max(8, size // 6)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "FS"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = center_x - text_width // 2
    text_y = center_y + size // 4
    
    # Add text background for better visibility
    padding = 2
    draw.rectangle([text_x - padding, text_y - padding, 
                   text_x + text_width + padding, text_y + text_height + padding], 
                  fill=(33, 150, 243, 200))
    
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save the image
    img.save(output_path, 'PNG')
    print(f"Created icon: {output_path}")

def main():
    """Generate all required icon sizes"""
    icons_dir = "static/icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    # Required icon sizes for PWA
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    for size in sizes:
        output_path = os.path.join(icons_dir, f"icon-{size}x{size}.png")
        create_icon(size, output_path)
    
    print(f"\nGenerated {len(sizes)} icons in {icons_dir}/")
    
    # Also create a favicon
    favicon_path = os.path.join("static", "favicon.ico")
    create_icon(32, favicon_path)
    print(f"Created favicon: {favicon_path}")

if __name__ == "__main__":
    main()
