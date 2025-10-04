import os
import uuid
import json
import requests
import logging
import io
from threading import Lock
from PIL import Image
from flask import Flask, flash, request, redirect, render_template, url_for, session, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Add these imports at the top of editjson.py
import base64
from PIL import Image, ImageOps

app = Flask(__name__, static_url_path='/static')
CORS(app)

# App configuration
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = "upload"

# Paths and file setup
file_name = './images/coins.json'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Update this line to include more image formats
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

BASE_UPLOAD_FOLDER = './images'
JSON_FILE_PATH = os.path.join(BASE_UPLOAD_FOLDER, 'coins.json')
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

# Ensure the JSON file exists
if not os.path.exists(JSON_FILE_PATH):
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump([], f)

# Default JSON file path
DEFAULT_JSON_FILE_PATH = 'images/coins.json'
current_json_file_path = DEFAULT_JSON_FILE_PATH
file_lock = Lock()  # Lock for thread-safe file operations

# Define the folder to store cropped images
IMAGE_FOLDER = os.path.join(os.getcwd(), 'crop')
os.makedirs(IMAGE_FOLDER, exist_ok=True)  # Ensure the folder exists

# Allowed file extensions for uploaded images
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Load countries data
COUNTRIES_FILE_PATH = './countries.json'
def load_countries():
    if os.path.exists(COUNTRIES_FILE_PATH):
        with open(COUNTRIES_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Helper functions
def save_file(file, country):
    """
    Save the file with a random UUID and structured path.
    """
    file_ext = file.filename.rsplit('.', 1)[-1]  # Get the file extension
    file_uuid = str(uuid.uuid4())  # Generate a random UUID
    country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)

    # Ensure the country folder exists
    os.makedirs(country_folder, exist_ok=True)

    file_path = os.path.join(country_folder, f"{file_uuid}.{file_ext}")
    file.save(file_path)
    return file_path, f"{file_uuid}.{file_ext}"

