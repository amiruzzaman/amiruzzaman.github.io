from flask import Flask, render_template, request, jsonify
import os
from PIL import Image

app = Flask(__name__)

# Store image paths with their original names
images = {"A": None, "B": None}

@app.route('/replace_images')
def replace_images():
    return render_template('replace_images.html')

@app.route('/upload_replace', methods=['POST'])
def upload_replace():
    global images
    file = request.files['file']
    slot = request.form['slot']  # Either "A" or "B"

    if file and slot in images:
        # Use original file name and save in the current working directory
        filename = file.filename
        filepath = os.path.join(os.getcwd(), filename)  # Save in current location
        file.save(filepath)
        images[slot] = filepath
        return jsonify({"status": "success", "filepath": filepath})

    return jsonify({"status": "error", "message": "Invalid file or slot"}), 400

@app.route('/replace', methods=['POST'])
def replace_image():
    global images
    data = request.get_json()

    if not data or "target" not in data:
        return jsonify({"status": "error", "message": "Missing target"}), 400

    target = data["target"]  # "A" or "B"
    source = "B" if target == "A" else "A"

    if target not in images or source not in images:
        return jsonify({"status": "error", "message": "Invalid target or source"}), 400

    target_path = images.get(target)
    source_path = images.get(source)

    if not target_path or not source_path:
        return jsonify({"status": "error", "message": "Image paths not found"}), 400

    if not os.path.exists(source_path):
        return jsonify({"status": "error", "message": f"Source image not found at {source_path}"}), 400

    try:
        # Open the source image
        with Image.open(source_path) as img_source:
            # Convert RGBA to RGB if needed
            if img_source.mode == "RGBA":
                img_source = img_source.convert("RGB")

            # Save the source image over the target (overwrite the actual file)
            img_source.save(target_path, format="JPEG")  

        return jsonify({"status": "success", "updated": target_path})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
