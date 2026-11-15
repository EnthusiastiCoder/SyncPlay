"""Generate a simple placeholder icon for SyncPlay."""
from PIL import Image, ImageDraw

def create_syncplay_icon():
    """Create a simple circular icon with gradient."""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a circular gradient background
    center = size // 2
    radius = size // 2 - 10
    
    # Outer circle (dark blue)
    draw.ellipse([10, 10, size-10, size-10], fill=(30, 144, 255, 255))
    
    # Inner circle (lighter blue)
    inner_offset = 30
    draw.ellipse([inner_offset, inner_offset, size-inner_offset, size-inner_offset], 
                 fill=(100, 180, 255, 255))
    
    # Center circle (white)
    center_offset = 80
    draw.ellipse([center_offset, center_offset, size-center_offset, size-center_offset], 
                 fill=(255, 255, 255, 255))
    
    # Save as .ico with multiple sizes
    img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Created icon.ico")

if __name__ == "__main__":
    create_syncplay_icon()
