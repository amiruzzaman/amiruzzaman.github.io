import webbrowser
from flask import Flask, request, jsonify, render_template_string, send_from_directory, session, redirect, url_for
import os
import uuid
import json
import requests
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from PIL import Image
import io
import logging
from threading import Lock
import shutil

# Create a Flask application instance
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

# Create a lock for thread-safe file operations
file_lock = Lock()

# --- USER MANAGEMENT ---
# Hash the password "coins" for secure storage
hashed_password = generate_password_hash("coins")
print(hashed_password);

def is_authenticated():
    """Checks if the user is authenticated."""
    return 'logged_in' in session and session['logged_in']

# --- HTML Templates ---
LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #1a202c;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background-color: #2d3748;
            border-radius: 1rem;
            padding: 2.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            max-width: 400px;
            width: 90%;
            text-align: center;
        }
        .input-field {
            width: 100%;
            padding: 0.75rem 1rem;
            background-color: #4a5568;
            border: 1px solid #718096;
            border-radius: 0.5rem;
            color: #e2e8f0;
            outline: none;
            transition: all 0.2s ease-in-out;
        }
        .input-field:focus {
            border-color: #63b3ed;
            box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.5);
        }
        .submit-btn {
            width: 100%;
            padding: 0.75rem 1rem;
            background-color: #38b2ac;
            color: white;
            font-weight: 600;
            border-radius: 0.5rem;
            transition: background-color 0.2s;
        }
        .submit-btn:hover {
            background-color: #319795;
        }
    </style>
</head>

<body>
    <div class="container">
        <h2 class="text-3xl font-bold mb-6 text-teal-300">Login</h2>
        <form id="login-form" class="space-y-4">
            <input type="text" id="username" name="username" placeholder="Username" class="input-field" required>
            <input type="password" id="password" name="password" placeholder="Password" class="input-field" required>
            <button type="submit" class="submit-btn">Login</button>
        </form>
        <div id="message" class="mt-4 text-sm font-semibold text-red-400"></div>
    </div>

    <script>
        document.getElementById('login-form').addEventListener('submit', async function(event) {
            event.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const messageElement = document.getElementById('message');

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const result = await response.json();
                if (response.ok) {
                    window.location.href = '/upload_form';
                } else {
                    messageElement.textContent = result.message;
                }
            } catch (error) {
                messageElement.textContent = 'An error occurred. Please try again.';
            }
        });
    </script>
</body>