def download_file_from_url(url, country):
    """
    Download the file from the given URL and save it.
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Extract file extension and sanitize file name
    file_name = os.path.basename(url.split('?')[0])  # Remove query parameters
    file_ext = file_name.split('.')[-1] if '.' in file_name else 'jpg'  # Default to .jpg if no extension
    file_uuid = str(uuid.uuid4())  # Generate a random UUID
    country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)

    # Ensure the country folder exists
    os.makedirs(country_folder, exist_ok=True)

    file_path = os.path.join(country_folder, f"{file_uuid}.{file_ext}")
    with open(file_path, 'wb') as f:
        f.write(response.content)
    return file_path, f"{file_uuid}.{file_ext}"

def update_json_file(country, image, note, donor_name, currency_type, size, year, hidden_note=""):
    """
    Update the coins.json file with the new entry.
    """
    with open(JSON_FILE_PATH, 'r') as f:
        data = json.load(f)

    # Create the new entry
    new_entry = {
        "country": country,
        "image": image,
        "note": note,
        "donor_name": donor_name,
        "currency_type": currency_type,
        "size": size,
        "year": year
    }
    
    # Add hidden_note if provided
    if hidden_note:
        new_entry["hidden_note"] = hidden_note

    # Add the new entry
    data.append(new_entry)

    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_json_file():
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file) if os.stat(file_name).st_size > 0 else []

def write_json_file(data):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

def add_to_json(country, image, note, donor_name, currency_type, size, year):
    data = read_json_file()
    data.append({
        'country': country.title(),
        'image': image,
        'note': note,
        'donor_name': donor_name,
        'currency_type': currency_type,
        'size': size,
        'year': year
    })
    write_json_file(data)

def edit_or_delete_entry(action, value):
    data = read_json_file()
    updated_data = []
    for entry in data:
        if action == 'delete' and entry["image"] == value:
            continue
        if action == 'edit':
            # Implement edit logic as needed
            pass
        updated_data.append(entry)
    write_json_file(updated_data)

def update_entry(updated_entry):
    data = read_json_file()
    for entry in data:
        if entry['image'] == updated_entry['row_id']:
            entry.update({
                "image": updated_entry.get("image", entry["image"]).replace('<br>', ''),
                "note": updated_entry.get("note", entry.get("note", "")).replace('<br>', ''),
                "country": updated_entry.get("country", entry["country"]).replace('<br>', ''),
                "donor_name": updated_entry.get("donor_name", entry["donor_name"]).replace('<br>', ''),
                "currency_type": updated_entry.get("currency_type", entry["currency_type"]).replace('<br>', ''),
                "size": updated_entry.get("size", entry.get("size", "")).replace('<br>', ''),
                "year": updated_entry.get("year", entry.get("year", "")).replace('<br>', '')
            })

            # ✅ Handle hidden_note
            if "hidden_note" in updated_entry:
                entry["hidden_note"] = updated_entry["hidden_note"].replace('<br>', '')
            elif "hidden_note" not in updated_entry and "hidden_note" in entry:
                del entry["hidden_note"]

    write_json_file(data)


def delete_entry(entry):
    data = read_json_file()
    updated_data = [item for item in data if item["image"] != entry["image"]]
    file_path = os.path.join(UPLOAD_FOLDER, entry["country"], entry["image"])
    if os.path.exists(file_path):
        os.remove(file_path)
    write_json_file(updated_data)

def load_json():
    with file_lock:  # Ensure thread-safe access
        if os.path.exists(current_json_file_path):
            with open(current_json_file_path, 'r') as file:
                return json.load(file)
    return []

def save_json(data):
    """Save JSON and handle image moves when country changes"""
    with file_lock:  # Ensure thread-safe access

        # Load existing JSON to compare old vs new
        if os.path.exists(current_json_file_path):
            with open(current_json_file_path, 'r') as f:
                old_data = json.load(f)
        else:
            old_data = []

        # Map old entries by image filename
        old_map = {entry["image"]: entry for entry in old_data}

        for entry in data:
            image = entry.get("image")
            country = entry.get("country")

            if not image or not country:
                continue

            old_entry = old_map.get(image)
            if old_entry:
                old_country = old_entry.get("country")

                # Country has changed
                if old_country and old_country != country:
                    old_path = os.path.join(BASE_UPLOAD_FOLDER, old_country, image)
                    new_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
                    new_path = os.path.join(new_folder, image)

                    try:
                        os.makedirs(new_folder, exist_ok=True)

                        if os.path.exists(old_path):
                            os.rename(old_path, new_path)  # move file
                            print(f"Moved {image} from {old_country} to {country}")
                        else:
                            print(f"Old file {old_path} not found, skipping move.")

                    except Exception as e:
                        print(f"Error moving file {image}: {e}")

        # Finally, save updated JSON
        with open(current_json_file_path, 'w') as f:
            json.dump(data, f, indent=2)


# Route to serve the ./index.html located in project root
@app.route('/root-index')
def root_index():
    return send_from_directory('.', 'index.html')

# Serve ./display.html
@app.route('/display.html')
def display_html():
    return send_from_directory('.', 'display.html')


# Serve ./countries.continents.json
@app.route('/countries.continents.json')
def countries_continents_json():
    return send_from_directory('.', 'countries.continents.json')

# Serve ./images/coins.json
@app.route('/images/coins.json')
def coins_json():
    return send_from_directory('images', 'coins.json')

# Serve ./countries.json
@app.route('/countries.json')
def countries_json():
    return send_from_directory('.', 'countries.json')

# Serve ./geojson/country_geojson_mapping.json
@app.route('/geojson/country_geojson_mapping.json')
def country_geojson_mapping():
    return send_from_directory('geojson', 'country_geojson_mapping.json')

# Serve ./continents.geojson
@app.route('/continents.geojson')
def continents_geojson():
    return send_from_directory('.', 'continents.geojson')

@app.route('/images/<path:filename>')
def serve_images_new(filename):
    return send_from_directory('images', filename)

@app.route('/geojson/<path:filename>')
def serve_geojson_new(filename):
    return send_from_directory('geojson', filename)
    
# Serve ./countries.languages.jso
@app.route('/countries.languages.json')
def countries_languages_json():
    return send_from_directory('.', 'countries.languages.json')
    
# Serve ./countries.details.json
@app.route('/countries.details.json')
def countries_details_json():
    return send_from_directory('.', 'countries.details.json')

@app.route('/flags/svg/<path:filename>')
def serve_flags_svg(filename):
    return send_from_directory('flags/svg', filename)


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload')
@app.route("/", methods=["GET", "POST"])
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Get form data
        country = request.form.get('country')
        note = request.form.get('note')
        donor_name = request.form.get('donor_name')
        currency_type = request.form.get('currency_type')
        size = request.form.get('size', '')
        year = request.form.get('year', '')
        hidden_note = request.form.get('hidden_note', '')
        
        print(f"Received form data: country={country}, donor={donor_name}, currency={currency_type}")

        # Validate required fields
        if not country:
            return jsonify({"message": "Country is required!"}), 400
        if not donor_name:
            return jsonify({"message": "Donor name is required!"}), 400
        if not currency_type:
            return jsonify({"message": "Currency type is required!"}), 400

        file = request.files.get('file')
        
        # Check if file was provided
        if not file or file.filename == '':
            print("No file provided in upload")
            return jsonify({"message": "No file provided!"}), 400
        
        # Check if file is allowed
        if not allowed_file(file.filename):
            print(f"File type not allowed: {file.filename}")
            return jsonify({"message": "File type not allowed!"}), 400
        
        # Handle local file upload
        try:
            file_path, file_name = save_file(file, country)
            # Update the JSON file with all fields including hidden_note
            update_json_file(country, file_name, note, donor_name, currency_type, size, year, hidden_note)
            return jsonify({
                "message": "File uploaded successfully!",
                "country": country,
                "note": note,
                "donor_name": donor_name,
                "currency_type": currency_type,
                "size": size,
                "year": year,
                "hidden_note": hidden_note,
                "file_path": file_path,
                "file_name": file_name
            })
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return jsonify({"message": "Error saving file!", "error": str(e)}), 500

    except Exception as e:
        print(f"Unexpected error in upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Server error!", "error": str(e)}), 500


@app.route('/upload-form')
def upload_form_page():
    """Serve the upload form page with image merging functionality"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload New Collection Item</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            position: relative;
        }

        .header-section {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }

        h1 {
            color: #2c3e50;
            font-size: 28px;
            font-weight: 700;
        }

        .navigation-buttons {
            display: flex;
            gap: 10px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e8ed;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
            outline: none;
        }

        .form-group textarea {
            height: 80px;
            resize: vertical;
        }

        .drop-area {
            border: 2px dashed #bdc3c7;
            border-radius: 8px;
            padding: 25px;
            text-align: center;
            background-color: #f8f9fa;
            color: #7f8c8d;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .drop-area.highlight {
            border-color: #3498db;
            background-color: #ebf5fb;
            color: #3498db;
        }

        .btn {
            padding: 12px 25px;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            margin-right: 10px;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .btn-primary {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
        }

        .btn-primary:hover {
            background: linear-gradient(135deg, #2980b9 0%, #2471a3 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
        }

        .btn-success {
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            box-shadow: 0 2px 8px rgba(39, 174, 96, 0.3);
        }

        .btn-success:hover {
            background: linear-gradient(135deg, #229954 0%, #1e8449 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(39, 174, 96, 0.4);
        }

        .btn-danger {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            box-shadow: 0 2px 8px rgba(231, 76, 60, 0.3);
        }

        .btn-danger:hover {
            background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4);
        }

        .btn-secondary {
            background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
            box-shadow: 0 2px 8px rgba(149, 165, 166, 0.3);
        }

        .btn-secondary:hover {
            background: linear-gradient(135deg, #7f8c8d 0%, #717d7e 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(149, 165, 166, 0.4);
        }

        .image-preview {
            max-width: 100%;
            max-height: 200px;
            margin-top: 10px;
            display: none;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .toast-message {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 6px;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            font-weight: 600;
        }

        .toast-message.error {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        }

        .merge-controls {
            margin-top: 25px;
            padding: 20px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }

        .merge-controls h3 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 18px;
        }

        .merge-drop-area {
            min-height: 120px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .merge-options {
            margin: 20px 0;
        }

        .merge-options label {
            display: inline-flex;
            align-items: center;
            margin-right: 20px;
            font-weight: 500;
            cursor: pointer;
        }

        .merge-options input[type="radio"] {
            margin-right: 8px;
        }

        #mergePreviewContainer {
            margin-top: 20px;
        }

        .merge-preview {
            padding: 15px;
            border: 2px dashed #3498db;
            border-radius: 8px;
            background-color: white;
        }

        .merge-preview img {
            max-width: 100%;
            max-height: 150px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        .merge-size-info {
            font-size: 12px;
            color: #7f8c8d;
            margin-top: 8px;
            font-weight: 500;
        }

        .image-drop-areas-container {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
        }

        .form-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #f0f0f0;
        }

        .btn i {
            margin-right: 8px;
        }

        .required-field::after {
            content: " *";
            color: #e74c3c;
        }
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="header-section">
            <h1><i class="fas fa-upload"></i> Upload New Collection Item</h1>
            <div class="navigation-buttons">
                <a href="http://localhost:5000/edit_json" class="btn btn-secondary" target="_blank">
                    <i class="fas fa-edit"></i> JSON Editor
                </a>
                <a href="http://localhost:5000/root-index" class="btn btn-secondary" target="_blank">
                    <i class="fas fa-home"></i> Home
                </a>
            </div>
        </div>
        
        <form id="uploadForm">
            <div class="form-group">
                <label for="country" class="required-field">Country:</label>
                <select id="country" name="country" required>
                    <option value="">Select a country</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="currencyType" class="required-field">Currency Type:</label>
                <select id="currencyType" name="currency_type" required>
                    <option value="coin">Coin</option>
                    <option value="paper-bill">Paper Bill</option>
                    <option value="antique">Antique</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="donorName" class="required-field">Donor Name:</label>
                <input type="text" id="donorName" name="donor_name" required placeholder="Enter donor name">
            </div>
            
            <div class="form-group">
                <label for="note">Note:</label>
                <textarea id="note" name="note" placeholder="Add any additional notes..."></textarea>
            </div>
            
            <div class="form-group">
                <label for="size">Size:</label>
                <input type="text" id="size" name="size" placeholder="e.g., 25mm">
            </div>
            
            <div class="form-group">
                <label for="year">Year:</label>
                <input type="text" id="year" name="year" placeholder="e.g., 2023">
            </div>
            
            <div class="form-group">
                <label for="hiddenNote">Hidden Note (Optional):</label>
                <textarea id="hiddenNote" name="hidden_note" placeholder="Not shown publicly - for internal use only"></textarea>
            </div>
            
            <div class="form-group">
                <label class="required-field">Image Upload:</label>
                <div class="drop-area" id="imageDropArea">
                    <p><i class="fas fa-cloud-upload-alt" style="font-size: 24px; margin-bottom: 10px;"></i></p>
                    <p>Drag & drop an image here or click to select</p>
                    <p style="font-size: 12px; color: #95a5a6; margin-top: 5px;">Supports: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP</p>
                    <input type="file" id="imageInput" accept="image/*" style="display: none;">
                </div>
                <img id="imagePreview" class="image-preview">
            </div>
            
            <div class="merge-controls">
                <h3><i class="fas fa-object-group"></i> Merge Images (Optional)</h3>
                <p style="color: #7f8c8d; margin-bottom: 15px;">Combine two images into one (e.g., front and back of a coin)</p>
                
                <div class="image-drop-areas-container">
                    <div class="drop-area merge-drop-area" id="mergeDropArea1">
                        <p><i class="fas fa-image" style="font-size: 20px; margin-bottom: 8px;"></i></p>
                        <p>Drag & drop first image here</p>
                    </div>
                    <div class="drop-area merge-drop-area" id="mergeDropArea2">
                        <p><i class="fas fa-image" style="font-size: 20px; margin-bottom: 8px;"></i></p>
                        <p>Drag & drop second image here</p>
                    </div>
                </div>
                
                <div class="merge-options">
                    <div>
                        <strong>Merge Direction:</strong>
                        <label><input type="radio" name="mergeDirection" value="horizontal" checked> <i class="fas fa-arrows-alt-h"></i> Side by Side</label>
                        <label><input type="radio" name="mergeDirection" value="vertical"> <i class="fas fa-arrows-alt-v"></i> Top and Bottom</label>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <strong>Resize Option:</strong>
                        <label><input type="radio" name="resizeOption" value="equal" checked> <i class="fas fa-equals"></i> Equal Size</label>
                        <label><input type="radio" name="resizeOption" value="original"> <i class="fas fa-expand"></i> Keep Original Sizes</label>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <button type="button" id="mergeImagesBtn" class="btn btn-primary" disabled>
                            <i class="fas fa-object-group"></i> Merge Images
                        </button>
                        <button type="button" id="clearMergeBtn" class="btn btn-danger">
                            <i class="fas fa-trash"></i> Clear Merge
                        </button>
                    </div>
                </div>
                
                <div id="mergePreviewContainer" style="display: none;">
                    <div class="merge-preview">
                        <p><strong><i class="fas fa-eye"></i> Preview:</strong></p>
                        <div id="imagePreviews"></div>
                        <div class="merge-size-info" id="sizeInfo"></div>
                    </div>
                </div>
            </div>
            
            <div class="form-actions">
                <div>
                    <button type="submit" class="btn btn-success">
                        <i class="fas fa-check"></i> Upload Item
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="window.open('/edit_json', '_blank')">Edit JSON</button>
                        <i class="fas fa-arrow-left"></i> Back to Editor
                    </button>
                </div>
                <a href="http://localhost:5000/root-index" class="btn btn-secondary" target="_blank">
                    <i class="fas fa-home"></i> Go to Home
                </a>
            </div>
        </form>
    </div>
    
    <div id="toastMessage" class="toast-message"></div>

    <script>
        // Your existing JavaScript code remains exactly the same
        let uploadedFile = null;
        let mergeImage1 = null;
        let mergeImage2 = null;
        let countriesData = [];

        // Load countries on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadCountries();
            setupEventListeners();
            setupImageMerging();
        });

        function loadCountries() {
            fetch('/get-countries')
                .then(response => response.json())
                .then(data => {
                    countriesData = data;
                    populateCountryDropdown();
                })
                .catch(error => {
                    console.error("Error loading countries:", error);
                    // Fallback countries
                    countriesData = [
                        {name: "United States"}, {name: "Canada"}, {name: "United Kingdom"},
                        {name: "Germany"}, {name: "France"}, {name: "Japan"},
                        {name: "China"}, {name: "India"}, {name: "Australia"},
                        {name: "Mexico"}, {name: "Brazil"}, {name: "Russia"}
                    ];
                    populateCountryDropdown();
                });
        }

        function populateCountryDropdown() {
            const countrySelect = document.getElementById('country');
            countrySelect.innerHTML = '<option value="">Select a country</option>';
            
            countriesData.forEach(country => {
                const option = document.createElement('option');
                option.value = country.name;
                option.textContent = country.name;
                countrySelect.appendChild(option);
            });
        }

        // ... rest of your existing JavaScript code remains exactly the same
        // (All the setupEventListeners, setupImageMerging, and other functions)
    </script>
</body>
</html>
    '''



@app.route('/merge-images-upload', methods=['POST'])
def merge_images_upload():
    """Handle image merging for the upload form"""
    try:
        # Get form data
        country = request.form.get('country')
        image1 = request.files.get('image1')
        image2 = request.files.get('image2')
        direction = request.form.get('direction', 'horizontal')
        
        if not all([country, image1, image2]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Process images
        img1 = Image.open(image1)
        img2 = Image.open(image2)
        
        # Determine output format
        output_format = 'PNG'
        if image1.content_type == 'image/jpeg' and image2.content_type == 'image/jpeg':
            output_format = 'JPEG'
        
        # Merge images
        if direction == 'horizontal':
            # Resize to same height
            max_height = max(img1.height, img2.height)
            img1_resized = ImageOps.contain(img1, (img1.width, max_height))
            img2_resized = ImageOps.contain(img2, (img2.width, max_height))
            
            new_width = img1_resized.width + img2_resized.width
            if output_format == 'PNG':
                merged_image = Image.new('RGBA', (new_width, max_height))
            else:
                merged_image = Image.new('RGB', (new_width, max_height))
                
            merged_image.paste(img1_resized, (0, 0))
            merged_image.paste(img2_resized, (img1_resized.width, 0))
        else:
            # Resize to same width
            max_width = max(img1.width, img2.width)
            img1_resized = ImageOps.contain(img1, (max_width, img1.height))
            img2_resized = ImageOps.contain(img2, (max_width, img2.height))
            
            new_height = img1_resized.height + img2_resized.height
            if output_format == 'PNG':
                merged_image = Image.new('RGBA', (max_width, new_height))
            else:
                merged_image = Image.new('RGB', (max_width, new_height))
                
            merged_image.paste(img1_resized, (0, 0))
            merged_image.paste(img2_resized, (0, img1_resized.height))
        
        # Save merged image
        file_ext = 'jpg' if output_format == 'JPEG' else 'png'
        file_uuid = str(uuid.uuid4())
        filename = f"{file_uuid}.{file_ext}"
        country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
        
        os.makedirs(country_folder, exist_ok=True)
        file_path = os.path.join(country_folder, filename)
        
        save_kwargs = {'quality': 95} if output_format == 'JPEG' else {}
        merged_image.save(file_path, format=output_format, **save_kwargs)
        
        return jsonify({
            "message": "Images merged successfully",
            "filename": filename,
            "filepath": file_path,
            "format": output_format
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to merge images: {str(e)}"}), 500


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if request.method == 'POST':
        action = 'delete' if request.form.get('delete') else 'edit'
        value = request.form.get('delete') or request.form.get('edit')
        edit_or_delete_entry(action, value)

    coins = read_json_file()
    return render_template('edit.html', title="Edit Page", jsonfile=json.dumps(coins))

@app.route('/test', methods=['POST'])
def test():
    data = request.get_json()
    update_entry(data)
    return render_template('edit_table.html')

@app.route('/testdelete', methods=['POST'])
def testdelete():
    data = request.get_json()
    delete_entry(data)
    return render_template('edit_table.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            session['id'] = request.form['username']
            return redirect(url_for('upload_form'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return render_template('login.html')

# Check if the uploaded file has an allowed extension
def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Route to render the crop image page
@app.route('/crop-image')
def crop_image():
    return render_template('crop.html')

# Route to serve cropped images
@app.route('/crop/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

# Route to handle image upload and save cropped image
@app.route('/crop', methods=['POST'])
def upload_cropped_image():
    if 'image' not in request.files:
        return jsonify({'message': 'No image file provided'}), 400

    file = request.files['image']

    if file and allowed_image_file(file.filename):
        filename = file.filename
        file_path = os.path.join(IMAGE_FOLDER, filename)
        file.save(file_path)  # Save the uploaded image
        return jsonify({'message': f'Cropped image saved as {filename}', 'file_path': file_path}), 200
    else:
        return jsonify({'message': 'Invalid file type'}), 400

@app.route('/manage_image', methods=['GET', 'POST'])
def manage_image():
    # List the images in the /crop folder
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if allowed_image_file(f)]

    if request.method == 'POST':
        # Uploading a new image
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename == '':
                flash('No selected file', 'error')
            elif file and allowed_image_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(IMAGE_FOLDER, filename))
                flash(f"Image uploaded successfully: {filename}", 'success')
                return redirect(url_for('manage_image'))

        # Renaming the image
        if 'new_name' in request.form:
            image_file = request.form['image_file']
            new_name = request.form['new_name']
            if image_file and new_name:
                extension = os.path.splitext(image_file)[1]  # Preserve the file extension
                new_image_path = os.path.join(IMAGE_FOLDER, f'{new_name}{extension}')
                try:
                    os.rename(os.path.join(IMAGE_FOLDER, image_file), new_image_path)
                    flash(f"Image renamed successfully to {new_name}{extension}", 'success')
                except Exception as e:
                    flash(f"Error renaming image: {e}", 'error')
                return redirect(url_for('manage_image'))

        # Deleting the image
        if 'delete' in request.form:
            image_file = request.form['image_file']
            if image_file:
                try:
                    os.remove(os.path.join(IMAGE_FOLDER, image_file))
                    flash("Image deleted successfully.", 'success')
                except Exception as e:
                    flash(f"Error deleting image: {e}", 'error')
                return redirect(url_for('manage_image'))

    return render_template('renameimage.html', image_files=image_files)

# Serve image files
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

# API to get countries data
@app.route('/get-countries', methods=['GET'])
def get_countries():
    countries = load_countries()
    return jsonify(countries)

# API to handle image upload for a specific country
@app.route('/upload-image', methods=['POST'])
def upload_image():
    try:
        country = request.form.get('country')
        file = request.files.get('file')
        existing_image = request.form.get('existing_image')  # 👈 pass current filename from frontend if editing

        if not country:
            return jsonify({"error": "Country is required"}), 400

        if not file:
            return jsonify({"error": "No file provided"}), 400

        country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
        os.makedirs(country_folder, exist_ok=True)

        file_ext = file.filename.rsplit('.', 1)[-1].lower()

        if existing_image:
            old_ext = existing_image.rsplit('.', 1)[-1].lower()
            if file_ext == old_ext:
                # ✅ Replace old file, keep same name
                filename = existing_image
            else:
                # ✅ Different extension → generate new UUID
                filename = f"{uuid.uuid4()}.{file_ext}"
        else:
            # ✅ No existing image → new UUID
            filename = f"{uuid.uuid4()}.{file_ext}"

        file_path = os.path.join(country_folder, filename)
        file.save(file_path)

        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "filepath": file_path
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Edit JSON page - now with embedded HTML
@app.route('/edit_json')
def edit_json():
    global current_json_file_path
    current_json_file_path = DEFAULT_JSON_FILE_PATH  # Reset to default file
    
    # Return the embedded HTML content directly
    return '''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="shortcut icon" href="#">
    <title>..::Amir's edit json::..</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }

        body {
            background-color: #72787e;
            color: #fff;
            padding: 20px;
        }

        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #ffc107;
        }

        .container {
            width: 80%;
            margin: 0 auto;
            padding: 20px;
            background-color: #495057;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }

        #jsonTableContainer {
            border: 2px solid #198754;
            padding: 10px;
            background-color: #6c757d;
            min-height: 100px;
            border-radius: 4px;
        }

        .row {
            display: flex;
            align-items: center;
            border-bottom: 1px solid #ddd;
            padding: 10px 0;
            transition: background-color 0.3s ease;
        }

        .row:nth-child(odd) {
            background-color: #6c757d;
        }

        .row:hover {
            background-color: #495057;
        }

        .column {
            flex: 1;
            text-align: center;
            padding: 5px;
            color: #fff;
        }

        .thumbnail {
            max-width: 50px;
            max-height: 50px;
            border-radius: 4px;
            cursor: pointer;
        }

        .delete-btn {
            color: #ff4d4d;
            cursor: pointer;
            font-weight: bold;
        }

        a {
            color: #ffc107;
            text-decoration: none;
        }

        a:hover {
            color: #fff;
            text-decoration: underline;
        }

        .download-btn {
            width: 100%;
            padding: 10px;
            background-color: #198754;
            color: #fff;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s ease;
        }

        .download-btn:hover {
            background-color: #145d37;
        }

        .file-input {
            margin-bottom: 20px;
            display: block;
            padding: 10px;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fff;
            color: #333;
        }

        .header {
            font-weight: bold;
            background-color: #198754;
            color: #fff;
        }

        .add-row-btn {
            width: 100%;
            padding: 10px;
            background-color: #ffc107;
            color: #333;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
            transition: background 0.3s ease;
        }

        .add-row-btn:hover {
            background-color: #e0a800;
        }

        .image-input {
            width: 100%;
            padding: 5px;
            font-size: 14px;
            text-align: center;
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
            overflow-y: auto;
        }

        .modal-content {
            position: relative;
            width: 90%;
            max-width: 800px;
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #333;
            max-height: 90vh;
            overflow-y: auto;
        }

        .modal img {
            max-width: 100%;
            max-height: 400px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .modal-close {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 20px;
            color: black;
            cursor: pointer;
        }

        .modal h2,
        .modal p {
            margin: 10px 0;
        }

        /* Form styling */
        .edit-form {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            text-align: left;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }

        .form-group textarea {
            height: 80px;
            resize: vertical;
        }

        .save-btn {
            grid-column: span 2;
            padding: 10px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }

        .save-btn:hover {
            background-color: #218838;
        }

        /* Drag-and-drop effects */
        .row.draggable {
            cursor: move;
        }

        .row.drag-over {
            background-color: #495057;
        }

        /* imageModal */
        .image-filename {
            margin-top: 10px;
            font-size: 14px;
            color: #333;
            text-align: center;
            font-weight: bold;
        }

        /*sorting*/
        .sortable {
            cursor: pointer;
            position: relative;
        }
        
        .sortable:after {
            content: ' ⇅';
            font-size: 0.8em;
            color: #ccc;
            position: absolute;
            right: 5px;
        }
        
        /* Hide the default file input */
        #uploadFileInput {
            display: none;
        }

        /* Professional button styling */
        .btn-success {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
            margin: 5px;
        }

        .btn-success:hover {
            background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
            text-decoration: none;
            color: white;
        }

        .btn-success i {
            margin-right: 8px;
            font-size: 16px;
        }

        .btn-secondary {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(108, 117, 125, 0.3);
            margin: 5px;
        }

        .btn-secondary:hover {
            background: linear-gradient(135deg, #5a6268 0%, #545b62 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(108, 117, 125, 0.4);
            color: white;
            text-decoration: none;
        }

        .btn-secondary i {
            margin-right: 8px;
            font-size: 16px;
        }

        /* Style the file input trigger (the label) */
        .file-input-label {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            font-size: 14px;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);
            margin: 5px;
        }

        .file-input-label:hover {
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.4);
        }

        .file-input-label i {
            margin-right: 8px;
        }

        /* Style the upload button with an icon */
        #uploadFileBtn {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            font-size: 14px;
            border-radius: 6px;
            cursor: pointer;
            border: none;
            margin: 5px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
            font-weight: 600;
        }

        #uploadFileBtn i {
            margin-right: 8px;
        }

        #uploadFileBtn:hover {
            background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
        }

        /* css for delete buttons*/
        .delete-btn {
            display: inline-flex;
            align-items: center;
            color: yellow;
            cursor: pointer;
            font-weight: bold;
        }

        .delete-btn i {
            margin-right: 8px;
        }

        .delete-btn:hover {
            color: red;
        }

        /* Dropdown styling */
        .country-dropdown {
            width: 100%;
            padding: 5px;
            font-size: 14px;
            text-align: center;
            background-color: #fff;
            color: #333;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        /* Drag and drop area styling */
        .drop-area {
            border: 2px dashed #ccc;
            border-radius: 4px;
            padding: 20px;
            text-align: center;
            background-color: #f8f9fa;
            color: #333;
            margin: 10px 0;
            cursor: pointer;
        }

        .drop-area.highlight {
            border-color: #007bff;
            background-color: #e9f0ff;
        }
        
        /* Currency type dropdown */
        .currency-dropdown {
            width: 100%;
            padding: 5px;
            font-size: 14px;
            text-align: center;
            background-color: #fff;
            color: #333;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        /* Image drop area in table */
        .image-drop-area {
            border: 2px dashed #ccc;
            border-radius: 4px;
            padding: 10px;
            text-align: center;
            background-color: #f8f9fa;
            color: #333;
            margin: 5px 0;
            cursor: pointer;
            min-height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .image-drop-area.highlight {
            border-color: #007bff;
            background-color: #e9f0ff;
        }

        .image-drop-area p {
            margin: 0;
            font-size: 12px;
        }
        
        /* Search box styling */
    .search-container {
        margin-bottom: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }

    .search-box {
        width: 300px;
        padding: 10px;
        font-size: 16px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: #fff;
        color: #333;
    }

    .search-box:focus {
        outline: none;
        border-color: #007bff;
        box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
    }

    .clear-search-btn {
        padding: 10px;
        background-color: #dc3545;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .clear-search-btn:hover {
        background-color: #c82333;
    }
    
    .toast-message {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: rgba(40, 167, 69, 0.5);
        color: white;
        padding: 15px;
        text-align: center;
        font-size: 16px;
        font-weight: bold;
        z-index: 3000;
        opacity: 0;
        display: none;
        transition: opacity 0.5s ease;
    }

    .filter-buttons {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-bottom: 20px;
    }

    .filter-btn {
        padding: 10px 15px;
        background-color: #6c757d;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        transition: background 0.3s ease;
    }

    .filter-btn:hover {
        background-color: #5a6268;
    }

    .filter-btn.active {
        background-color: #28a745;
    }

    .search-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }

    .search-box {
        width: 100%;
        padding: 10px;
        font-size: 14px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: #fff;
        color: #333;
    }

    .image-drop-areas-container {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }

    .merge-drop-area {
        flex: 1;
        min-height: 80px;
    }

    .merge-options {
        display: flex;
        gap: 15px;
        align-items: center;
        margin-bottom: 10px;
    }

    .merge-options label {
        display: flex;
        align-items: center;
        gap: 5px;
        color: #333;
        font-weight: normal;
    }

    #mergeImagesBtn {
        padding: 5px 10px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }

    #mergeImagesBtn:disabled {
        background-color: #6c757d;
        cursor: not-allowed;
    }
    
    .merge-preview {
        margin-top: 10px;
        padding: 10px;
        border: 2px dashed #007bff;
        border-radius: 5px;
        background-color: #f8f9fa;
    }

    .merge-preview img {
        max-width: 100%;
        max-height: 150px;
        margin: 5px;
        border: 1px solid #ddd;
    }

    .merge-size-info {
        font-size: 12px;
        color: #666;
        margin-top: 5px;
    }

    .button-container {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin: 15px 0;
        flex-wrap: wrap;
    }
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>

