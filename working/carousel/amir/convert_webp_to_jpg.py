from PIL import Image

def convert_webp_to_jpg(webp_file):
    """Converts a WebP image to JPG with the same name."""

    img = Image.open(webp_file).convert("RGB")
    jpg_file = webp_file.replace(".webp", ".jpg")
    img.save(jpg_file, "JPEG")

if __name__ == "__main__":
    webp_file = "images/Nepal/5b2d8a03-c1d4-49a0-83a4-cf1ad771a729.webp"  # Replace with your actual WebP file name
    convert_webp_to_jpg(webp_file)