</html>
"""

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="shortcut icon" href="#">
    <title>Donation Form</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        body {
            font-family: 'Inter', sans-serif;
            background-color: #1a202c; /* dark slate */
            color: #e2e8f0; /* light gray */
            display: flex;
            justify-content: center;
            min-height: 100vh;
            padding: 2.5rem;
        }

        .drop-zone {
            border: 2px dashed #4a5568; /* dark gray */
            border-radius: 0.5rem;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 1rem;
            background-color: #2d3748; /* dark gray background */
        }

        .drop-zone.hover {
            border-color: #38b2ac; /* teal on hover */
            background-color: #4a5568; /* darker background */
        }
        
        .tab-button.active {
            border-bottom: 2px solid #38b2ac;
        }
    </style>
</head>

<body class="bg-gray-900 text-gray-200">
    <div class="container mx-auto max-w-xl p-8 bg-gray-800 rounded-2xl shadow-2xl mt-10">
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-3xl font-bold text-teal-400">
                <i class="fas fa-hand-holding-heart mr-3"></i> Donation Form
            </h2>
            <button id="logout-btn" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg shadow-lg transition-colors duration-200">
                Logout
            </button>
        </div>
        
        <!-- Tab Navigation -->
        <div class="flex border-b border-gray-600 mb-6">
            <button id="tab-upload" class="tab-button flex-1 py-2 px-4 text-center font-semibold text-gray-400 hover:text-white transition-colors duration-200 active">
                Upload
            </button>
            <button id="tab-replace" class="tab-button flex-1 py-2 px-4 text-center font-semibold text-gray-400 hover:text-white transition-colors duration-200">
                Replace
            </button>
        </div>

        <!-- Tab Content - Upload -->
        <div id="content-upload" class="tab-content space-y-6">
            <form id="donation-form" class="space-y-6">
                <div class="space-y-2">
                    <label for="donor-name" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-user mr-2 text-teal-400"></i> Donor Name
                    </label>
                    <input type="text" id="donor-name" name="donor-name" placeholder="Enter your name" required
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500">
                </div>

                <div class="space-y-2">
                    <label for="country" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-globe mr-2 text-teal-400"></i> Country
                    </label>
                    <select id="country" name="country" required
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500">
                        <option value="" disabled selected>Select a country</option>
                    </select>
                </div>

                <div class="space-y-2">
                    <label class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-file-upload mr-2 text-teal-400"></i> File Upload
                    </label>
                    <div id="drop-zone" class="drop-zone flex flex-col items-center justify-center">
                        <i class="fas fa-image text-4xl text-gray-500 mb-2"></i>
                        <p class="text-sm text-gray-400">Drag & drop an image here or</p>
                        <div class="relative mt-2">
                            <button type="button" class="bg-teal-500 hover:bg-teal-600 text-white font-semibold py-2 px-4 rounded-full transition-colors duration-200">
                                Choose a file
                            </button>
                            <input type="file" id="file-input" name="file" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer">
                        </div>
                    </div>
                    <div id="image-preview" class="hidden mt-4 text-center">
                        <img id="preview-img" alt="Image Preview" class="max-w-full h-auto rounded-lg shadow-lg max-h-64 object-contain mx-auto">
                        <p id="file-name" class="mt-2 text-sm text-gray-400 truncate"></p>
                    </div>
                </div>

                <div class="space-y-2">
                    <label for="file-url" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-link mr-2 text-teal-400"></i> File URL
                    </label>
                    <input type="url" id="file-url" name="file-url" placeholder="Enter file URL (optional)"
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500">
                </div>

                <div class="space-y-2">
                    <label for="currency-type" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-money-bill-wave mr-2 text-teal-400"></i> Type of Currency
                    </label>
                    <select id="currency-type" name="currency-type" required
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500">
                        <option value="" disabled selected>Select currency type</option>
                        <option value="paper-bill">Paper Bill</option>
                        <option value="coin">Coin</option>
                        <option value="antique">Antique</option>
                    </select>
                </div>

                <div class="space-y-2">
                    <label for="note" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-comment mr-2 text-teal-400"></i> Note
                    </label>
                    <textarea id="note" name="note" rows="4" placeholder="Add any additional information..." required
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500"></textarea>
                </div>

                <button type="submit"
                    class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-colors duration-200">
                    Submit Donation
                </button>
            </form>
        </div>

        <!-- Tab Content - Replace -->
        <div id="content-replace" class="tab-content hidden space-y-6">
            <form id="replace-form" class="space-y-6">
                <div class="space-y-2">
                    <label for="old-country" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-flag mr-2 text-teal-400"></i> Existing Country Name
                    </label>
                    <select id="old-country" name="old-country" required
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500">
                        <option value="" disabled selected>Select an existing country</option>
                    </select>
                </div>

                <div class="space-y-2">
                    <label for="new-country" class="block text-sm font-medium text-gray-400">
                        <i class="fas fa-flag mr-2 text-teal-400"></i> New Country Name
                    </label>
                    <select id="new-country" name="new-country" required
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:border-teal-500 focus:ring-teal-500">
                        <option value="" disabled selected>Select a new country</option>
                    </select>
                </div>

                <button type="submit"
                    class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-colors duration-200">
                    Replace
                </button>
            </form>
        </div>

        <div id="message-container" class="mt-8"></div>
    </div>

    <script>
        // Load country options dynamically for both forms
        function loadCountries() {
            fetch('/static/countries.json')
                .then(response => response.json())
                .then(data => {
                    const countrySelects = document.querySelectorAll('#country, #new-country');
                    countrySelects.forEach(select => {
                        const currentSelection = select.value;
                        select.innerHTML = '<option value="" disabled selected>Select a country</option>';
                        data.forEach(country => {
                            const option = document.createElement('option');
                            option.value = country.name;
                            option.textContent = country.name;
                            if (country.name === currentSelection) {
                                option.selected = true;
                            }
                            select.appendChild(option);
                        });
                    });
                })
                .catch(error => console.error('Error loading countries:', error));
        }

        // Load existing countries for the replace form
        function loadExistingCountries() {
            fetch('/api/countries_with_data')
                .then(response => response.json())
                .then(data => {
                    const oldCountrySelect = document.getElementById('old-country');
                    const currentSelection = oldCountrySelect.value;
                    oldCountrySelect.innerHTML = '<option value="" disabled selected>Select an existing country</option>';
                    data.forEach(country => {
                        const option = document.createElement('option');
                        option.value = country;
                        option.textContent = country;
                        if (country === currentSelection) {
                            option.selected = true;
                        }
                        oldCountrySelect.appendChild(option);
                    });
                })
                .catch(error => console.error('Error loading existing countries:', error));
        }
        
        // Clear information when a new country is selected in upload form
        document.getElementById('country').addEventListener('change', () => {
            const selectedCountry = document.getElementById('country').value;
            document.getElementById('donation-form').reset();
            document.getElementById('image-preview').classList.add('hidden');
            document.getElementById('message-container').innerHTML = '';
            document.getElementById('country').value = selectedCountry;
        });

        // ===========================================
        // Drag and Drop & File Preview Logic
        // ===========================================
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const previewContainer = document.getElementById('image-preview');
        const previewImg = document.getElementById('preview-img');
        const fileNameElement = document.getElementById('file-name');

        function handleFiles(files) {
            const file = files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.src = e.target.result;
                    previewContainer.classList.remove('hidden');
                    fileNameElement.textContent = file.name;
                };
                reader.readAsDataURL(file);
                // Assign the file to the input element
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
            } else {
                previewContainer.classList.add('hidden');
                fileInput.value = null; // Clear the input
            }
        }

        // Handle file selection from the file input
        fileInput.addEventListener('change', function () {
            handleFiles(this.files);
        });

        // Drag and drop event listeners
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('hover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('hover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('hover');
            const files = e.dataTransfer.files;
            handleFiles(files);
        });

        // ===========================================
        // Tab Functionality
        // ===========================================
        const tabUpload = document.getElementById('tab-upload');
        const tabReplace = document.getElementById('tab-replace');
        const contentUpload = document.getElementById('content-upload');
        const contentReplace = document.getElementById('content-replace');

        tabUpload.addEventListener('click', () => {
            switchTab('upload');
        });
        tabReplace.addEventListener('click', () => {
            switchTab('replace');
        });

        function switchTab(tab) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));
            
            if (tab === 'upload') {
                tabUpload.classList.add('active');
                contentUpload.classList.remove('hidden');
                document.getElementById('message-container').innerHTML = '';
                loadCountries(); // Reload countries for upload form
            } else {
                tabReplace.classList.add('active');
                contentReplace.classList.remove('hidden');
                document.getElementById('message-container').innerHTML = '';
                loadCountries(); // Reload for new country dropdown
                loadExistingCountries(); // Load countries with data for old country dropdown
            }
        }


        // ===========================================
        // Form Submission Logic
        // ===========================================
        document.getElementById('donation-form').addEventListener('submit', function (event) {
            event.preventDefault();

            const donorName = document.getElementById('donor-name').value;
            const fileUrlInput = document.getElementById('file-url');
            const country = document.getElementById('country').value;
            const currencyType = document.getElementById('currency-type').value;
            const note = document.getElementById('note').value;

            const formData = new FormData();

            // Check if a file is provided via local upload
            const file = fileInput.files[0];
            if (file) {
                formData.append('file', file);
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
            if (!file && !fileUrlValue) {
                showMessage('Please provide either a file or a valid URL.', 'error');
                return;
            }

            fetch('/upload', {
                method: 'POST',
                body: formData,
            })
                .then((response) => response.json())
                .then((result) => {
                    if (result.error) {
                        showMessage(`
                            ${result.message}<br><br>
                            <strong>Donor Name:</strong> ${result['donor_name'] || 'N/A'}<br>
                            <strong>Country:</strong> ${result.country || 'N/A'}<br>
                            <strong>Currency Type:</strong> ${result['currency_type'] || 'N/A'}<br>
                            <strong>Note:</strong> ${result.note || 'N/A'}<br>
                        `, 'error');
                    } else {
                        showMessage(`
                            <p>${result.message}</p>
                            <p><strong>Donor Name:</strong> ${result.donor_name}</p>
                            <p><strong>Country:</strong> ${result.country}</p>
                            <p><strong>Currency Type:</strong> ${result.currency_type}</p>
                            <p><strong>Note:</strong> ${result.note}</p>
                            <div class="mt-4 text-center">
                                <img src="${result.file_path}" alt="Uploaded Image" class="max-w-full h-auto rounded-lg shadow-md max-h-64 object-contain mx-auto">
                            </div>
                        `, 'success');
                    }
                })
                .catch((error) => {
                    showMessage(`Error: ${error.message}`, 'error');
                });
        });

        document.getElementById('replace-form').addEventListener('submit', function(event) {
            event.preventDefault();

            const oldCountry = document.getElementById('old-country').value;
            const newCountry = document.getElementById('new-country').value;

            if (!oldCountry || !newCountry) {
                showMessage('Please select both existing and new country names.', 'error');
                return;
            }

            if (oldCountry === newCountry) {
                showMessage('The new country must be different from the existing country.', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('old_country', oldCountry);
            formData.append('new_country', newCountry);

            fetch('/replace', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(result => {
                if (result.error) {
                    showMessage(result.message, 'error');
                } else {
                    showMessage(result.message, 'success');
                    // Reload the existing countries dropdown after a successful replacement
                    loadExistingCountries();
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, 'error');
            });
        });


        // Helper function to show messages
        function showMessage(content, type) {
            const messageContainer = document.getElementById('message-container');
            const messageClasses = type === 'success' ? 'bg-green-700 text-green-100 p-4 rounded-lg shadow-md' : 'bg-red-700 text-red-100 p-4 rounded-lg shadow-md';
            messageContainer.innerHTML = `
                <div class="${messageClasses}">
                    ${content}
                </div>
            `;
            messageContainer.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Logout functionality
        document.getElementById('logout-btn').addEventListener('click', async () => {
            await fetch('/logout', { method: 'POST' });
            window.location.href = '/';
        });

        // Initialize the countries when the page loads
        window.addEventListener('DOMContentLoaded', () => {
            switchTab('upload');
        });
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
    with file_lock:
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
def home():
    """Serves the index.html page from the base directory."""
    return send_from_directory('.', 'index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        # Check credentials
        if username == 'coin' and check_password_hash(hashed_password, password):
            session['logged_in'] = True
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"message": "Invalid username or password."}), 401

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout', methods=['POST'])
def logout():
    """Logs out the user."""
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/upload_form')
def upload_form():
    """Serves the upload form page, requires authentication."""
    if not is_authenticated():
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file uploads, requires authentication."""
    if not is_authenticated():
        return jsonify({"message": "Unauthorized. Please log in."}), 401

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