<body>
    <div id="toastMessage" class="toast-message">✅ Changes saved successfully!</div>

    <div class="container">
        <h1>JSON Viewer & Editor</h1>

        <div class="search-container">
            <input type="text" id="countrySearch" class="search-box" placeholder="Search by country...">
            <input type="text" id="sizeSearch" class="search-box" placeholder="Search by size...">
            <input type="number" id="yearFromSearch" class="search-box" placeholder="Year from..." min="0" max="9999">
            <input type="number" id="yearToSearch" class="search-box" placeholder="Year to..." min="0" max="9999">
            <button id="clearSearch" class="clear-search-btn" title="Clear all filters">
                <i class="fas fa-times"></i>
            </button>
        </div>

        <div class="filter-buttons">
            <button id="applyFilters" class="filter-btn">Apply Filters</button>
            <button id="clearFilters" class="filter-btn">Clear Filters</button>
            <button id="toggleAddMode" class="filter-btn">Add New Mode</button>
        </div>
        
        <!-- Updated Professional Button Container -->
        <div class="button-container">
            <label for="uploadFileInput" class="file-input-label">
                <i class="fas fa-file-upload"></i> Choose File
            </label>
            <input type="file" id="uploadFileInput" accept=".json" />

            <button id="uploadFileBtn">
                <i class="fas fa-upload"></i> Upload File
            </button>

            <button class="btn-success" onclick="window.location.href='/upload-form'">
                <i class="fas fa-plus-circle"></i> Add New Item
            </button>
        </div>

        <div id="jsonTableContainer">Loading data...</div>

        <button class="add-row-btn" id="addRowBtn">Add New Row</button>
        <button class="download-btn" id="downloadBtn">Download Updated JSON</button>
        
        <!-- Keep the second Add New Item button at the bottom -->
        <div class="button-container" style="margin-top: 20px;">
            <button class="btn-success" onclick="window.location.href='/upload-form'">
                <i class="fas fa-plus-circle"></i> Add New Item
            </button>
        </div>
    </div>

    <div id="imageModal" class="modal">
        <div class="modal-content">
            <span id="closeModal" class="modal-close">&times;</span>
            <img id="modalImage" src="" alt="Enlarged Image">
            <div id="imageFileName" class="image-filename"></div>
            <div class="edit-form" id="editForm">
                <div class="form-group">
                    <label for="editCountry">Country:</label>
                    <select id="editCountry" name="country" class="country-dropdown"></select>
                </div>
                <div class="form-group">
                    <label for="editCurrencyType">Currency Type:</label>
                    <select id="editCurrencyType" name="currency_type" class="currency-dropdown">
                        <option value="coin">Coin</option>
                        <option value="paper-bill">Paper Bill</option>
                        <option value="antique">Antique</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="editDonorName">Donor Name:</label>
                    <input type="text" id="editDonorName" name="donor_name">
                </div>
                <div class="form-group">
                    <label for="editNote">Note:</label>
                    <textarea id="editNote" name="note"></textarea>
                </div>
                <div class="form-group">
                    <label for="editSize">Size:</label>
                    <input type="text" id="editSize" name="size">
                </div>
                <div class="form-group">
                    <label for="editYear">Year:</label>
                    <input type="text" id="editYear" name="year">
                </div>
                <div class="form-group" style="grid-column: span 2;">
                    <label for="editImage">Image:</label>
                    <div class="drop-area" id="modalImageDropArea">
                        <p>Drag & drop an image here or click to select</p>
                        <input type="file" id="editImageInput" accept="image/*" style="display: none;">
                    </div>
                </div>
                
                <div class="form-group" style="grid-column: span 2;">
                    <label>Merge Images (Optional):</label>
                    <div class="merge-controls">
                        <div class="image-drop-areas-container">
                            <div class="image-drop-area merge-drop-area" id="mergeDropArea1">
                                <p>Drag & drop first image here</p>
                            </div>
                            <div class="image-drop-area merge-drop-area" id="mergeDropArea2">
                                <p>Drag & drop second image here</p>
                            </div>
                        </div>
                        
                        <div class="merge-options">
                            <div>
                                <strong>Merge Direction:</strong>
                                <label><input type="radio" name="mergeDirection" value="horizontal" checked> Side by Side</label>
                                <label><input type="radio" name="mergeDirection" value="vertical"> Top and Bottom</label>
                            </div>
                            
                            <div style="margin-top: 10px;">
                                <strong>Resize Option:</strong>
                                <label><input type="radio" name="resizeOption" value="equal" checked> Equal Size</label>
                                <label><input type="radio" name="resizeOption" value="original"> Keep Original Sizes</label>
                            </div>
                            
                            <button type="button" id="modalMergeImagesBtn" disabled>Merge Images</button>
                        </div>
                        
                        <div id="mergePreviewContainer" style="display: none;">
                            <div class="merge-preview">
                                <p><strong>Preview:</strong></p>
                                <div id="imagePreviews"></div>
                                <div class="merge-size-info" id="sizeInfo"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="editHiddenNote">Hidden Note:</label>
                    <textarea id="editHiddenNote" name="hidden_note" placeholder="(Optional, not shown publicly)"></textarea>
                </div>
                <button type="button" class="save-btn" id="saveChangesBtn">Save Changes</button>
            </div>
            
        </div>
    </div>

    <script>
