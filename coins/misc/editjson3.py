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

def update_json_file(country, image, note, donor_name, currency_type, size, year):
    """
    Update the coins.json file with the new entry.
    """
    with open(JSON_FILE_PATH, 'r') as f:
        data = json.load(f)

    # Add the new entry
    data.append({
        "country": country,
        "image": image,
        "note": note,
        "donor_name": donor_name,
        "currency_type": currency_type,
        "size": size,
        "year": year
    })

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
                "note": updated_entry.get("note", entry["note"]).replace('<br>', ''),
                "country": updated_entry.get("country", entry["country"]).replace('<br>', ''),
                "donor_name": updated_entry.get("donor_name", entry["donor_name"]).replace('<br>', ''),
                "currency_type": updated_entry.get("currency_type", entry["currency_type"]).replace('<br>', ''),
                "size": updated_entry.get("size", entry.get("size", "")).replace('<br>', ''),
                "year": updated_entry.get("year", entry.get("year", "")).replace('<br>', '')
            })
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
    country = request.form.get('country')
    note = request.form.get('note')
    donor_name = request.form.get('donor-name')
    currency_type = request.form.get('currency-type')
    size = request.form.get('size', '')
    year = request.form.get('year', '')

    # Validate required fields
    if not country:
        return jsonify({"message": "Country is required!"}), 400
    if not donor_name:
        return jsonify({"message": "Donor name is required!"}), 400
    if not currency_type:
        return jsonify({"message": "Currency type is required!"}), 400

    file = request.files.get('file')
    file_url = request.form.get('file-url')

    # Handle local file upload
    if file:
        try:
            file_path, file_name = save_file(file, country)
            update_json_file(country, file_name, note, donor_name, currency_type, size, year)  # Update the JSON file
            return jsonify({
                "message": "File uploaded successfully!",
                "country": country,
                "note": note,
                "donor_name": donor_name,
                "currency_type": currency_type,
                "size": size,
                "year": year,
                "file_path": file_path
            })
        except Exception as e:
            return jsonify({"message": "Error saving file!", "error": str(e)}), 500

    # Handle file upload via URL
    if file_url:
        try:
            file_path, file_name = download_file_from_url(file_url, country)
            update_json_file(country, file_name, note, donor_name, currency_type, size, year)  # Update the JSON file
            return jsonify({
                "message": "File fetched and saved successfully!",
                "country": country,
                "note": note,
                "donor_name": donor_name,
                "currency_type": currency_type,
                "size": size,
                "year": year,
                "file_path": file_path
            })
        except requests.RequestException as e:
            return jsonify({"message": "Error fetching the file from URL!", "error": str(e)}), 400

    return jsonify({"message": "No file or URL provided!"}), 400

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
    overflow-y: auto;  /* ✅ allow scrolling when needed */
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
    max-height: 90vh;   /* ✅ prevent it from going off screen */
    overflow-y: auto;   /* ✅ scroll inside modal if content too tall */
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

        /* Style the file input trigger (the label) */
        label {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            font-size: 14px;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
        }

        label i {
            margin-right: 8px;
        }

        label:hover {
            background-color: #0056b3;
        }

        /* Style the upload button with an icon */
        #uploadFileBtn {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background-color: #28a745;
            color: white;
            font-size: 14px;
            border-radius: 5px;
            cursor: pointer;
            border: none;
            margin-top: 10px;
        }

        #uploadFileBtn i {
            margin-right: 8px;
        }

        #uploadFileBtn:hover {
            background-color: #218838;
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
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>