@app.route('/replace', methods=['POST'])
def replace_country():
    """
    Handles the replacement of a country name.
    It renames the directory and updates the coins.json file.
    """
    if not is_authenticated():
        return jsonify({"message": "Unauthorized. Please log in."}), 401

    old_country = request.form.get('old_country')
    new_country = request.form.get('new_country')

    if not old_country or not new_country:
        return jsonify({"message": "Both existing and new country names are required."}), 400

    old_folder_path = os.path.join(BASE_UPLOAD_FOLDER, old_country)
    new_folder_path = os.path.join(BASE_UPLOAD_FOLDER, new_country)

    if not os.path.isdir(old_folder_path):
        return jsonify({"message": f"Country folder '{old_country}' not found."}), 404

    # Check if the new folder already exists
    if os.path.isdir(new_folder_path):
        return jsonify({"message": f"A folder for '{new_country}' already exists. Please choose a different name."}), 409

    try:
        # Step 1: Rename the folder
        shutil.move(old_folder_path, new_folder_path)

        # Step 2: Update the JSON file
        with file_lock:
            with open(JSON_FILE_PATH, 'r') as f:
                data = json.load(f)
            
            # Update all entries with the old country name
            for entry in data:
                if entry.get('country') == old_country:
                    entry['country'] = new_country
                    # The image path also needs to be updated to the new directory
                    image_name = entry.get('image')
                    if image_name:
                         #entry['image'] = os.path.join(new_country, os.path.basename(image_name))
                         entry['image'] = os.path.basename(image_name)
                    
            with open(JSON_FILE_PATH, 'w') as f:
                json.dump(data, f, indent=4)
        
        return jsonify({"message": f"Successfully replaced '{old_country}' with '{new_country}'."})

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}", "error": True}), 500

