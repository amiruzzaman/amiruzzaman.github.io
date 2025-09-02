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
    with file_lock:  # Ensure thread-safe access
        with open(current_json_file_path, 'w') as file:
            json.dump(data, file, indent=2)

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
        }

        .modal-content {
            position: relative;
            width: 80%;
            max-width: 800px;
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #333;
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
                    <input type="text" id="editCountry" name="country">
                </div>
                <div class="form-group">
                    <label for="editCurrencyType">Currency Type:</label>
                    <input type="text" id="editCurrencyType" name="currency_type">
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
        
                const columns = [
                    { content: row.country || "No Country", key: 'country' },
                    { content: row.currency_type || "No Currency Type", key: 'currency_type' },
                    { content: row.donor_name || "No Donor Name", key: 'donor_name' },
                    { content: `<img src="images/${row.country}/${row.image}" alt="Image" class="thumbnail" onerror="this.src='images/placeholder.jpg';" data-index="${index}" />`, key: 'image', isHTML: true },
                    { content: row.note || "No Note", key: 'note' },
                    { content: row.size || "No Size", key: 'size' },
                    { content: row.year || "No Year", key: 'year' }
                ];
        
                columns.forEach(col => {
                    const columnDiv = document.createElement('div');
                    columnDiv.classList.add('column', 'editable');
                    if (col.isHTML) {
                        columnDiv.innerHTML = col.content;
                    } else {
                        columnDiv.contentEditable = true;
                        columnDiv.textContent = col.content;
                        columnDiv.addEventListener('blur', () => {
                            row[col.key] = columnDiv.textContent;
                            saveUpdates();
                        });
                    }
                    rowDiv.appendChild(columnDiv);
                });
        
                const actionDiv = document.createElement('div');
                actionDiv.classList.add('column');
                const deleteBtn = document.createElement('span');
                deleteBtn.classList.add('delete-btn');
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                deleteBtn.addEventListener('click', () => {
                    jsonData.splice(index, 1);
                    renderTable(jsonData);
                    saveUpdates();
                });
                actionDiv.appendChild(deleteBtn);
                rowDiv.appendChild(actionDiv);
        
                tableContainer.appendChild(rowDiv);
            });
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

        fetch('/get-json')
            .then(response => response.json())
            .then(data => {
                jsonData = data;
                renderTable(jsonData);
            });

        document.getElementById("addRowBtn").addEventListener("click", function () {
            const newRow = {
                country: "New Country",
                currency_type: "New Currency Type",
                donor_name: "New Donor",
                image: "placeholder.jpg",
                note: "Add a note",
                size: "",
                year: ""
            };
            jsonData.push(newRow);
            renderTable(jsonData);
            saveUpdates();
        });

        document.getElementById("downloadBtn").addEventListener('click', () => {
            const dataStr = JSON.stringify(jsonData, null, 2);
            const blob = new Blob([dataStr], { type: 'application/json' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'data.json';
            link.click();
        });

        const modal = document.getElementById("imageModal");
        const modalImage = document.getElementById("modalImage");
        const closeModal = document.getElementById("closeModal");
        const imageFileName = document.getElementById("imageFileName");
        const saveChangesBtn = document.getElementById("saveChangesBtn");

        document.addEventListener("click", (e) => {
            if (e.target.classList.contains("thumbnail")) {
                const imageSrc = e.target.src;
                const fileName = imageSrc.split('/').pop();
                const index = parseInt(e.target.getAttribute('data-index'));
                
                currentEditingIndex = index;
                const rowData = jsonData[index];

                // Set the image source and file name in the modal
                modalImage.src = imageSrc;
                imageFileName.textContent = fileName;

                // Fill the form with current data
                document.getElementById("editCountry").value = rowData.country || "";
                document.getElementById("editCurrencyType").value = rowData.currency_type || "";
                document.getElementById("editDonorName").value = rowData.donor_name || "";
                document.getElementById("editNote").value = rowData.note || "";
                document.getElementById("editSize").value = rowData.size || "";
                document.getElementById("editYear").value = rowData.year || "";

                modal.style.display = "flex";
            }
        });

        saveChangesBtn.addEventListener("click", function() {
            if (currentEditingIndex >= 0) {
                // Update the data with form values
                jsonData[currentEditingIndex].country = document.getElementById("editCountry").value;
                jsonData[currentEditingIndex].currency_type = document.getElementById("editCurrencyType").value;
                jsonData[currentEditingIndex].donor_name = document.getElementById("editDonorName").value;
                jsonData[currentEditingIndex].note = document.getElementById("editNote").value;
                jsonData[currentEditingIndex].size = document.getElementById("editSize").value;
                jsonData[currentEditingIndex].year = document.getElementById("editYear").value;

                // Save updates
                saveUpdates();
                
                // Refresh the table
                renderTable(jsonData);
                
                // Close the modal
                modal.style.display = "none";
                
                alert("Changes saved successfully!");
            }
        });

        closeModal.addEventListener("click", () => {
            modal.style.display = "none";
        });

        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.style.display = "none";
            }
        });
    </script>
