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

# Add specific CORS headers for the upload route
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# App configuration
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = "upload"

# Paths and file setup
file_name = './images/coins.json'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

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

def save_file(file, country):
    """
    Save the file with a random UUID and structured path.
    """
    try:
        print(f"Attempting to save file for country: {country}")
        print(f"Original filename: {file.filename}")
        
        # Get the file extension
        if '.' in file.filename:
            file_ext = file.filename.rsplit('.', 1)[-1].lower()
        else:
            file_ext = 'jpg'  # Default extension if none provided
        
        file_uuid = str(uuid.uuid4())  # Generate a random UUID
        
        # Ensure the country folder exists
        country_folder = ensure_country_folder_exists(country)
        print(f"Country folder: {country_folder}")
        print(f"Folder exists: {os.path.exists(country_folder)}")
        
        # Create the filename and path
        filename = f"{file_uuid}.{file_ext}"
        file_path = os.path.join(country_folder, filename)
        print(f"Saving file to: {file_path}")
        
        # Check if we have write permissions
        if not os.access(country_folder, os.W_OK):
            print(f"NO WRITE PERMISSION for folder: {country_folder}")
            raise Exception(f"No write permission for folder: {country_folder}")
        
        # Save the file
        file.save(file_path)
        
        # Verify the file was saved
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"File saved successfully: {filename} ({file_size} bytes)")
            return file_path, filename
        else:
            print("File save failed - file doesn't exist after save operation")
            raise Exception("File save failed")
            
    except Exception as e:
        print(f"Error in save_file: {str(e)}")
        raise e
def ensure_country_folder_exists(country):
    """
    Ensure the country folder exists, create it if it doesn't.
    """
    try:
        # Sanitize country name to remove any invalid characters
        import re
        safe_country = re.sub(r'[<>:"/\\|?*]', '', country).strip()
        if not safe_country:
            safe_country = "unknown"
            
        country_folder = os.path.join(BASE_UPLOAD_FOLDER, safe_country)
        print(f"Ensuring folder exists: {country_folder}")
        
        if not os.path.exists(country_folder):
            print(f"Creating folder: {country_folder}")
            os.makedirs(country_folder, exist_ok=True)
            # Set permissions (read, write, execute for owner; read and execute for group/others)
            os.chmod(country_folder, 0o755)
        
        # Verify the folder was created and is writable
        if not os.path.exists(country_folder):
            raise Exception(f"Failed to create folder: {country_folder}")
            
        if not os.access(country_folder, os.W_OK):
            raise Exception(f"Folder is not writable: {country_folder}")
            
        print(f"Folder ready: {country_folder}")
        return country_folder
        
    except Exception as e:
        print(f"Error ensuring folder exists: {str(e)}")
        # Fallback to a default folder if country folder creation fails
        default_folder = os.path.join(BASE_UPLOAD_FOLDER, "default")
        os.makedirs(default_folder, exist_ok=True)
        return default_folder

def update_json_file(country, image, note, donor_name, currency_type, size, year, hidden_note=""):
    """
    Update the coins.json file with the new entry.
    """
    print(f"Updating JSON with entry: {country}, {image}, {donor_name}")
    
    # Ensure the JSON file exists
    if not os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, 'w') as f:
            json.dump([], f)
    
    # Load existing data
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        print(f"Loaded {len(data)} existing entries")
    except (json.JSONDecodeError, FileNotFoundError):
        print("No existing data found, starting fresh")
        data = []

    # Add the new entry
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

    data.append(new_entry)
    print(f"Added new entry: {new_entry}")

    # Save updated data
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"JSON file updated successfully with {len(data)} entries")

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def read_json_file():
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file) if os.stat(file_name).st_size > 0 else []

def write_json_file(data):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

