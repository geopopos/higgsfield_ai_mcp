import os
import sys
from PIL import Image, ImageDraw, ImageFont

def draw_cyberpunk_character():
    os.makedirs("assets/characters", exist_ok=True)
    os.makedirs("assets/locations", exist_ok=True)
    
    # 1. Main Character Sheet
    img = Image.new("RGB", (1920, 1080), color=(15, 18, 25))
    draw = ImageDraw.Draw(img)
    
    # Draw Title & Grid Frame
    draw.rectangle([30, 30, 1890, 1050], outline=(255, 40, 80), width=4)
    draw.text((60, 60), "KAI ONYX - CHARACTER TURNAROUND REF SHEET [紫禁夜行]", fill=(255, 255, 255))
    
    # 4 View Panels (Front, 3/4, Side, Back)
    panel_titles = ["1. FRONT VIEW", "2. 3/4 ANGLE VIEW", "3. SIDE PROFILE", "4. BACK VIEW"]
    for i in range(4):
        x1 = 70 + i * 450
        y1 = 140
        x2 = x1 + 420
        y2 = 980
        draw.rectangle([x1, y1, x2, y2], outline=(0, 220, 255), width=2)
        draw.text((x1 + 20, y1 + 20), panel_titles[i], fill=(0, 220, 255))
        
        # Silhouette Proxy Body
        cx = (x1 + x2) // 2
        draw.ellipse([cx - 40, y1 + 100, cx + 40, y1 + 180], fill=(40, 50, 70)) # Head
        draw.polygon([(cx - 80, y1 + 200), (cx + 80, y1 + 200), (cx + 60, y2 - 200), (cx - 60, y2 - 200)], fill=(30, 40, 60)) # Techwear Hoodie Body
        
        # Key Accents
        draw.rectangle([cx - 15, y1 + 210, cx + 15, y1 + 240], fill=(0, 255, 180)) # Jade Pendant (冷冰冰的玉)
        draw.line([(cx + 40, y1 + 220), (cx + 70, y1 + 450)], fill=(255, 50, 80), width=8) # Cybernetic Arm Brace (Cyber Arm)

    char_path = "assets/characters/character_main_sheet.png"
    img.save(char_path)
    print(f"[SUCCESS] Character Ref Sheet generated: {char_path}")

    # 2. Location Ref Keyframes
    for loc_idx in range(1, 5):
        loc_img = Image.new("RGB", (1280, 720), color=(10, 12, 18))
        l_draw = ImageDraw.Draw(loc_img)
        l_draw.rectangle([20, 20, 1260, 700], outline=(255, 180, 0), width=3)
        l_draw.text((40, 40), f"LOCATION KEYFRAME #{loc_idx} [Chinese Cyberpunk Forbidden Palace]", fill=(255, 255, 255))
        loc_path = f"assets/locations/location_sec_{loc_idx}.png"
        loc_img.save(loc_path)
        print(f"[SUCCESS] Location Ref Keyframe generated: {loc_path}")

if __name__ == "__main__":
    draw_cyberpunk_character()
