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
        width: 100%;                     /* full screen width */
        background-color: rgba(40, 167, 69, 0.5); /* ✅ more transparent */
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

    </style>
    
    <style>
.search-options {
    margin-left: 10px;
}

.search-options label {
    color: #fff;
    font-size: 14px;
    display: flex;
    align-items: center;
}

.search-options input[type="checkbox"] {
    margin-right: 5px;
}

.advanced-search-container {
    margin-bottom: 20px;
    padding: 15px;
    background-color: #5a6268;
    border-radius: 4px;
}

.advanced-search-container h3 {
    color: #ffc107;
    margin-bottom: 10px;
    font-size: 16px;
}

.advanced-search-fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 10px;
    align-items: end;
}

.search-field {
    display: flex;
    flex-direction: column;
}

.search-field label {
    color: #fff;
    margin-bottom: 5px;
    font-size: 14px;
}

.search-select {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #fff;
    color: #333;
}

.search-btn {
    padding: 8px 15px;
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.search-btn.clear {
    background-color: #dc3545;
}

.search-btn:hover {
    opacity: 0.9;
}

.filter-indicator {
    margin-top: 10px;
    padding: 8px;
    background-color: #17a2b8;
    border-radius: 4px;
    color: white;
    font-size: 14px;
}

.filter-tag {
    display: inline-block;
    background-color: #6c757d;
    padding: 3px 8px;
    border-radius: 12px;
    margin: 0 5px;
    font-size: 12px;
}

.filter-tag .close {
    margin-left: 5px;
    cursor: pointer;
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
            <button id="clearSearch" class="clear-search-btn" title="Clear search">
                <i class="fas fa-times"></i>
            </button>
            <div class="search-options">
                <label>
                    <input type="checkbox" id="keepFilteredView"> Keep Filtered View
                </label>
            </div>
        </div>

        <div class="advanced-search-container">
            <h3>Advanced Search</h3>
            <div class="advanced-search-fields">
                <div class="search-field">
                    <label for="sizeSearch">Size:</label>
                    <input type="text" id="sizeSearch" class="search-box" placeholder="e.g., 25 or 25x30">
                </div>
                <div class="search-field">
                    <label for="yearSearch">Year:</label>
                    <input type="text" id="yearSearch" class="search-box" placeholder="e.g., 1999 or 2000-2010">
                </div>
                <div class="search-field">
                    <label for="currencyTypeSearch">Currency Type:</label>
                    <select id="currencyTypeSearch" class="search-select">
                        <option value="">All Types</option>
                        <option value="coin">Coin</option>
                        <option value="paper-bill">Paper Bill</option>
                        <option value="antique">Antique</option>
                    </select>
                </div>
                <button id="applyAdvancedSearch" class="search-btn">Apply Advanced Filters</button>
                <button id="clearAdvancedSearch" class="search-btn clear">Clear All Filters</button>
            </div>
        </div>
        
        <div id="filterIndicator" class="filter-indicator" style="display: none;"></div>

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
                    <label for="editYear">Year:</label>
                    <input type="text" id="editYear" name="year">
                </div>
                <div class="form-group">
                    <label for="editSize">Size:</label>
                    <input type="text" id="editSize" name="size">
                </div>
                <div class="form-group">
                    <label for="editDenomination">Denomination:</label>
                    <input type="text" id="editDenomination" name="denomination">
                </div>
                <div class="form-group">
                    <label for="editComposition">Composition:</label>
                    <input type="text" id="editComposition" name="composition">
                </div>
                <div class="form-group">
                    <label for="editDescription">Description:</label>
                    <textarea id="editDescription" name="description"></textarea>
                </div>
                <div class="form-group">
                    <label for="editImageUrl">Image URL:</label>
                    <input type="text" id="editImageUrl" name="image_url">
                </div>
                <button type="button" id="saveChangesBtn" class="save-btn">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
        // Sample data to populate the table
        const sampleData = [
            {
                country: "USA",
                currency_type: "coin",
                year: "2020",
                size: "25mm",
                denomination: "1 Dollar",
                composition: "Silver",
                description: "American Silver Eagle",
                image_url: "https://via.placeholder.com/50?text=USA"
            },
            {
                country: "Canada",
                currency_type: "coin",
                year: "2019",
                size: "28mm",
                denomination: "1 Dollar",
                composition: "Silver",
                description: "Canadian Maple Leaf",
                image_url: "https://via.placeholder.com/50?text=Canada"
            },
            {
                country: "UK",
                currency_type: "paper-bill",
                year: "2018",
                size: "150x75mm",
                denomination: "10 Pounds",
                composition: "Polymer",
                description: "Bank of England Note",
                image_url: "https://via.placeholder.com/50?text=UK"
            },
            {
                country: "Australia",
                currency_type: "coin",
                year: "2021",
                size: "25mm",
                denomination: "1 Dollar",
                composition: "Silver",
                description: "Australian Kangaroo",
                image_url: "https://via.placeholder.com/50?text=Australia"
            },
            {
                country: "Japan",
                currency_type: "coin",
                year: "2017",
                size: "23mm",
                denomination: "100 Yen",
                composition: "Copper-Nickel",
                description: "Japanese Cherry Blossom",
                image_url: "https://via.placeholder.com/50?text=Japan"
            }
        ];

        let jsonData = [...sampleData];
        let currentEditIndex = -1;
        let isFiltered = false;
        let activeFilters = {};

        // Function to populate the table with JSON data
        function populateTable(data) {
            const container = document.getElementById('jsonTableContainer');
            
            if (!data || data.length === 0) {
                container.innerHTML = '<p>No data available</p>';
                return;
            }

            // Create table with headers
            let tableHTML = `
                <div class="row header">
                    <div class="column sortable" data-sort="country">Country</div>
                    <div class="column sortable" data-sort="currency_type">Type</div>
                    <div class="column sortable" data-sort="year">Year</div>
                    <div class="column sortable" data-sort="size">Size</div>
                    <div class="column sortable" data-sort="denomination">Denomination</div>
                    <div class="column sortable" data-sort="composition">Composition</div>
                    <div class="column">Image</div>
                    <div class="column">Actions</div>
                </div>
            `;

            // Add rows for each data item
            data.forEach((item, index) => {
                tableHTML += `
                    <div class="row draggable" draggable="true" data-index="${index}">
                        <div class="column">${item.country || ''}</div>
                        <div class="column">${item.currency_type || ''}</div>
                        <div class="column">${item.year || ''}</div>
                        <div class="column">${item.size || ''}</div>
                        <div class="column">${item.denomination || ''}</div>
                        <div class="column">${item.composition || ''}</div>
                        <div class="column">
                            <img src="${item.image_url || 'https://via.placeholder.com/50?text=No+Image'}" 
                                 alt="Thumbnail" class="thumbnail" 
                                 onclick="openModal('${item.image_url || ''}', ${index})">
                        </div>
                        <div class="column">
                            <span class="delete-btn" onclick="deleteRow(${index})">
                                <i class="fas fa-trash"></i> Delete
                            </span>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = tableHTML;
            
            // Add sorting functionality
            document.querySelectorAll('.sortable').forEach(header => {
                header.addEventListener('click', () => {
                    const field = header.getAttribute('data-sort');
                    sortTable(field);
                });
            });
            
            // Add drag and drop functionality
            setupDragAndDrop();
        }

        // Function to sort the table
        function sortTable(field) {
            jsonData.sort((a, b) => {
                if (a[field] < b[field]) return -1;
                if (a[field] > b[field]) return 1;
                return 0;
            });
            
            // Check if we're in filtered view
            if (isFiltered && document.getElementById('keepFilteredView').checked) {
                // Apply the same filter again after sorting
                applyFilters();
            } else {
                populateTable(jsonData);
            }
        }

        // Function to setup drag and drop
        function setupDragAndDrop() {
            const rows = document.querySelectorAll('.row.draggable');
            const container = document.getElementById('jsonTableContainer');
            
            let draggedItem = null;
            
            rows.forEach(row => {
                // Drag start event
                row.addEventListener('dragstart', function(e) {
                    draggedItem = row;
                    setTimeout(() => {
                        row.style.opacity = '0.5';
                    }, 0);
                });
                
                // Drag end event
                row.addEventListener('dragend', function() {
                    draggedItem = null;
                    setTimeout(() => {
                        row.style.opacity = '1';
                    }, 0);
                });
                
                // Drag over event
                row.addEventListener('dragover', function(e) {
                    e.preventDefault();
                });
                
                // Drag enter event
                row.addEventListener('dragenter', function(e) {
                    e.preventDefault();
                    this.style.backgroundColor = '#495057';
                });
                
                // Drag leave event
                row.addEventListener('dragleave', function() {
                    this.style.backgroundColor = '';
                });
                
                // Drop event
                row.addEventListener('drop', function(e) {
                    e.preventDefault();
                    this.style.backgroundColor = '';
                    
                    if (draggedItem && draggedItem !== this) {
                        // Get the indices of the dragged item and the drop target
                        const fromIndex = parseInt(draggedItem.getAttribute('data-index'));
                        const toIndex = parseInt(this.getAttribute('data-index'));
                        
                        // Rearrange the data array
                        const [movedItem] = jsonData.splice(fromIndex, 1);
                        jsonData.splice(toIndex, 0, movedItem);
                        
                        // Repopulate the table
                        populateTable(jsonData);
                    }
                });
            });
        }

        // Function to open modal with image and form
        function openModal(imageUrl, index) {
            const modal = document.getElementById('imageModal');
            const modalImage = document.getElementById('modalImage');
            const imageFileName = document.getElementById('imageFileName');
            currentEditIndex = index;
            
            // Set image and filename
            modalImage.src = imageUrl || 'https://via.placeholder.com/400?text=No+Image';
            imageFileName.textContent = `Image: ${imageUrl ? imageUrl.split('/').pop() : 'No image available'}`;
            
            // Populate form with current data
            const item = jsonData[index];
            document.getElementById('editCountry').value = item.country || '';
            document.getElementById('editCurrencyType').value = item.currency_type || 'coin';
            document.getElementById('editYear').value = item.year || '';
            document.getElementById('editSize').value = item.size || '';
            document.getElementById('editDenomination').value = item.denomination || '';
            document.getElementById('editComposition').value = item.composition || '';
            document.getElementById('editDescription').value = item.description || '';
            document.getElementById('editImageUrl').value = item.image_url || '';
            
            // Show modal
            modal.style.display = 'flex';
        }

        // Function to close modal
        function closeModal() {
            const modal = document.getElementById('imageModal');
            modal.style.display = 'none';
        }

        // Function to save changes from the modal form
        function saveChanges() {
            if (currentEditIndex === -1) return;
            
            // Get form values
            jsonData[currentEditIndex] = {
                country: document.getElementById('editCountry').value,
                currency_type: document.getElementById('editCurrencyType').value,
                year: document.getElementById('editYear').value,
                size: document.getElementById('editSize').value,
                denomination: document.getElementById('editDenomination').value,
                composition: document.getElementById('editComposition').value,
                description: document.getElementById('editDescription').value,
                image_url: document.getElementById('editImageUrl').value
            };
            
            // Repopulate table
            if (isFiltered && document.getElementById('keepFilteredView').checked) {
                applyFilters();
            } else {
                populateTable(jsonData);
            }
            
            // Show success message
            showToast('Changes saved successfully!');
            
            // Close modal
            closeModal();
        }

        // Function to delete a row
        function deleteRow(index) {
            if (confirm('Are you sure you want to delete this item?')) {
                jsonData.splice(index, 1);
                
                // Repopulate table
                if (isFiltered && document.getElementById('keepFilteredView').checked) {
                    applyFilters();
                } else {
                    populateTable(jsonData);
                }
                
                showToast('Item deleted successfully!');
            }
        }

        // Function to add a new row
        function addNewRow() {
            const newItem = {
                country: "New Country",
                currency_type: "coin",
                year: "2023",
                size: "0mm",
                denomination: "0",
                composition: "",
                description: "New item",
                image_url: "https://via.placeholder.com/50?text=New"
            };
            
            jsonData.push(newItem);
            
            // Repopulate table
            if (isFiltered && document.getElementById('keepFilteredView').checked) {
                applyFilters();
            } else {
                populateTable(jsonData);
            }
            
            // Open modal to edit the new item
            openModal('', jsonData.length - 1);
        }

        // Function to download updated JSON
        function downloadJSON() {
            const dataStr = JSON.stringify(jsonData, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            const exportFileDefaultName = 'data.json';
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
            
            showToast('JSON file downloaded successfully!');
        }

        // Function to handle file upload
        function handleFileUpload(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(event) {
                try {
                    const parsedData = JSON.parse(event.target.result);
                    jsonData = parsedData;
                    isFiltered = false;
                    activeFilters = {};
                    updateFilterIndicator();
                    populateTable(jsonData);
                    showToast('File uploaded successfully!');
                } catch (error) {
                    alert('Error parsing JSON file: ' + error.message);
                }
            };
            reader.readAsText(file);
        }

        // Function to show toast message
        function showToast(message) {
            const toast = document.getElementById('toastMessage');
            toast.textContent = message;
            toast.style.display = 'block';
            toast.style.opacity = '1';
            
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => {
                    toast.style.display = 'none';
                }, 500);
            }, 3000);
        }

        // Function to apply search filters
        function applySearch() {
            const searchTerm = document.getElementById('countrySearch').value.toLowerCase();
            
            if (!searchTerm) {
                // If search term is empty, show all data
                isFiltered = false;
                activeFilters = {};
                updateFilterIndicator();
                populateTable(jsonData);
                return;
            }
            
            const filteredData = jsonData.filter(item => {
                return item.country && item.country.toLowerCase().includes(searchTerm);
            });
            
            isFiltered = true;
            activeFilters.country = searchTerm;
            updateFilterIndicator();
            populateTable(filteredData);
        }

        // Function to apply advanced filters
        function applyAdvancedFilters() {
            const sizeTerm = document.getElementById('sizeSearch').value.toLowerCase();
            const yearTerm = document.getElementById('yearSearch').value.toLowerCase();
            const currencyTypeTerm = document.getElementById('currencyTypeSearch').value;
            
            // If all filters are empty, show all data
            if (!sizeTerm && !yearTerm && !currencyTypeTerm) {
                isFiltered = false;
                activeFilters = {};
                updateFilterIndicator();
                populateTable(jsonData);
                return;
            }
            
            const filteredData = jsonData.filter(item => {
                let match = true;
                
                // Size filter
                if (sizeTerm) {
                    if (item.size) {
                        // Check if it's a range search (e.g., "25x30" or "25-30")
                        if (sizeTerm.includes('x') || sizeTerm.includes('-')) {
                            const sizeParts = item.size.toLowerCase().split(/x|-/);
                            const searchParts = sizeTerm.split(/x|-/);
                            
                            // Check if any part matches
                            match = match && searchParts.some(part => 
                                sizeParts.some(sp => sp.includes(part))
                            );
                        } else {
                            match = match && item.size.toLowerCase().includes(sizeTerm);
                        }
                    } else {
                        match = false;
                    }
                }
                
                // Year filter
                if (yearTerm) {
                    if (item.year) {
                        // Check if it's a range search (e.g., "1990-2000")
                        if (yearTerm.includes('-')) {
                            const [start, end] = yearTerm.split('-').map(y => parseInt(y.trim()));
                            const itemYear = parseInt(item.year);
                            
                            if (!isNaN(start) && !isNaN(end) && !isNaN(itemYear)) {
                                match = match && (itemYear >= start && itemYear <= end);
                            } else {
                                match = match && item.year.toLowerCase().includes(yearTerm);
                            }
                        } else {
                            match = match && item.year.toLowerCase().includes(yearTerm);
                        }
                    } else {
                        match = false;
                    }
                }
                
                // Currency type filter
                if (currencyTypeTerm) {
                    match = match && item.currency_type === currencyTypeTerm;
                }
                
                return match;
            });
            
            isFiltered = true;
            activeFilters = {};
            if (sizeTerm) activeFilters.size = sizeTerm;
            if (yearTerm) activeFilters.year = yearTerm;
            if (currencyTypeTerm) activeFilters.currency_type = currencyTypeTerm;
            
            updateFilterIndicator();
            populateTable(filteredData);
        }

        // Function to update filter indicator
        function updateFilterIndicator() {
            const indicator = document.getElementById('filterIndicator');
            
            if (Object.keys(activeFilters).length === 0) {
                indicator.style.display = 'none';
                return;
            }
            
            let html = 'Active filters: ';
            const filterTags = [];
            
            for (const [key, value] of Object.entries(activeFilters)) {
                filterTags.push(`
                    <span class="filter-tag">
                        ${key}: ${value}
                        <span class="close" onclick="removeFilter('${key}')">&times;</span>
                    </span>
                `);
            }
            
            indicator.innerHTML = html + filterTags.join('');
            indicator.style.display = 'block';
        }

        // Function to remove a specific filter
        function removeFilter(filterKey) {
            delete activeFilters[filterKey];
            
            if (Object.keys(activeFilters).length === 0) {
                // No filters left, show all data
                isFiltered = false;
                populateTable(jsonData);
            } else {
                // Reapply remaining filters
                applyAdvancedFilters();
            }
            
            updateFilterIndicator();
        }

        // Function to clear all filters
        function clearAllFilters() {
            document.getElementById('countrySearch').value = '';
            document.getElementById('sizeSearch').value = '';
            document.getElementById('yearSearch').value = '';
            document.getElementById('currencyTypeSearch').value = '';
            
            isFiltered = false;
            activeFilters = {};
            updateFilterIndicator();
            populateTable(jsonData);
        }

        // Initialize the page
        document.addEventListener('DOMContentLoaded', function() {
            // Populate the table with sample data
            populateTable(jsonData);
            
            // Populate country dropdown
            const countries = ["USA", "Canada", "UK", "Australia", "Japan", "Germany", "France", "Italy", "China", "India"];
            const countryDropdown = document.getElementById('editCountry');
            countries.forEach(country => {
                const option = document.createElement('option');
                option.value = country;
                option.textContent = country;
                countryDropdown.appendChild(option);
            });
            
            // Set up event listeners
            document.getElementById('closeModal').addEventListener('click', closeModal);
            document.getElementById('saveChangesBtn').addEventListener('click', saveChanges);
            document.getElementById('addRowBtn').addEventListener('click', addNewRow);
            document.getElementById('downloadBtn').addEventListener('click', downloadJSON);
            document.getElementById('uploadFileBtn').addEventListener('click', function() {
                document.getElementById('uploadFileInput').click();
            });
            document.getElementById('uploadFileInput').addEventListener('change', handleFileUpload);
            
            // Search functionality
            document.getElementById('countrySearch').addEventListener('input', applySearch);
            document.getElementById('clearSearch').addEventListener('click', function() {
                document.getElementById('countrySearch').value = '';
                applySearch();
            });
            
            // Advanced search functionality
            document.getElementById('applyAdvancedSearch').addEventListener('click', applyAdvancedFilters);
            document.getElementById('clearAdvancedSearch').addEventListener('click', clearAllFilters);
            
            // Close modal when clicking outside
            window.addEventListener('click', function(event) {
                const modal = document.getElementById('imageModal');
                if (event.target === modal) {
                    closeModal();
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

@app.route('/search-json', methods=['POST'])
def search_json():
    try:
        search_criteria = request.get_json()
        data = load_json()
        
        filtered_data = []
        for item in data:
            match = True
            
            # Country search
            if search_criteria.get('country'):
                if search_criteria['country'].lower() not in item.get('country', '').lower():
                    match = False
            
            # Size search
            if match and search_criteria.get('size'):
                if search_criteria['size'].lower() not in item.get('size', '').lower():
                    match = False
            
            # Year search (supports ranges like "2000-2010")
            if match and search_criteria.get('year'):
                year_value = item.get('year', '')
                if search_criteria['year'].find('-') != -1:
                    # Handle year range
                    try:
                        start_year, end_year = map(int, search_criteria['year'].split('-'))
                        item_year = int(year_value) if year_value.isdigit() else None
                        if not item_year or not (start_year <= item_year <= end_year):
                            match = False
                    except:
                        match = False
                else:
                    # Exact year match
                    if search_criteria['year'] not in year_value:
                        match = False
            
            # Currency type search
            if match and search_criteria.get('currency_type'):
                if search_criteria['currency_type'].lower() != item.get('currency_type', '').lower():
                    match = False
            
            if match:
                filtered_data.append(item)
                
        return jsonify(filtered_data)
        
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