import os
from PIL import Image

def convert_webp_to_jpg(webp_file):
    """Converts a WebP image to JPG with the same name."""
    img = Image.open(webp_file).convert("RGB")
    jpg_file = webp_file.replace(".webp", ".jpg")
    img.save(jpg_file, "JPEG")

def convert_all_webp_in_directory(directory):
    """Converts all WebP files in a given directory to JPG."""
    for filename in os.listdir(directory):
        if filename.endswith(".webp"):
            webp_file = os.path.join(directory, filename)
            convert_webp_to_jpg(webp_file)
            print(f"Converted {filename} to JPG.")

def delete_all_webp_in_directory(directory):
    """Deletes all WebP files in a given directory."""
    for filename in os.listdir(directory):
        if filename.endswith(".webp"):
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
            print(f"Deleted {filename}.")
if __name__ == "__main__":
    directory = "images/Vietnam"  # Replace with your actual directory path
    convert_all_webp_in_directory(directory)
    delete_all_webp_in_directory(directory)
