from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import os
import json
from PIL import Image
import io
import uuid

app = Flask(__name__, template_folder='templates')  # Specify the folder containing HTML templates
JSON_FILE_PATH = 'images/coins.json'

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

# Load JSON data
def load_json():
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, 'r') as file:
            return json.load(file)
    return []

# Save JSON data
def save_json(data):
    with open(JSON_FILE_PATH, 'w') as file:
        json.dump(data, file, indent=2)

@app.route('/edit_json')
def index():
    # Render the HTML template
    return render_template('editjson_python.html')

@app.route('/get-json', methods=['GET'])
def get_json():
    return jsonify(load_json())

# Save updates to the JSON file
@app.route('/update-json', methods=['POST'])
def update_json():
    try:
        updated_data = request.json
        with open(JSON_FILE_PATH, 'w') as json_file:
            json.dump(updated_data, json_file, indent=2)
        return jsonify({"message": "JSON updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/merge-images', methods=['GET', 'POST'])
def merge_images():
    if request.method == 'GET':
        return render_template('merge_images.html')

    try:
        # Get uploaded files
        image1_file = request.files.get('image1')
        image2_file = request.files.get('image2')
        merge_type = request.form.get('mergeType', 'vertical')
        filename = request.form.get('filename', str(uuid.uuid4()))

        if not image1_file or not image2_file:
            return jsonify({'error': 'Both images are required.'}), 400

        # Open and convert images
        image1 = Image.open(image1_file).convert("RGBA")
        image2 = Image.open(image2_file).convert("RGBA")

        # Resize images for seamless merging
        if merge_type == 'vertical':
            new_width = max(image1.width, image2.width)
            image1 = image1.resize((new_width, int(image1.height * (new_width / image1.width))), Image.ANTIALIAS)
            image2 = image2.resize((new_width, int(image2.height * (new_width / image2.width))), Image.ANTIALIAS)
            new_height = image1.height + image2.height
            merged_image = Image.new('RGBA', (new_width, new_height))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (0, image1.height))
        elif merge_type == 'horizontal':
            new_height = max(image1.height, image2.height)
            image1 = image1.resize((int(image1.width * (new_height / image1.height)), new_height), Image.ANTIALIAS)
            image2 = image2.resize((int(image2.width * (new_height / image2.height)), new_height), Image.ANTIALIAS)
            new_width = image1.width + image2.width
            merged_image = Image.new('RGBA', (new_width, new_height))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (image1.width, 0))
        else:
            return jsonify({'error': 'Invalid merge type.'}), 400

        # Save merged image to a bytes buffer
        buffer = io.BytesIO()
        merged_image.save(buffer, format="PNG")
        buffer.seek(0)

        return send_file(buffer, mimetype='image/png')

    except Exception as e:
        return jsonify({'error': f'An error occurred during processing: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)