def add_to_json(country, image, note, donor_name, currency_type, size, year, hidden_note=""):
    data = read_json_file()
    new_entry = {
        'country': country.title(),
        'image': image,
        'note': note,
        'donor_name': donor_name,
        'currency_type': currency_type,
        'size': size,
        'year': year
    }
    
    # Add hidden_note if provided
    if hidden_note:
        new_entry["hidden_note"] = hidden_note
        
    data.append(new_entry)
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
        return jsonify({"message": "Server error!", "error": str(e)}), 500

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
    <title>Coin Collection Manager</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }

        body {
            background-color: #f5f5f5;
            color: #333;
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
        }

        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }

        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 5px 5px 0 0;
            margin-right: 5px;
        }

        .tab.active {
            background-color: white;
            border-bottom: 1px solid white;
            margin-bottom: -1px;
            font-weight: bold;
        }

        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #ddd;
            border-top: none;
        }

        .tab-content.active {
            display: block;
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
        .form-group select,
        .form-group textarea {
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

        .drop-area {
            border: 2px dashed #ccc;
            border-radius: 4px;
            padding: 20px;
            text-align: center;
            background-color: #f8f9fa;
            color: #666;
            margin: 10px 0;
            cursor: pointer;
        }

        .drop-area.highlight {
            border-color: #007bff;
            background-color: #e9f0ff;
        }

        .drop-area p {
            margin: 0;
        }

        .btn {
            padding: 10px 15px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }

        .btn-primary {
            background-color: #007bff;
        }

        .btn-success {
            background-color: #28a745;
        }

        .btn-danger {
            background-color: #dc3545;
        }

        .image-preview {
            max-width: 100%;
            max-height: 200px;
            margin-top: 10px;
            display: none;
        }

        .toast-message {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: rgba(40, 167, 69, 0.9);
            color: white;
            padding: 15px;
            border-radius: 4px;
            z-index: 1000;
            display: none;
        }

        .merge-controls {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f8f9fa;
        }

        .merge-drop-area {
            min-height: 100px;
            margin-bottom: 10px;
        }

        .merge-options {
            margin: 15px 0;
        }

        .merge-options label {
            display: inline-block;
            margin-right: 15px;
        }

        #mergePreviewContainer {
            margin-top: 15px;
        }

        .merge-preview {
            padding: 10px;
            border: 1px dashed #007bff;
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

        .collection-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .collection-item {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background-color: #f8f9fa;
        }

        .collection-item img {
            max-width: 100%;
            max-height: 150px;
            display: block;
            margin: 10px auto;
        }

        .search-container {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }

        .search-container input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Coin Collection Manager</h1>
        
        <div class="tabs">
            <div class="tab active" data-tab="upload">Upload Item</div>
            <div class="tab" data-tab="view">View Collection</div>
        </div>
        
        <div class="tab-content active" id="upload-tab">
            <form id="uploadForm">
                <div class="form-group">
                    <label for="country">Country:</label>
                    <select id="country" name="country" required>
                        <option value="">Select a country</option>
                        <!-- Countries will be populated by JavaScript -->
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="currencyType">Currency Type:</label>
                    <select id="currencyType" name="currency_type" required>
                        <option value="coin">Coin</option>
                        <option value="paper-bill">Paper Bill</option>
                        <option value="antique">Antique</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="donorName">Donor Name:</label>
                    <input type="text" id="donorName" name="donor_name" required>
                </div>
                
                <div class="form-group">
                    <label for="note">Note:</label>
                    <textarea id="note" name="note"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="size">Size:</label>
                    <input type="text" id="size" name="size">
                </div>
                
                <div class="form-group">
                    <label for="year">Year:</label>
                    <input type="text" id="year" name="year">
                </div>
                
                <div class="form-group">
                    <label for="hiddenNote">Hidden Note (Optional):</label>
                    <textarea id="hiddenNote" name="hidden_note" placeholder="Not shown publicly"></textarea>
                </div>
                
                <div class="form-group">
                    <label>Image Upload:</label>
                    <div class="drop-area" id="imageDropArea">
                        <p>Drag & drop an image here or click to select</p>
                        <input type="file" id="imageInput" accept="image/*" style="display: none;">
                    </div>
                    <img id="imagePreview" class="image-preview">
                </div>
                
                <div class="merge-controls">
                    <h3>Merge Images (Optional)</h3>
                    <p>Combine two images into one (e.g., front and back of a coin)</p>
                    
                    <div class="image-drop-areas-container">
                        <div class="drop-area merge-drop-area" id="mergeDropArea1">
                            <p>Drag & drop first image here</p>
                        </div>
                        <div class="drop-area merge-drop-area" id="mergeDropArea2">
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
                        
                        <button type="button" id="mergeImagesBtn" class="btn" disabled>Merge Images</button>
                        <button type="button" id="clearMergeBtn" class="btn btn-danger">Clear Merge</button>
                    </div>
                    
                    <div id="mergePreviewContainer" style="display: none;">
                        <div class="merge-preview">
                            <p><strong>Preview:</strong></p>
                            <div id="imagePreviews"></div>
                            <div class="merge-size-info" id="sizeInfo"></div>
                        </div>
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary">Upload Item</button>
            </form>
        </div>
        
        <div class="tab-content" id="view-tab">
            <div class="search-container">
                <input type="text" id="searchInput" placeholder="Search collection...">
                <button id="clearSearch" class="btn">Clear Search</button>
            </div>
            
            <div id="collectionContainer" class="collection-container">
                <!-- Collection items will be displayed here -->
            </div>
        </div>
    </div>
    
    <div id="toastMessage" class="toast-message"></div>

    <script>
        // Global variables
        let uploadedFile = null;
        let mergeImage1 = null;
        let mergeImage2 = null;
        let countriesData = [];
        let collectionData = [];

        // Initialize the application
        //document.addEventListener('DOMContentLoaded', function() {
        //    loadCountries();
        //    setupEventListeners();
        //    loadCollection();
        //});

        // Test connection on page load
        function testConnection() {
            fetch('/test-connection')
                .then(response => response.json())
                .then(data => {
                    console.log('Connection test:', data);
                })
                .catch(error => {
                    console.error('Connection test failed:', error);
                    showToast('Cannot connect to server. Please check if the server is running.', 'error');
                });
        }

        // Call this when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            testConnection();
            loadCountries();
            setupEventListeners();
            loadCollection();
        });

        // Load countries from the server
        function loadCountries() {
            fetch('/get-countries')
                .then(response => response.json())
                .then(data => {
                    countriesData = data;
                    populateCountryDropdown();
                })
                .catch(error => {
                    console.error("Error loading countries:", error);
                    // Fallback to default countries if server fails
                    countriesData = [
                        {name: "United States"},
                        {name: "Canada"},
                        {name: "United Kingdom"},
                        {name: "Germany"},
                        {name: "France"},
                        {name: "Japan"},
                        {name: "China"},
                        {name: "India"},
                        {name: "Australia"},
                        {name: "Mexico"},
                        {name: "Brazil"},
                        {name: "Russia"}
                    ];
                    populateCountryDropdown();
                });
        }

        // Populate the country dropdown
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

        // Set up all event listeners
        function setupEventListeners() {
            // Tab navigation
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', function() {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    
                    this.classList.add('active');
                    document.getElementById(this.dataset.tab + '-tab').classList.add('active');
                    
                    if (this.dataset.tab === 'view') {
                        loadCollection();
                    }
                });
            });
            
            // Image upload handling
            const dropArea = document.getElementById('imageDropArea');
            const fileInput = document.getElementById('imageInput');
            
            // Click to select file
            dropArea.addEventListener('click', () => {
                fileInput.click();
            });
            
            // Drag and drop events
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, preventDefaults, false);
            });
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, highlight, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, unhighlight, false);
            });
            
            // Handle file drop
            dropArea.addEventListener('drop', handleDrop, false);
            
            // Handle file selection
            fileInput.addEventListener('change', handleFileSelect, false);
            
            // Form submission
            document.getElementById('uploadForm').addEventListener('submit', handleFormSubmit);
            
            // Merge images functionality
            setupImageMerging();
            
            // Search functionality
            document.getElementById('searchInput').addEventListener('input', filterCollection);
            document.getElementById('clearSearch').addEventListener('click', clearSearch);
            
            // Clear merge button
            document.getElementById('clearMergeBtn').addEventListener('click', clearMergeAreas);
        }

        // Prevent default behavior for drag and drop
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight drop area
        function highlight() {
            document.getElementById('imageDropArea').classList.add('highlight');
        }

        // Remove highlight from drop area
        function unhighlight() {
            document.getElementById('imageDropArea').classList.remove('highlight');
        }

        // Handle file drop
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }

        // Handle file selection
        function handleFileSelect(e) {
            const files = e.target.files;
            handleFiles(files);
        }

        // Process uploaded files
        function handleFiles(files) {
            if (files.length === 0) return;
            
            const file = files[0];
            if (!file.type.startsWith('image/')) {
                showToast('Please select an image file', 'error');
                return;
            }
            
            uploadedFile = file;
            
            // Display preview
            const reader = new FileReader();
            reader.onload = function(e) {
                const preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
                
                document.getElementById('imageDropArea').innerHTML = 
                    `<p>${file.name} (${Math.round(file.size / 1024)}KB)</p>`;
            };
            reader.readAsDataURL(file);
        }

        // Set up image merging functionality
        function setupImageMerging() {
            const mergeDropArea1 = document.getElementById('mergeDropArea1');
            const mergeDropArea2 = document.getElementById('mergeDropArea2');
            const mergeImagesBtn = document.getElementById('mergeImagesBtn');
            
            // Setup drop areas for merging
            setupMergeDropArea(mergeDropArea1, 1);
            setupMergeDropArea(mergeDropArea2, 2);
            
            // Merge button click handler
            mergeImagesBtn.addEventListener('click', function() {
                if (!mergeImage1 || !mergeImage2) {
                    showToast('Please upload both images first', 'error');
                    return;
                }
                
                const mergeDirection = document.querySelector('input[name="mergeDirection"]:checked').value;
                const resizeOption = document.querySelector('input[name="resizeOption"]:checked').value;
                
                mergeImages(mergeImage1, mergeImage2, mergeDirection, resizeOption)
                    .then(result => {
                        showToast(result.message);
                        
                        // Update the form with the merged image
                        uploadedFile = result.file;
                        document.getElementById('imageDropArea').innerHTML = 
                            `<p>Merged image: ${result.filename}</p>`;
                        document.getElementById('imagePreview').src = URL.createObjectURL(result.file);
                        document.getElementById('imagePreview').style.display = 'block';
                        
                        // Reset merge areas
                        clearMergeAreas();
                    })
                    .catch(error => {
                        console.error('Error merging images:', error);
                        showToast('Error merging images: ' + error.message, 'error');
                    });
            });
        }

        // Set up individual merge drop area
        function setupMergeDropArea(dropArea, imageNumber) {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
            
            // Click to select file
            dropArea.addEventListener('click', () => {
                fileInput.click();
            });
            
            // Drag and drop events
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, preventDefaults, false);
            });
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => {
                    dropArea.classList.add('highlight');
                }, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => {
                    dropArea.classList.remove('highlight');
                }, false);
            });
            
            // Handle file drop
            dropArea.addEventListener('drop', function(e) {
                handleMergeFileDrop(e, imageNumber);
            }, false);
            
            // Handle file selection
            fileInput.addEventListener('change', function(e) {
                handleMergeFileSelect(e, imageNumber);
            });
        }

        // Handle merge file drop
        function handleMergeFileDrop(e, imageNumber) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleMergeFiles(files, imageNumber);
        }

        // Handle merge file selection
        function handleMergeFileSelect(e, imageNumber) {
            const files = e.target.files;
            handleMergeFiles(files, imageNumber);
        }

        // Process merge files
        function handleMergeFiles(files, imageNumber) {
            if (files.length === 0) return;
            
            const file = files[0];
            if (!file.type.startsWith('image/')) {
                showToast('Please select an image file', 'error');
                return;
            }
            
            if (imageNumber === 1) {
                mergeImage1 = file;
            } else {
                mergeImage2 = file;
            }
            
            // Display preview
            const reader = new FileReader();
            reader.onload = function(e) {
                const htmlContent = '<img src="' + e.target.result + '" style="max-width: 100%; max-height: 70px;">' +
                                   '<div style="font-size: 10px; margin-top: 5px;">' +
                                   file.name + '<br>' + file.type + ' (' + Math.round(file.size / 1024) + 'KB)' +
                                   '</div>';
                
                if (imageNumber === 1) {
                    document.getElementById('mergeDropArea1').innerHTML = htmlContent;
                } else {
                    document.getElementById('mergeDropArea2').innerHTML = htmlContent;
                }
                
                // Enable merge button if both images are uploaded
                if (mergeImage1 && mergeImage2) {
                    document.getElementById('mergeImagesBtn').disabled = false;
                    showImagePreviews();
                }
            };
            reader.readAsDataURL(file);
        }

        // Show preview of images to be merged
        function showImagePreviews() {
            const previewContainer = document.getElementById('mergePreviewContainer');
            const imagePreviews = document.getElementById('imagePreviews');
            const sizeInfo = document.getElementById('sizeInfo');
            
            previewContainer.style.display = 'block';
            imagePreviews.innerHTML = '';
            
            const reader1 = new FileReader();
            const reader2 = new FileReader();
            
            reader1.onload = function(e1) {
                reader2.onload = function(e2) {
                    const img1 = new Image();
                    const img2 = new Image();
                    
                    img1.onload = img2.onload = function() {
                        imagePreviews.innerHTML = '<img src="' + e1.target.result + '" title="Image 1: ' + img1.width + '×' + img1.height + '">' +
                                                 '<img src="' + e2.target.result + '" title="Image 2: ' + img2.width + '×' + img2.height + '">';
                        
                        const direction = document.querySelector('input[name="mergeDirection"]:checked').value;
                        const resizeOption = document.querySelector('input[name="resizeOption"]:checked').value;
                        
                        if (resizeOption === 'equal') {
                            if (direction === 'horizontal') {
                                const targetHeight = Math.min(img1.height, img2.height);
                                const width1 = Math.round((targetHeight / img1.height) * img1.width);
                                const width2 = Math.round((targetHeight / img2.height) * img2.width);
                                sizeInfo.textContent = 'Merged size: ' + (width1 + width2) + '×' + targetHeight + ' pixels';
                            } else {
                                const targetWidth = Math.min(img1.width, img2.width);
                                const height1 = Math.round((targetWidth / img1.width) * img1.height);
                                const height2 = Math.round((targetWidth / img2.width) * img2.height);
                                sizeInfo.textContent = 'Merged size: ' + targetWidth + '×' + (height1 + height2) + ' pixels';
                            }
                        } else {
                            if (direction === 'horizontal') {
                                sizeInfo.textContent = 'Merged size: ' + (img1.width + img2.width) + '×' + Math.max(img1.height, img2.height) + ' pixels';
                            } else {
                                sizeInfo.textContent = 'Merged size: ' + Math.max(img1.width, img2.width) + '×' + (img1.height + img2.height) + ' pixels';
                            }
                        }
                    };
                    
                    img1.src = e1.target.result;
                    img2.src = e2.target.result;
                };
                reader2.readAsDataURL(mergeImage2);
            };
            reader1.readAsDataURL(mergeImage1);
        }

        // Merge two images
        function mergeImages(image1, image2, direction, resizeOption) {
            return new Promise((resolve, reject) => {
                const reader1 = new FileReader();
                const reader2 = new FileReader();
                
                reader1.onload = function(e1) {
                    reader2.onload = function(e2) {
                        const img1 = new Image();
                        const img2 = new Image();
                        
                        img1.onload = function() {
                            img2.onload = function() {
                                try {
                                    // Create canvas
                                    const canvas = document.createElement('canvas');
                                    const ctx = canvas.getContext('2d');
                                    
                                    let width1 = img1.width;
                                    let height1 = img1.height;
                                    let width2 = img2.width;
                                    let height2 = img2.height;
                                    
                                    // Resize images if needed
                                    if (resizeOption === 'equal') {
                                        if (direction === 'horizontal') {
                                            // Make both images same height
                                            const targetHeight = Math.min(height1, height2);
                                            width1 = Math.round((targetHeight / height1) * width1);
                                            height1 = targetHeight;
                                            width2 = Math.round((targetHeight / height2) * width2);
                                            height2 = targetHeight;
                                        } else {
                                            // Make both images same width
                                            const targetWidth = Math.min(width1, width2);
                                            height1 = Math.round((targetWidth / width1) * height1);
                                            width1 = targetWidth;
                                            height2 = Math.round((targetWidth / width2) * height2);
                                            width2 = targetWidth;
                                        }
                                    }
                                    
                                    // Set canvas size based on merge direction
                                    if (direction === 'horizontal') {
                                        canvas.width = width1 + width2;
                                        canvas.height = Math.max(height1, height2);
                                    } else {
                                        canvas.width = Math.max(width1, width2);
                                        canvas.height = height1 + height2;
                                    }
                                    
                                    // Draw images on canvas
                                    if (direction === 'horizontal') {
                                        ctx.drawImage(img1, 0, 0, width1, height1);
                                        ctx.drawImage(img2, width1, 0, width2, height2);
                                    } else {
                                        ctx.drawImage(img1, 0, 0, width1, height1);
                                        ctx.drawImage(img2, 0, height1, width2, height2);
                                    }
                                    
                                    // Convert canvas to blob
                                    canvas.toBlob(function(blob) {
                                        const filename = `merged-${Date.now()}.png`;
                                        const file = new File([blob], filename, { type: 'image/png' });
                                        
                                        resolve({
                                            message: 'Images merged successfully',
                                            filename: filename,
                                            file: file
                                        });
                                    }, 'image/png');
                                    
                                } catch (error) {
                                    reject(new Error('Failed to merge images: ' + error.message));
                                }
                            };
                            
                            img2.onerror = function() {
                                reject(new Error('Failed to load second image'));
                            };
                            
                            img2.src = e2.target.result;
                        };
                        
                        img1.onerror = function() {
                            reject(new Error('Failed to load first image'));
                        };
                        
                        img1.src = e1.target.result;
                    };
                    
                    reader2.onerror = function() {
                        reject(new Error('Failed to read second image file'));
                    };
                    
                    reader2.readAsDataURL(image2);
                };
                
                reader1.onerror = function() {
                    reject(new Error('Failed to read first image file'));
                };
                
                reader1.readAsDataURL(image1);
            });
        }

        // Clear merge areas
        function clearMergeAreas() {
            mergeImage1 = null;
            mergeImage2 = null;
            document.getElementById('mergeDropArea1').innerHTML = '<p>Drag & drop first image here</p>';
            document.getElementById('mergeDropArea2').innerHTML = '<p>Drag & drop second image here</p>';
            document.getElementById('mergeImagesBtn').disabled = true;
            document.getElementById('mergePreviewContainer').style.display = 'none';
        }

        
         // Handle form submission
        function handleFormSubmit(e) {
            e.preventDefault();
            
            // Validate form
            const country = document.getElementById('country').value;
            const currencyType = document.getElementById('currencyType').value;
            const donorName = document.getElementById('donorName').value;
            
            if (!country || !currencyType || !donorName) {
                showToast('Please fill in all required fields', 'error');
                return;
            }
            
            if (!uploadedFile) {
                showToast('Please upload an image', 'error');
                return;
            }
            
            // Create FormData object
            const formData = new FormData();
            formData.append('country', country);
            formData.append('currency_type', currencyType);
            formData.append('donor_name', donorName);
            formData.append('note', document.getElementById('note').value);
            formData.append('size', document.getElementById('size').value);
            formData.append('year', document.getElementById('year').value);
            formData.append('hidden_note', document.getElementById('hiddenNote').value);
            formData.append('file', uploadedFile);
            
            // Show loading state
            showToast('Uploading item...');
            
            // Send to server - use absolute URL to avoid CORS issues
            const uploadUrl = window.location.origin + '/upload';
            
            fetch(uploadUrl, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || 'Upload failed') });
                }
                return response.json();
            })
            .then(data => {
                if (data.message) {
                    showToast(data.message);
                    resetForm();
                    loadCollection(); // Reload the collection
                } else {
                    showToast(data.error || 'An error occurred', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error uploading item: ' + error.message, 'error');
            });
        }       

        // Reset the form
        function resetForm() {
            document.getElementById('uploadForm').reset();
            document.getElementById('imagePreview').style.display = 'none';
            document.getElementById('imageDropArea').innerHTML = '<p>Drag & drop an image here or click to select</p>';
            uploadedFile = null;
            clearMergeAreas();
        }

        // Load collection from server
        function loadCollection() {
            fetch('/get-json')
                .then(response => response.json())
                .then(data => {
                    collectionData = data;
                    displayCollection(data);
                })
                .catch(error => {
                    console.error('Error loading collection:', error);
                    showToast('Error loading collection', 'error');
                });
        }

        // Display collection items
        function displayCollection(data) {
            const container = document.getElementById('collectionContainer');
            container.innerHTML = '';
            
            if (data.length === 0) {
                container.innerHTML = '<p>No items in collection yet.</p>';
                return;
            }
            
            data.forEach((item, index) => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'collection-item';
                
                // Create image URL based on country and image filename
                const imageUrl = `images/${item.country}/${item.image}`;
                
                itemDiv.innerHTML = `
                    <h3>${item.country} - ${item.currency_type}</h3>
                    <p><strong>Donor:</strong> ${item.donor_name}</p>
                    <p><strong>Year:</strong> ${item.year || 'N/A'}</p>
                    <p><strong>Size:</strong> ${item.size || 'N/A'}</p>
                    <p><strong>Note:</strong> ${item.note || 'N/A'}</p>
                    <img src="${imageUrl}" alt="${item.country} ${item.currency_type}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZWVlZSIvPjx0ZXh0IHg9IjEwMCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4='">
                    <button class="btn btn-danger" onclick="deleteItem(${index})">Delete</button>
                `;
                container.appendChild(itemDiv);
            });
        }

        // Delete an item from the collection
        function deleteItem(index) {
            if (confirm('Are you sure you want to delete this item?')) {
                const item = collectionData[index];
                
                fetch('/testdelete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(item)
                })
                .then(response => response.json())
                .then(data => {
                    showToast('Item deleted successfully');
                    loadCollection(); // Reload the collection
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error deleting item', 'error');
                });
            }
        }

        // Filter collection based on search input
        function filterCollection() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            if (!searchTerm) {
                displayCollection(collectionData);
                return;
            }
            
            const filteredData = collectionData.filter(item => {
                return (
                    item.country.toLowerCase().includes(searchTerm) ||
                    item.currency_type.toLowerCase().includes(searchTerm) ||
                    item.donor_name.toLowerCase().includes(searchTerm) ||
                    (item.note && item.note.toLowerCase().includes(searchTerm)) ||
                    (item.year && item.year.toLowerCase().includes(searchTerm)) ||
                    (item.size && item.size.toLowerCase().includes(searchTerm))
                );
            });
            
            displayCollection(filteredData);
        }

        // Clear search
        function clearSearch() {
            document.getElementById('searchInput').value = '';
            displayCollection(collectionData);
        }

        // Show toast message
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toastMessage');
            toast.textContent = message;
            toast.style.backgroundColor = type === 'success' ? 'rgba(40, 167, 69, 0.9)' : 'rgba(220, 53, 69, 0.9)';
            toast.style.display = 'block';
            
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }
    </script>
</body>
</html>
    '''

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

@app.route('/test-connection', methods=['GET'])
def test_connection():
    return jsonify({"message": "Connection successful", "status": "ok"})

@app.route('/debug-folders', methods=['GET'])
def debug_folders():
    """
    Debug endpoint to check folder permissions and structure
    """
    try:
        base_folder = BASE_UPLOAD_FOLDER
        debug_info = {
            "base_folder": base_folder,
            "base_exists": os.path.exists(base_folder),
            "base_writable": os.access(base_folder, os.W_OK) if os.path.exists(base_folder) else False,
            "current_working_dir": os.getcwd(),
            "folder_contents": []
        }
        
        if os.path.exists(base_folder):
            for item in os.listdir(base_folder):
                item_path = os.path.join(base_folder, item)
                if os.path.isdir(item_path):
                    debug_info["folder_contents"].append({
                        "name": item,
                        "is_dir": True,
                        "writable": os.access(item_path, os.W_OK),
                        "file_count": len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                    })
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)