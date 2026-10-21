import os
from PIL import Image

def generate_icons():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base_dir, "static", "images")
    
    # Preferred logo: logo_light.png (cream text on transparent background)
    src_logo_path = os.path.join(img_dir, "logo_light.png")
    if not os.path.exists(src_logo_path):
        src_logo_path = os.path.join(img_dir, "logo_transparent.png")
        
    logo = Image.open(src_logo_path).convert("RGBA")
    
    # Background color: Nabt Luxury Botanical Olive (#23261f -> RGB: 35, 38, 31)
    bg_color = (35, 38, 31, 255)
    
    # Target sizes:
    # 1. apple-touch-icon.png (180x180) - Standard iOS Home Screen
    # 2. apple-touch-icon-152x152.png (152x152) - iPad Home Screen
    # 3. apple-touch-icon-167x167.png (167x167) - iPad Pro
    # 4. icon-192.png (192x192) - Android PWA
    # 5. icon-512.png (512x512) - High-res PWA Splash & App Stores
    sizes = [
        (180, "apple-touch-icon.png"),
        (180, "apple-touch-icon-180x180.png"),
        (152, "apple-touch-icon-152x152.png"),
        (167, "apple-touch-icon-167x167.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png")
    ]
    
    for size, filename in sizes:
        # Create solid square background (no rounded corners - iOS/Android mask automatically)
        canvas = Image.new("RGBA", (size, size), bg_color)
        
        # Calculate fitted logo size with safe margin (70% of canvas width/height)
        max_logo_w = int(size * 0.72)
        max_logo_h = int(size * 0.72)
        
        logo_w, logo_h = logo.size
        ratio = min(max_logo_w / logo_w, max_logo_h / logo_h)
        new_w = max(1, int(logo_w * ratio))
        new_h = max(1, int(logo_h * ratio))
        
        resized_logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center the logo on the canvas
        offset_x = (size - new_w) // 2
        offset_y = (size - new_h) // 2
        
        canvas.paste(resized_logo, (offset_x, offset_y), resized_logo)
        
        # Convert to RGB (iOS Apple Touch icon requires RGB with no alpha channel for reliable rendering)
        final_icon = canvas.convert("RGB")
        target_path = os.path.join(img_dir, filename)
        final_icon.save(target_path, "PNG", quality=95, optimize=True)
        print(f"Generated {filename} ({size}x{size})")

if __name__ == "__main__":
    generate_icons()
