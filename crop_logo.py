from PIL import Image, ImageOps
import os

path = r"c:\Users\prata\.gemini\antigravity\scratch\meeting-prompter-premium\assets\logo_header.png"

try:
    img = Image.open(path).convert("RGBA")
    # Get bounding box of non-zero alpha pixels
    bbox = img.getbbox()
    if bbox:
        cropped = img.crop(bbox)
        cropped.save(path)
        print(f"Cropped logo to {cropped.size}")
    else:
        print("Image is empty/transparent")
except Exception as e:
    print(f"Error: {e}")