<body>
    <div class="container">
        <h1>JSON Viewer & Editor</h1>

        <input type="file" id="jsonFileInput" class="file-input" accept=".json" />

        <label for="uploadFileInput">
            <i class="fas fa-file-upload"></i> Choose File
        </label>
        <input type="file" id="uploadFileInput" accept=".json" />

        <button id="uploadFileBtn">
            <i class="fas fa-upload"></i> Upload File
        </button>

        <div id="jsonTableContainer">Container is here</div>

        <button class="add-row-btn" id="addRowBtn">Add New Row</button>
        <button class="download-btn" id="downloadBtn">Download Updated JSON</button>
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
                    <div class="drop-area" id="imageDropArea">
                        <p>Drag & drop an image here or click to select</p>
                        <input type="file" id="editImageInput" accept="image/*" style="display: none;">
                    </div>
                </div>
                <button type="button" class="save-btn" id="saveChangesBtn">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
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

        document.getElementById("jsonFileInput").addEventListener("change", function (event) {
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
            
            // Clear existing options
            editCountryDropdown.innerHTML = '';
            
            // Add default option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Select a country';
            editCountryDropdown.appendChild(defaultOption);
            
            // Add countries
            countriesData.forEach(country => {
                const option = document.createElement('option');
                option.value = country.name;
                option.textContent = country.name;
                editCountryDropdown.appendChild(option);
            });
        }

        function renderTable(data) {
            const tableContainer = document.getElementById("jsonTableContainer");
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

                //countrySelect.addEventListener('change', function() {
                //    row.country = this.value;
                //    saveUpdates();
                //});

                countrySelect.addEventListener('change', function() {
    const oldCountry = row.country;
    const newCountry = this.value;
    const image = row.image;

    if (!image || image === "placeholder.jpg") {
        // Just update JSON if no real image
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
            this.value = oldCountry; // revert if failed
        } else {
            console.log(data.message);
            row.country = newCountry;
            renderTable(jsonData);
        }
    })
    .catch(error => {
        console.error("Error updating country:", error);
        this.value = oldCountry; // revert if error
    });
});


                
                // Add default option
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Select country';
                countrySelect.appendChild(defaultOption);
                
                // Add countries
                countriesData.forEach(country => {
                    const option = document.createElement('option');
                    option.value = country.name;
                    option.textContent = country.name;
                    if (row.country === country.name) {
                        option.selected = true;
                    }
                    countrySelect.appendChild(option);
                });
                
                // If country is not in the list, add it as an option
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
                
                if (row.image && row.image !== 'placeholder.jpg') {
                    const image = document.createElement('img');
                    image.src = `images/${row.country}/${row.image}`;
                    image.alt = "Image";
                    image.classList.add('thumbnail');
                    image.setAttribute('data-index', index);
                    image.onerror = function() {
                        this.src = 'images/placeholder.jpg';
                    };
                    imageColumn.appendChild(image);
                } else {
                    const dropArea = document.createElement('div');
                    dropArea.classList.add('image-drop-area');
                    dropArea.setAttribute('data-index', index);
                    dropArea.innerHTML = '<p>Drag & drop image here</p>';
                    
                    // Add drag and drop functionality
                    setupImageDropArea(dropArea, row, index);
                    
                    imageColumn.appendChild(dropArea);
                }
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
            
            // Handle file drop
            dropArea.addEventListener('drop', handleDropFile, false);
            
            // Handle file selection
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
                //formData.append('existing_image', row.image);
                // ✅ Add existing image filename if row already has one
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
                        // Update the image in the current row
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

        function saveUpdates() {
            fetch('/update-json', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(jsonData),
            })
                .then(response => response.json())
                .then(data => {
                    console.log(data.message || "File updated.");
                })
                .catch(error => {
                    console.error("Error:", error);
                    alert("An error occurred while updating the file.");
                });
        }

        // Handle image upload via drag and drop in modal
        function setupModalImageUpload() {
            const dropArea = document.getElementById('imageDropArea');
            const fileInput = document.getElementById('editImageInput');
            
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
                
                // ✅ Add existing image filename if editing an existing row
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
                        alert('Image uploaded successfully: ' + data.filename);
                        // Update the image in the current editing row
                        if (currentEditingIndex !== -1) {
                            jsonData[currentEditingIndex].image = data.filename;
                            renderTable(jsonData);
                            saveUpdates();
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error uploading image');
                });
            }
        }

        document.addEventListener("DOMContentLoaded", function () {
            fetch('/get-json')
                .then(response => response.json())
                .then(data => {
                    jsonData = data;
                    renderTable(jsonData);
                })
                .catch(error => {
                    console.error("Error fetching JSON data:", error);
                });

            // Load countries data
            loadCountries();
            
            // Setup image upload functionality
            setupModalImageUpload();
            
            // Setup auto-save for modal fields
            setupModalAutoSave();


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

            function setupModalAutoSave() {
                const fields = [
                    { id: "editCountry", key: "country" },
                    { id: "editCurrencyType", key: "currency_type" },
                    { id: "editDonorName", key: "donor_name" },
                    { id: "editNote", key: "note" },
                    { id: "editSize", key: "size" },
                    { id: "editYear", key: "year" }
                ];

                fields.forEach(field => {
                    const el = document.getElementById(field.id);

                    // For text inputs & textarea → blur event
                    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
                        el.addEventListener("blur", function () {
                            if (currentEditingIndex !== -1) {
                                jsonData[currentEditingIndex][field.key] = this.value;
                                renderTable(jsonData);
                                saveUpdates();
                            }
                        });
                    }

                    // For dropdowns → change event
                    if (el.tagName === "SELECT") {
                        el.addEventListener("change", function () {
                            if (currentEditingIndex !== -1) {
                                jsonData[currentEditingIndex][field.key] = this.value;
                                renderTable(jsonData);
                                saveUpdates();
                            }
                        });
                    }
                });
            }


            document.addEventListener("click", function (event) {
                if (event.target.classList.contains("thumbnail")) {
                    const index = event.target.getAttribute("data-index");
                    const row = jsonData[index];
                    
                    document.getElementById("modalImage").src = `images/${row.country}/${row.image}`;
                    document.getElementById("imageFileName").textContent = row.image;
                    
                    // Populate form fields
                    document.getElementById("editCountry").value = row.country || "";
                    document.getElementById("editCurrencyType").value = row.currency_type || "";
                    document.getElementById("editDonorName").value = row.donor_name || "";
                    document.getElementById("editNote").value = row.note || "";
                    document.getElementById("editSize").value = row.size || "";
                    document.getElementById("editYear").value = row.year || "";
                    
                    currentEditingIndex = index;
                    document.getElementById("imageModal").style.display = "flex";
                }
            });
        });
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)