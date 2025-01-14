from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import json

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

if __name__ == '__main__':
    app.run(debug=True)
