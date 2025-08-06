from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os
import uuid
import json
import requests
from werkzeug.utils import secure_filename
from flask_cors import CORS
from PIL import Image
import io
import logging
from threading import Lock

app = Flask(__name__)
CORS(app)

# App configuration
app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Paths and file setup
BASE_UPLOAD_FOLDER = './images'
JSON_FILE_PATH = os.path.join(BASE_UPLOAD_FOLDER, 'coins.json')
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

# Ensure the JSON file exists
if not os.path.exists(JSON_FILE_PATH):
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump([], f)

# HTML Template
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="shortcut icon" href="#">
    <title>Donation Form</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #ffc107;
            --secondary-color: #495057;
            --background-color: #72787e;
            --input-bg: #6c757d;
            --success-color: #198754;
            --error-color: #dc3545;
            --text-color: #fff;
            --border-radius: 8px;
            --box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            background-color: var(--secondary-color);
            padding: 30px;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            max-width: 600px;
            width: 100%;
            margin: 20px 0;
            position: relative;
            overflow: visible;
        }

        h2 {
            text-align: center;
            color: var(--primary-color);
            margin-bottom: 25px;
            font-size: 28px;
            position: relative;
            padding-bottom: 10px;
        }

        h2::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 3px;
            background-color: var(--primary-color);
            border-radius: 3px;
        }

        .form-group {
            margin-bottom: 20px;
            position: relative;
        }

        label {
            color: var(--primary-color);
            font-weight: 600;
            margin-bottom: 8px;
            display: block;
        }

        label i {
            margin-right: 8px;
            width: 20px;
            text-align: center;
        }

        input,
        select,
        textarea {
            width: 100%;
            padding: 12px 15px;
            margin-top: 5px;
            border-radius: var(--border-radius);
            border: 1px solid rgba(221, 221, 221, 0.3);
            background-color: var(--input-bg);
            color: var(--text-color);
            font-size: 16px;
            transition: all 0.3s ease;
        }

        input:focus,
        select:focus,
        textarea:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.2);
        }

        input[type="submit"] {
            background-color: var(--success-color);
            color: var(--text-color);
            font-weight: 600;
            cursor: pointer;
            border: none;
            padding: 14px;
            margin-top: 10px;
            transition: background-color 0.3s;
        }

        input[type="submit"]:hover {
            background-color: #157347;
        }

        #image-preview {
            display: none;
            margin-top: 15px;
            text-align: center;
            border: 2px dashed rgba(255, 255, 255, 0.2);
            border-radius: var(--border-radius);
            padding: 10px;
        }

        #image-preview img {
            max-width: 100%;
            max-height: 200px;
            border-radius: var(--border-radius);
            object-fit: contain;
        }

        #message-container {
            margin-top: 25px;
            padding: 15px;
            border-radius: var(--border-radius);
            background-color: rgba(0, 0, 0, 0.2);
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .success-message {
            color: #d4edda;
            background-color: rgba(25, 135, 84, 0.2);
            border-left: 4px solid var(--success-color);
        }

        .error-message {
            color: #f8d7da;
            background-color: rgba(220, 53, 69, 0.2);
            border-left: 4px solid var(--error-color);
        }

        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
        }

        .file-input-button {
            border: 1px solid rgba(221, 221, 221, 0.3);
            border-radius: var(--border-radius);
            padding: 10px 15px;
            background-color: var(--input-bg);
            color: var(--text-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
        }

        .file-input-button i {
            margin-left: 8px;
        }

        #file-input {
            position: absolute;
            left: 0;
            top: 0;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        .preview-placeholder {
            color: rgba(255, 255, 255, 0.6);
            font-style: italic;
            text-align: center;
            padding: 20px;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }

            h2 {
                font-size: 24px;
            }

            input,
            select,
            textarea {
                padding: 10px 12px;
            }
        }
    </style>
</head>

