from PIL import Image
import os

def convert_to_ico(png_path, ico_path):
    img = Image.open(png_path)
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, sizes=icon_sizes)
    print(f"Converted {png_path} to {ico_path}")

if __name__ == "__main__":
    base_path = r"c:\Users\prata\.gemini\antigravity\scratch\meeting-prompter-premium"
    png_path = os.path.join(base_path, "assets", "icon.png")
    ico_path = os.path.join(base_path, "assets", "nebula.ico")
    convert_to_ico(png_path, ico_path)