// Global variables
let jsonData = [];
let sortOrder = 1;
let currentEditingIndex = -1;
let countriesData = [];

// Load countries data
function loadCountries() {
    fetch('/get-countries')
        .then(response => response.json())
        .then(data => {
            countriesData = data;
            populateCountryDropdowns();
        })
        .catch(error => {
            console.error("Error loading countries:", error);
        });
}

// Populate country dropdowns
function populateCountryDropdowns() {
    const editCountryDropdown = document.getElementById('editCountry');
    
    if (!editCountryDropdown) return;
    
    editCountryDropdown.innerHTML = '';
    
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select a country';
    editCountryDropdown.appendChild(defaultOption);
    
    countriesData.forEach(country => {
        const option = document.createElement('option');
        option.value = country.name;
        option.textContent = country.name;
        editCountryDropdown.appendChild(option);
    });
}

function renderTable(data) {
    const tableContainer = document.getElementById("jsonTableContainer");
    if (!tableContainer) return;
    
    tableContainer.innerHTML = '';

    const headerRow = document.createElement('div');
    headerRow.classList.add('row', 'header');
    const headers = [
        { text: 'Country', key: 'country' },
        { text: 'Currency Type', key: 'currency_type' },
        { text: 'Donor Name', key: 'donor_name' },
        { text: 'Image', key: 'image' },
        { text: 'Note', key: 'note' },
        { text: 'Size', key: 'size' },
        { text: 'Year', key: 'year' },
        { text: 'Actions', key: null }
    ];
    
    headers.forEach(header => {
        const column = document.createElement('div');
        column.classList.add('column');
        column.textContent = header.text;
        if (header.key) {
            column.dataset.key = header.key;
            column.classList.add('sortable');
            column.addEventListener('click', () => {
                sortTable(header.key);
            });
        }
        headerRow.appendChild(column);
    });
    tableContainer.appendChild(headerRow);

    data.forEach((row, index) => {
        const rowDiv = document.createElement('div');
        rowDiv.classList.add('row');
        rowDiv.draggable = true;
        rowDiv.setAttribute('data-index', index);

        rowDiv.addEventListener('dragstart', handleDragStart);
        rowDiv.addEventListener('dragover', handleDragOver);
        rowDiv.addEventListener('drop', handleDrop);

        // Country dropdown
        const countryColumn = document.createElement('div');
        countryColumn.classList.add('column');
        const countrySelect = document.createElement('select');
        countrySelect.classList.add('country-dropdown');

        countrySelect.addEventListener('change', function() {
            const oldCountry = row.country;
            const newCountry = this.value;
            const image = row.image;

            if (!image || image === "placeholder.jpg") {
                row.country = newCountry;
                saveUpdates();
                return;
            }

            fetch('/update-country', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: image,
                    old_country: oldCountry,
                    new_country: newCountry
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                    this.value = oldCountry;
                } else {
                    console.log(data.message);
                    row.country = newCountry;
                    renderTable(jsonData);
                }
            })
            .catch(error => {
                console.error("Error updating country:", error);
                this.value = oldCountry;
            });
        });

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select country';
        countrySelect.appendChild(defaultOption);
        
        countriesData.forEach(country => {
            const option = document.createElement('option');
            option.value = country.name;
            option.textContent = country.name;
            if (row.country === country.name) {
                option.selected = true;
            }
            countrySelect.appendChild(option);
        });
        
        if (row.country && !countriesData.some(c => c.name === row.country)) {
            const option = document.createElement('option');
            option.value = row.country;
            option.textContent = row.country;
            option.selected = true;
            countrySelect.appendChild(option);
        }
        
        countryColumn.appendChild(countrySelect);
        rowDiv.appendChild(countryColumn);
        
        // Currency type dropdown
        const currencyColumn = document.createElement('div');
        currencyColumn.classList.add('column');
        const currencySelect = document.createElement('select');
        currencySelect.classList.add('currency-dropdown');
        currencySelect.addEventListener('change', function() {
            row.currency_type = this.value;
            saveUpdates();
        });
        
        const currencyOptions = ['coin', 'paper-bill', 'antique'];
        currencyOptions.forEach(optionValue => {
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionValue.charAt(0).toUpperCase() + optionValue.slice(1);
            if (row.currency_type === optionValue) {
                option.selected = true;
            }
            currencySelect.appendChild(option);
        });
        
        currencyColumn.appendChild(currencySelect);
        rowDiv.appendChild(currencyColumn);
        
        // Donor name (editable)
        const donorColumn = document.createElement('div');
        donorColumn.classList.add('column', 'editable');
        donorColumn.textContent = row.donor_name || "No Donor Name";
        donorColumn.contentEditable = true;
        donorColumn.addEventListener('blur', function() {
            row.donor_name = this.textContent;
            saveUpdates();
        });
        rowDiv.appendChild(donorColumn);
        
        // Image column with drag and drop
        const imageColumn = document.createElement('div');
        imageColumn.classList.add('column');
        
        const dropArea = document.createElement('div');
        dropArea.classList.add('image-drop-area');
        dropArea.setAttribute('data-index', index);

        if (row.image && row.image !== 'placeholder.jpg') {
            dropArea.innerHTML = `<img src="images/${row.country}/${row.image}" 
                                    class="thumbnail" 
                                    data-index="${index}" 
                                    onerror="this.src='images/placeholder.jpg'">`;
        } else {
            dropArea.innerHTML = '<p>Drag & drop image here</p>';
        }

        setupImageDropArea(dropArea, row, index);
        imageColumn.appendChild(dropArea);
        rowDiv.appendChild(imageColumn);
        
        // Note (editable)
        const noteColumn = document.createElement('div');
        noteColumn.classList.add('column', 'editable');
        noteColumn.textContent = row.note || "No Note";
        noteColumn.contentEditable = true;
        noteColumn.addEventListener('blur', function() {
            row.note = this.textContent;
            saveUpdates();
        });
        rowDiv.appendChild(noteColumn);
        
        // Size (editable)
        const sizeColumn = document.createElement('div');
        sizeColumn.classList.add('column', 'editable');
        sizeColumn.textContent = row.size || "No Size";
        sizeColumn.contentEditable = true;
        sizeColumn.addEventListener('blur', function() {
            row.size = this.textContent;
            saveUpdates();
        });
        rowDiv.appendChild(sizeColumn);
        
        // Year (editable)
        const yearColumn = document.createElement('div');
        yearColumn.classList.add('column', 'editable');
        yearColumn.textContent = row.year || "No Year";
        yearColumn.contentEditable = true;
        yearColumn.addEventListener('blur', function() {
            row.year = this.textContent;
            saveUpdates();
        });
        rowDiv.appendChild(yearColumn);
        
        // Actions (delete button)
        const actionColumn = document.createElement('div');
        actionColumn.classList.add('column');
        const deleteBtn = document.createElement('span');
        deleteBtn.classList.add('delete-btn');
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete this entry?')) {
                jsonData.splice(index, 1);
                renderTable(jsonData);
                saveUpdates();
            }
        });
        actionColumn.appendChild(deleteBtn);
        rowDiv.appendChild(actionColumn);

        tableContainer.appendChild(rowDiv);
    });
}