@app.route('/api/countries_with_data')
def api_countries_with_data():
    """
    Returns a list of unique country names that have at least one coin entry.
    """
    if not is_authenticated():
        return jsonify({"message": "Unauthorized. Please log in."}), 401

    try:
        with open(JSON_FILE_PATH, 'r') as f:
            all_coins = json.load(f)
        
        # Get unique country names from the JSON data
        countries = sorted(list(set(coin.get('country') for coin in all_coins if 'country' in coin)))
        return jsonify(countries)
    except FileNotFoundError:
        return jsonify({"error": "Coin data file not found"}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/display.html')
def display_coins():
    """
    Serves the display.html page.
    """
    return send_from_directory('.', 'display.html')

@app.route('/api/coins')
def api_coins():
    """
    Returns coin data as JSON for a given country.
    """
    country_name = request.args.get('country')
    if not country_name:
        return jsonify({"error": "Country parameter is missing"}), 400

    try:
        with open(JSON_FILE_PATH, 'r') as f:
            all_coins = json.load(f)
        
        country_coins = [
            coin for coin in all_coins if coin.get('country') == country_name
        ]
        return jsonify(country_coins)
    except FileNotFoundError:
        return jsonify({"error": "Coin data file not found"}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/images/<path:filename>')
def serve_images(filename):
    """Serves images from the 'images' folder."""
    return send_from_directory('images', filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serves static files, like countries.json, from a 'static' folder."""
    return send_from_directory('static', filename)

@app.route('/geojson/<path:filename>')
def serve_geojson(filename):
    """Serves GeoJSON files from the 'geojson' folder."""
    return send_from_directory('geojson', filename)

@app.route('/countries.json')
def serve_countries_json():
    """Serves the countries.json file from the root directory."""
    return send_from_directory('.', 'countries.json')

@app.route('/countries.continents.json')
def serve_countries_continents_json():
    """Serves the countries.continents.json file from the root directory."""
    return send_from_directory('.', 'countries.continents.json')
    
@app.route('/<path:filename>')
def serve_root_files(filename):
    """Serves files from the root directory, like continents.geojson."""
    return send_from_directory('.', filename)

if __name__ == "__main__":
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=True)