</body>
</html>
'''

# API to get JSON data
@app.route('/get-json', methods=['GET'])
def get_json():
    return jsonify(load_json())

# API to update JSON data
@app.route('/update-json', methods=['POST'])
def update_json():
    try:
        updated_data = request.json
        if not isinstance(updated_data, list):  # Ensure it's a list of items
            return jsonify({"error": "Invalid JSON structure. Must be a list."}), 400
        save_json(updated_data)
        return jsonify({"message": "JSON updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update JSON: {str(e)}"}), 500

# Upload and set a new JSON file
@app.route('/upload-json', methods=['POST'])
def upload_json():
    global current_json_file_path
    if 'file' not in request.files:
        return jsonify({"error": "No file provided!"}), 400

    file = request.files['file']

    if not file.filename.endswith('.json'):
        return jsonify({"error": "Invalid file format. Only JSON files are allowed."}), 400

    upload_folder = 'uploads'
    os.makedirs(upload_folder, exist_ok=True)
    upload_path = os.path.join(upload_folder, file.filename)
    try:
        file.save(upload_path)
        current_json_file_path = upload_path  # Update the current file path
        return jsonify({"message": f"File uploaded and set to: {current_json_file_path}"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to upload file: {str(e)}"}), 500

# Merge images functionality
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/merge-images', methods=['GET', 'POST'])
def merge_images():
    if request.method == 'GET':
        logger.info("Rendering the merge images page.")
        return render_template('merge_images.html')

    try:
        logger.info("Processing image merge request.")
        
        # Retrieve the uploaded files
        image1_file = request.files['image1']
        image2_file = request.files['image2']
        merge_type = request.form['mergeType']
        format = request.form['format']  # JPG, PNG, BMP, WebP, etc.
        filename = request.form.get('filename', 'merged_image')

        logger.info(f"Received images: {image1_file.filename}, {image2_file.filename}")
        logger.info(f"Merge type: {merge_type}, Output format: {format}, Filename: {filename}")

        # Open images using PIL
        image1 = Image.open(image1_file)
        image2 = Image.open(image2_file)

        # Ensure the images are compatible for WebP or other formats
        image1 = image1.convert('RGBA') if format.upper() == 'WEBP' else image1.convert('RGB')
        image2 = image2.convert('RGBA') if format.upper() == 'WEBP' else image2.convert('RGB')

        # Resize images to the same width or height for merging
        if merge_type == 'vertical':
            new_width = max(image1.width, image2.width)
            total_height = image1.height + image2.height
            merged_image = Image.new('RGBA' if format.upper() == 'WEBP' else 'RGB', 
                                     (new_width, total_height), (255, 255, 255, 0))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (0, image1.height))
        elif merge_type == 'horizontal':
            total_width = image1.width + image2.width
            new_height = max(image1.height, image2.height)
            merged_image = Image.new('RGBA' if format.upper() == 'WEBP' else 'RGB', 
                                     (total_width, new_height), (255, 255, 255, 0))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (image1.width, 0))

        # Handle JPG format conversion for PIL compatibility
        if format.upper() == 'JPG':
            format = 'JPEG'

        # Save the image to a BytesIO buffer in the requested format
        image_io = io.BytesIO()
        merged_image.save(image_io, format=format.upper())
        image_io.seek(0)

        # Set the correct content type for the response
        mime_type = f'image/{format.lower()}'
        logger.info(f"Image merged successfully. Returning image in {mime_type} format.")
        return send_file(
            image_io,
            mimetype=mime_type,
            as_attachment=True,
            download_name=f"{filename}.{format.lower()}"
        )
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return {"error": str(e)}, 400

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)