// Setup image drop area functionality
function setupImageDropArea(dropArea, row, index) {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);
    
    dropArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    dropArea.addEventListener('drop', handleDropFile, false);
    
    fileInput.addEventListener('change', handleFileSelect, false);
    
    function handleDropFile(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files, row, index);
    }
    
    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files, row, index);
    }
    
    function handleFiles(files, row, index) {
        if (files.length === 0) return;
        
        const file = files[0];
        const country = row.country;
        
        if (!country) {
            alert('Please select a country first');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('country', country);

        if (row.image && row.image !== "placeholder.jpg") {
            formData.append('existing_image', row.image);
        }

        fetch('/upload-image', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error uploading image: ' + data.error);
            } else {
                jsonData[index].image = data.filename;
                renderTable(jsonData);
                saveUpdates();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error uploading image');
        });
    }
}

function sortTable(key) {
    jsonData.sort((a, b) => {
        if (a[key] < b[key]) return -1 * sortOrder;
        if (a[key] > b[key]) return 1 * sortOrder;
        return 0;
    });
    sortOrder *= -1;
    renderTable(jsonData);
    
    fetch('/update-json', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jsonData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            console.log('Backend JSON updated successfully:', data.message);
        } else {
            console.error('Error updating JSON:', data.error);
            alert(`Error updating JSON: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error with fetch request:', error);
        alert('An error occurred while updating the JSON file.');
    });
}

function handleDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.getAttribute('data-index'));
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function handleDrop(e) {
    e.preventDefault();
    const draggedIndex = e.dataTransfer.getData('text/plain');
    const targetIndex = e.target.closest('.row').getAttribute('data-index');

    if (draggedIndex !== targetIndex) {
        const draggedItem = jsonData.splice(draggedIndex, 1)[0];
        jsonData.splice(targetIndex, 0, draggedItem);
        renderTable(jsonData);
        saveUpdates();
    }
}

function showToast(message) {
    const toast = document.getElementById("toastMessage");
    if (!toast) return;
    
    toast.textContent = "✅ " + message;
    toast.style.display = "block";
    toast.style.opacity = "1";

    setTimeout(() => {
        toast.style.opacity = "0";
    }, 3000);

    setTimeout(() => {
        toast.style.display = "none";
    }, 4000);
}

function saveUpdates() {
    fetch('/update-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonData),
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message || "File updated.");
        showToast(data.message || "Changes saved!");
    })
    .catch(error => {
        console.error("Error:", error);
        showToast("❌ Error saving changes!");
    });
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
    // Load initial data
    fetch('/get-json')
        .then(response => response.json())
        .then(data => {
            jsonData = data;
            renderTable(jsonData);
        })
        .catch(error => {
            console.error("Error fetching JSON data:", error);
            document.getElementById("jsonTableContainer").innerHTML = "Error loading data";
        });

    // Load countries
    loadCountries();

    // Add event listeners
    document.getElementById("uploadFileBtn").addEventListener("click", function () {
        const fileInput = document.getElementById("uploadFileInput");
        const file = fileInput.files[0];

        if (!file) {
            alert("Please select a file to upload.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        fetch('/upload-json', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert(data.message);
                fetch('/get-json')
                    .then(response => response.json())
                    .then(newData => {
                        jsonData = newData;
                        renderTable(jsonData);
                    });
            } else {
                alert(data.error || "An error occurred.");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while uploading the file.");
        });
    });

    document.getElementById("addRowBtn").addEventListener("click", function () {
        const newRow = {
            country: "",
            currency_type: "coin",
            donor_name: "New Donor Name",
            image: "placeholder.jpg",
            note: "New Note",
            size: "",
            year: ""
        };
        jsonData.push(newRow);
        renderTable(jsonData);
        saveUpdates();
    });

    document.getElementById("downloadBtn").addEventListener("click", function () {
        const jsonString = JSON.stringify(jsonData, null, 2);
        const blob = new Blob([jsonString], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "coins.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    document.getElementById("closeModal").addEventListener("click", function () {
        document.getElementById("imageModal").style.display = "none";
    });

    // File input change listener
    document.getElementById("uploadFileInput").addEventListener("change", function (event) {
        const file = event.target.files[0];

        if (!file) {
            alert("No file selected. Please select a JSON file.");
            return;
        }

        if (file.type !== "application/json") {
            alert("Invalid file type. Please upload a valid JSON file.");
            return;
        }

        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                jsonData = JSON.parse(e.target.result);
                renderTable(jsonData);
            } catch (error) {
                alert("Error parsing JSON file. Please check the file format.");
                console.error("JSON Parsing Error:", error);
            }
        };

        reader.onerror = function () {
            alert("Error reading the file. Please try again.");
        };

        reader.readAsText(file);
    });

    // ========== MODAL FUNCTIONALITY ==========

    // Modal click functionality
    document.addEventListener("click", function (event) {
        if (event.target.classList.contains("thumbnail")) {
            const index = event.target.getAttribute("data-index");
            const row = jsonData[index];
            
            // Update modal image and info
            document.getElementById("modalImage").src = `images/${row.country}/${row.image}`;
            document.getElementById("imageFileName").textContent = row.image;
            
            // Populate form fields
            document.getElementById("editCountry").value = row.country || "";
            document.getElementById("editCurrencyType").value = row.currency_type || "";
            document.getElementById("editDonorName").value = row.donor_name || "";
            document.getElementById("editNote").value = row.note || "";
            document.getElementById("editSize").value = row.size || "";
            document.getElementById("editYear").value = row.year || "";
            document.getElementById("editHiddenNote").value = row.hidden_note || "";
            
            currentEditingIndex = index;
            document.getElementById("imageModal").style.display = "flex";
            
            // Reset merge areas
            document.getElementById('mergeDropArea1').innerHTML = '<p>Drag & drop first image here</p>';
            document.getElementById('mergeDropArea2').innerHTML = '<p>Drag & drop second image here</p>';
            document.getElementById('modalMergeImagesBtn').disabled = true;
        }
    });

    // Auto-save functionality for modal fields
    function setupModalAutoSave() {
        const fields = [
            { id: "editCountry", key: "country", type: "select" },
            { id: "editCurrencyType", key: "currency_type", type: "select" },
            { id: "editDonorName", key: "donor_name", type: "input" },
            { id: "editNote", key: "note", type: "textarea" },
            { id: "editSize", key: "size", type: "input" },
            { id: "editYear", key: "year", type: "input" },
            { id: "editHiddenNote", key: "hidden_note", type: "textarea" }
        ];

        fields.forEach(field => {
            const element = document.getElementById(field.id);
            if (!element) return;

            if (field.type === "select") {
                element.addEventListener("change", function() {
                    if (currentEditingIndex !== -1) {
                        jsonData[currentEditingIndex][field.key] = this.value;
                        saveUpdates();
                    }
                });
            } else {
                element.addEventListener("blur", function() {
                    if (currentEditingIndex !== -1) {
                        jsonData[currentEditingIndex][field.key] = this.value;
                        saveUpdates();
                    }
                });
            }
        });
    }

    // Modal image upload functionality
    function setupModalImageUpload() {
        const dropArea = document.getElementById('modalImageDropArea');
        const fileInput = document.getElementById('editImageInput');
        
        if (!dropArea || !fileInput) return;
        
        // Click to select file
        dropArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
        });
        
        // Handle file drop
        dropArea.addEventListener('drop', handleDropFile, false);
        
        // Handle file selection
        fileInput.addEventListener('change', handleFileSelect, false);
        
        function handleDropFile(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }
        
        function handleFileSelect(e) {
            const files = e.target.files;
            handleFiles(files);
        }
        
        function handleFiles(files) {
            if (files.length === 0) return;
            
            const file = files[0];
            const country = document.getElementById('editCountry').value;
            
            if (!country) {
                alert('Please select a country first');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('country', country);
            
            // If editing existing row, replace the image
            if (currentEditingIndex !== -1 && jsonData[currentEditingIndex].image && jsonData[currentEditingIndex].image !== "placeholder.jpg") {
                formData.append('existing_image', jsonData[currentEditingIndex].image);
            }
            
            fetch('/upload-image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error uploading image: ' + data.error);
                } else {
                    // Update the image in the current editing row
                    if (currentEditingIndex !== -1) {
                        jsonData[currentEditingIndex].image = data.filename;
                        renderTable(jsonData);
                        saveUpdates();
                        // Update modal image display
                        document.getElementById("modalImage").src = `images/${country}/${data.filename}`;
                        document.getElementById("imageFileName").textContent = data.filename;
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error uploading image');
            });
        }
    }

    // Modal image merging functionality
    function setupModalImageMerging() {
        let mergeImage1 = null;
        let mergeImage2 = null;

        const mergeDropArea1 = document.getElementById('mergeDropArea1');
        const mergeDropArea2 = document.getElementById('mergeDropArea2');
        const mergeImagesBtn = document.getElementById('modalMergeImagesBtn');

        // Setup drop areas for merging
        function setupMergeDropArea(dropArea, imageNumber) {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
            
            dropArea.addEventListener('click', () => fileInput.click());
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, preventDefaults, false);
            });
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
            });
            
            dropArea.addEventListener('drop', function(e) {
                handleMergeFileDrop(e, imageNumber);
            }, false);
            
            fileInput.addEventListener('change', function(e) {
                handleMergeFileSelect(e, imageNumber);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            function handleMergeFileDrop(e, imageNumber) {
                const dt = e.dataTransfer;
                const files = dt.files;
                handleMergeFiles(files, imageNumber);
            }

            function handleMergeFileSelect(e, imageNumber) {
                const files = e.target.files;
                handleMergeFiles(files, imageNumber);
            }

            function handleMergeFiles(files, imageNumber) {
                if (files.length === 0) return;
                
                const file = files[0];
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file');
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    const fileSizeKB = Math.round(file.size / 1024);
                    const htmlContent = '<img src="' + e.target.result + '" style="max-width: 100%; max-height: 70px;">' +
                                       '<div style="font-size: 10px; margin-top: 5px;">' +
                                       file.name + '<br>' + file.type + ' (' + fileSizeKB + 'KB)' +
                                       '</div>';
                    
                    if (imageNumber === 1) {
                        mergeImage1 = file;
                        mergeDropArea1.innerHTML = htmlContent;
                    } else {
                        mergeImage2 = file;
                        mergeDropArea2.innerHTML = htmlContent;
                    }
                    
                    // Enable merge button if both images are uploaded
                    if (mergeImage1 && mergeImage2) {
                        mergeImagesBtn.disabled = false;
                    }
                };
                reader.readAsDataURL(file);
            }
        }

        // Setup both drop areas
        setupMergeDropArea(mergeDropArea1, 1);
        setupMergeDropArea(mergeDropArea2, 2);

        // Merge button click handler
        mergeImagesBtn.addEventListener('click', function() {
            if (!mergeImage1 || !mergeImage2) {
                alert('Please upload both images first');
                return;
            }
            
            const mergeDirection = document.querySelector('input[name="mergeDirection"]:checked').value;
            const resizeOption = document.querySelector('input[name="resizeOption"]:checked').value;
            const country = document.getElementById('editCountry').value;
            
            if (!country) {
                alert('Please select a country first');
                return;
            }

            // Create FormData for merging
            const formData = new FormData();
            formData.append('image1', mergeImage1);
            formData.append('image2', mergeImage2);
            formData.append('direction', mergeDirection);
            formData.append('country', country);
            formData.append('resizeOption', resizeOption);

            // Show loading state
            const originalText = mergeImagesBtn.textContent;
            mergeImagesBtn.textContent = 'Merging...';
            mergeImagesBtn.disabled = true;

            fetch('/merge-images-upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error merging images: ' + data.error);
                } else {
                    alert('Images merged successfully!');
                    // Update the current row with merged image
                    if (currentEditingIndex !== -1) {
                        jsonData[currentEditingIndex].image = data.filename;
                        renderTable(jsonData);
                        saveUpdates();
                        // Update modal display
                        document.getElementById("modalImage").src = `images/${country}/${data.filename}`;
                        document.getElementById("imageFileName").textContent = data.filename;
                    }
                    // Clear merge areas
                    mergeImage1 = null;
                    mergeImage2 = null;
                    mergeDropArea1.innerHTML = '<p>Drag & drop first image here</p>';
                    mergeDropArea2.innerHTML = '<p>Drag & drop second image here</p>';
                    mergeImagesBtn.disabled = true;
                }
            })
            .catch(error => {
                console.error('Error merging images:', error);
                alert('Error merging images: ' + error.message);
            })
            .finally(() => {
                mergeImagesBtn.textContent = originalText;
                mergeImagesBtn.disabled = false;
            });
        });
    }

    // Initialize modal functionality
    setupModalAutoSave();
    setupModalImageUpload();
    setupModalImageMerging();

});
</script>
</body>

</html>
    '''

# ADD THIS NEW ROUTE - Serve box_country_list.html
@app.route('/box_country_list.html')
def box_country_list():
    return send_from_directory('.', 'box_country_list.html')

@app.route('/get-json', methods=['GET'])
def get_json():
    return jsonify(load_json())

@app.route('/update-json', methods=['POST'])
def update_json():
    try:
        data = request.get_json()
        save_json(data)
        return jsonify({"message": "JSON file updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-country', methods=['POST'])
def update_country():
    try:
        data = request.get_json()
        image = data.get("image")
        old_country = data.get("old_country")
        new_country = data.get("new_country")

        if not image or not old_country or not new_country:
            return jsonify({"error": "Missing parameters"}), 400

        old_path = os.path.join(BASE_UPLOAD_FOLDER, old_country, image)
        new_folder = os.path.join(BASE_UPLOAD_FOLDER, new_country)
        new_path = os.path.join(new_folder, image)

        os.makedirs(new_folder, exist_ok=True)

        if os.path.exists(old_path):
            os.rename(old_path, new_path)

        # Update JSON
        coins = load_json()
        for entry in coins:
            if entry["image"] == image and entry["country"] == old_country:
                entry["country"] = new_country
                break
        save_json(coins)

        return jsonify({"message": f"Country updated to {new_country} and file moved."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/filter-json', methods=['POST'])
def filter_json():
    try:
        filters = request.get_json()
        data = load_json()
        
        filtered_data = []
        for item in data:
            # Country filter
            if filters.get('country') and filters['country'].lower() not in item.get('country', '').lower():
                continue
                
            # Size filter
            if filters.get('size') and filters['size'].lower() not in item.get('size', '').lower():
                continue
                
            # Year range filter
            year = item.get('year', '')
            if year and year.isdigit():
                year_num = int(year)
                if filters.get('yearFrom') and year_num < int(filters['yearFrom']):
                    continue
                if filters.get('yearTo') and year_num > int(filters['yearTo']):
                    continue
            
            filtered_data.append(item)
            
        return jsonify(filtered_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload-json', methods=['POST'])
def upload_json():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and file.filename.endswith('.json'):
        try:
            data = json.load(file)
            save_json(data)
            return jsonify({"message": "File uploaded and JSON data updated successfully!"})
        except Exception as e:
            return jsonify({"error": f"Error processing JSON file: {str(e)}"}), 400
    else:
        return jsonify({"error": "Invalid file type. Please upload a JSON file."}), 400

# Update the merge-images route to handle different formats
@app.route('/merge-images', methods=['POST'])
def merge_images():
    try:
        # Get the JSON data
        data = request.get_json()
        
        # Get the base64 encoded images and merge direction
        image1_data = data.get('image1')
        image2_data = data.get('image2')
        direction = data.get('direction', 'horizontal')
        country = data.get('country')
        
        if not all([image1_data, image2_data, country]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Remove the data URL prefix if present
        if 'base64,' in image1_data:
            image1_data = image1_data.split('base64,')[1]
        if 'base64,' in image2_data:
            image2_data = image2_data.split('base64,')[1]
        
        # Decode base64 images
        image1 = Image.open(io.BytesIO(base64.b64decode(image1_data)))
        image2 = Image.open(io.BytesIO(base64.b64decode(image2_data)))
        
        # Determine the output format based on input images
        # Prefer PNG for transparency, otherwise use the format of the first image
        output_format = 'PNG'
        
        # Check if either image has transparency
        has_transparency = (
            (image1.mode in ('RGBA', 'LA') or 
             (image1.mode == 'P' and 'transparency' in image1.info)) or
            (image2.mode in ('RGBA', 'LA') or 
             (image2.mode == 'P' and 'transparency' in image2.info))
        )
        
        # If no transparency, use the format of the first image if it's JPEG
        if not has_transparency:
            # Try to get format from the first image
            try:
                if hasattr(image1, 'format') and image1.format:
                    first_format = image1.format.upper()
                    # Use JPEG for JPEG images to maintain quality
                    if first_format == 'JPEG':
                        output_format = 'JPEG'
            except:
                pass  # Fall back to PNG if we can't determine format
        
        # Determine the merge direction and resize images if needed
        if direction == 'horizontal':
            # Resize images to have the same height
            max_height = max(image1.height, image2.height)
            image1 = ImageOps.contain(image1, (image1.width, max_height))
            image2 = ImageOps.contain(image2, (image2.width, max_height))
            
            # Create new image with combined width
            new_width = image1.width + image2.width
            if has_transparency:
                merged_image = Image.new('RGBA', (new_width, max_height))
            else:
                merged_image = Image.new('RGB', (new_width, max_height))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (image1.width, 0))
        else:  # vertical
            # Resize images to have the same width
            max_width = max(image1.width, image2.width)
            image1 = ImageOps.contain(image1, (max_width, image1.height))
            image2 = ImageOps.contain(image2, (max_width, image2.height))
            
            # Create new image with combined height
            new_height = image1.height + image2.height
            if has_transparency:
                merged_image = Image.new('RGBA', (max_width, new_height))
            else:
                merged_image = Image.new('RGB', (max_width, new_height))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (0, image1.height))
        
        # Save the merged image to a bytes buffer
        buffer = io.BytesIO()
        
        # Set appropriate quality and format options
        save_kwargs = {}
        if output_format == 'JPEG':
            save_kwargs['quality'] = 95  # High quality JPEG
            file_ext = 'jpg'
        else:
            # PNG format - preserve transparency
            file_ext = 'png'
            if has_transparency:
                merged_image = merged_image.convert('RGBA')
        
        merged_image.save(buffer, format=output_format, **save_kwargs)
        buffer.seek(0)
        
        # Generate a filename with UUID
        file_uuid = str(uuid.uuid4())
        filename = f"{file_uuid}.{file_ext}"
        country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
        
        # Ensure the country folder exists
        os.makedirs(country_folder, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(country_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        return jsonify({
            "message": "Images merged and saved successfully",
            "filename": filename,
            "filepath": file_path,
            "format": output_format
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)