<body>
    <div class="container">
        <h2><i class="fas fa-hand-holding-heart"></i> Donation Form</h2>
        <form id="donation-form">
            <div class="form-group">
                <label for="donor-name"><i class="fas fa-user"></i> Donor Name</label>
                <input type="text" id="donor-name" name="donor-name" placeholder="Enter your name" required>
            </div>
            <div class="form-group">
                <label for="country"><i class="fas fa-globe"></i> Country</label>
                <select id="country" name="country" required>
                    <option value="" disabled selected>Select a country</option>
                </select>
            </div>
            <div class="form-group">
                <label><i class="fas fa-file-upload"></i> File Upload</label>
                <div class="file-input-wrapper">
                    <div class="file-input-button">
                        <span id="file-input-label">Choose a file</span>
                        <i class="fas fa-cloud-upload-alt"></i>
                    </div>
                    <input type="file" id="file-input" name="file">
                </div>
                <div id="image-preview">
                    <img id="preview-img" alt="Preview">
                </div>
            </div>
            <div class="form-group">
                <label for="file-url"><i class="fas fa-link"></i> File URL</label>
                <input type="url" id="file-url" name="file-url" placeholder="Enter file URL (optional)">
            </div>
            <div class="form-group">
                <label for="currency-type"><i class="fas fa-money-bill-wave"></i> Type of Currency</label>
                <select id="currency-type" name="currency-type" required>
                    <option value="" disabled selected>Select currency type</option>
                    <option value="paper-bill">Paper Bill</option>
                    <option value="coin">Coin</option>
                    <option value="antique">Antique</option>
                </select>
            </div>
            <div class="form-group">
                <label for="note"><i class="fas fa-comment"></i> Note</label>
                <textarea id="note" name="note" rows="4" placeholder="Add any additional information..."
                    required></textarea>
            </div>
            <input type="submit" value="Submit Donation">
        </form>
        <div id="message-container"></div>
    </div>

    <script>
        // Load country options dynamically
        function loadCountries() {
            fetch('/static/countries.json')
                .then(response => response.json())
                .then(data => {
                    const countrySelect = document.getElementById('country');
                    const currentSelection = countrySelect.value;
                    countrySelect.innerHTML = '<option value="" disabled selected>Select a country</option>';
                    data.forEach(country => {
                        const option = document.createElement('option');
                        option.value = country.name;
                        option.textContent = country.name;
                        if (country.name === currentSelection) {
                            option.selected = true;
                        }
                        countrySelect.appendChild(option);
                    });
                })
                .catch(error => console.error('Error loading countries:', error));
        }

        // Clear information when a new country is selected
        document.getElementById('country').addEventListener('change', () => {
            const selectedCountry = document.getElementById('country').value;
            document.getElementById('donation-form').reset();
            document.getElementById('image-preview').style.display = 'none';
            document.getElementById('message-container').innerHTML = '';
            document.getElementById('country').value = selectedCountry;
        });

        // Preview selected image and update file input label
        document.getElementById('file-input').addEventListener('change', function () {
            const preview = document.getElementById('image-preview');
            const previewImg = document.getElementById('preview-img');
            const fileLabel = document.getElementById('file-input-label');

            const file = this.files[0];
            if (file) {
                fileLabel.textContent = file.name;
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewImg.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            } else {
                fileLabel.textContent = 'Choose a file';
                preview.style.display = 'none';
            }
        });

        // Handle form submission
        document.getElementById('donation-form').addEventListener('submit', function (event) {
            event.preventDefault();

            const donorName = document.getElementById('donor-name').value;
            const fileInput = document.getElementById('file-input');
            const fileUrlInput = document.getElementById('file-url');
            const country = document.getElementById('country').value;
            const currencyType = document.getElementById('currency-type').value;
            const note = document.getElementById('note').value;

            const formData = new FormData();

            // Check if a file is provided via local upload
            if (fileInput.files.length > 0) {
                formData.append('file', fileInput.files[0]);
            }

            // Check if a file is provided via URL
            const fileUrlValue = fileUrlInput.value.trim();
            if (fileUrlValue) {
                formData.append('file-url', fileUrlValue);
            }

            // Add other form fields
            formData.append('donor-name', donorName);
            formData.append('country', country);
            formData.append('currency-type', currencyType);
            formData.append('note', note);

            // Ensure at least one file input is provided
            if (!fileInput.files.length && !fileUrlValue) {
                showMessage('Please provide either a file or a valid URL.', 'error');
                return;
            }

            fetch('/upload', {
                method: 'POST',
                body: formData,
            })
                .then((response) => response.json())
                .then((result) => {
                    if (result.message == 'Error fetching the file from URL!') {
                        showMessage(`
                            ${result.message}<br><br>
                            <strong>Donor Name:</strong> ${result['donor_name']}<br>
                            <strong>Country:</strong> ${result.country}<br>
                            <strong>Currency Type:</strong> ${result['currency_type']}<br>
                            <strong>Note:</strong> ${result.note}<br>
                            <strong>File Path:</strong> ${result.file_path}
                        `, 'error');
                    } else {
                        showMessage(`
                            <p>${result.message}</p>
                            <p><strong>Donor Name:</strong> ${result.donor_name}</p>
                            <p><strong>Country:</strong> ${result.country}</p>
                            <p><strong>Currency Type:</strong> ${result.currency_type}</p>
                            <p><strong>Note:</strong> ${result.note}</p>
                            <div style="margin-top: 15px; text-align: center;">
                                <img src="${result.file_path}" alt="Uploaded Image" style="max-width: 100%; border-radius: 8px;">
                            </div>
                        `, 'success');
                    }
                })
                .catch((error) => {
                    showMessage(`Error: ${error.message}`, 'error');
                });
        });

        // Helper function to show messages
        function showMessage(content, type) {
            const messageContainer = document.getElementById('message-container');
            messageContainer.innerHTML = `
                <div class="${type}-message">
                    ${content}
                </div>
            `;

            // Scroll to the message container smoothly
            messageContainer.scrollIntoView({ behavior: 'smooth' });
        }

        // Initialize the countries when the page loads
        window.addEventListener('DOMContentLoaded', loadCountries);
    </script>
</body>

</html>
"""

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

def update_json_file(country, image, note, donor_name, currency_type):
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
        "currency_type": currency_type
    })

    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def upload_form():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    country = request.form.get('country')
    note = request.form.get('note')
    donor_name = request.form.get('donor-name')
    currency_type = request.form.get('currency-type')

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
            update_json_file(country, file_name, note, donor_name, currency_type)  # Update the JSON file
            return jsonify({
                "message": "File uploaded successfully!",
                "country": country,
                "note": note,
                "donor_name": donor_name,
                "currency_type": currency_type,
                "file_path": file_path
            })
        except Exception as e:
            return jsonify({"message": "Error saving file!", "error": str(e)}), 500

    # Handle file upload via URL
    if file_url:
        try:
            file_path, file_name = download_file_from_url(file_url, country)
            update_json_file(country, file_name, note, donor_name, currency_type)  # Update the JSON file
            return jsonify({
                "message": "File fetched and saved successfully!",
                "country": country,
                "note": note,
                "donor_name": donor_name,
                "currency_type": currency_type,
                "file_path": file_path
            })
        except requests.RequestException as e:
            return jsonify({"message": "Error fetching the file from URL!", "error": str(e)}), 400

    return jsonify({"message": "No file or URL provided!"}), 400

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)