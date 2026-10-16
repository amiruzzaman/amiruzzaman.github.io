import os
import uuid
import json
import requests
import logging
import io
import base64
from threading import Lock
from PIL import Image, ImageOps
from flask import Flask, flash, request, redirect, render_template, url_for, session, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS

import re
#import requests
from bs4 import BeautifulSoup

from datetime import datetime
import time

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Add this after your directory definitions
required_dirs = ['images', 'crop', 'static', 'geojson', 'flags/svg', 'style', 'script']
for dir_name in required_dirs:
    os.makedirs(dir_name, exist_ok=True)

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
# COUNTRIES_FILE_PATH = './countries.json'
COUNTRIES_FILE_PATH = 'static/countries.json'
def load_countries():
    if os.path.exists(COUNTRIES_FILE_PATH):
        with open(COUNTRIES_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ============================================================
# ===== MULTI-DONOR SUPPORT HELPERS =====
# ============================================================
def normalize_donors(donor_name, donors=None):
    """
    Normalize donor data into a consistent format.
    Returns (primary_donor_name, donors_list).
    Accepts both legacy single-donor (donor_name string) and
    new multi-donor (donors list) formats.
    """
    # Prefer explicit donors array if provided
    if donors and isinstance(donors, list):
        clean_donors = [d.strip() for d in donors if d and isinstance(d, str) and d.strip()]
        if clean_donors:
            return clean_donors[0], clean_donors
    # Fall back to legacy donor_name
    if donor_name and isinstance(donor_name, str) and donor_name.strip():
        return donor_name.strip(), [donor_name.strip()]
    return "", []

def get_donors_from_entry(entry):
    """
    Extract donors list from a JSON entry.
    Handles both old format (donor_name only) and new format (donors array).
    """
    if entry.get('donors') and isinstance(entry['donors'], list):
        return [d for d in entry['donors'] if d and isinstance(d, str) and d.strip()]
    if entry.get('donor_name') and isinstance(entry['donor_name'], str) and entry['donor_name'].strip():
        return [entry['donor_name'].strip()]
    return []

def get_display_donors(entry):
    """Get comma-separated donor string for display purposes."""
    donors = get_donors_from_entry(entry)
    return ", ".join(donors) if donors else ""

def build_donors_fields(donor_name, donors=None):
    """
    Build the donor-related fields to store in a JSON entry.
    Returns a dict with 'donor_name' and (optionally) 'donors'.
    Single-donor entries only get 'donor_name' to keep files clean.
    """
    primary_donor, donors_list = normalize_donors(donor_name, donors)
    fields = {"donor_name": primary_donor}
    if donors_list and len(donors_list) > 1:
        fields["donors"] = donors_list
    return fields
# ===== END MULTI-DONOR HELPERS =====

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

@app.route('/get-json-stats', methods=['GET'])
def get_json_stats():
    """Get statistics about the JSON data without loading everything"""
    try:
        with file_lock:
            if os.path.exists(current_json_file_path):
                # Get file size without loading entire file
                file_size = os.path.getsize(current_json_file_path)
                
                # Count items efficiently
                with open(current_json_file_path, 'r') as f:
                    data = json.load(f)
                    total_items = len(data)
                
                return jsonify({
                    'total_items': total_items,
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2)
                })
        return jsonify({'total_items': 0, 'file_size_bytes': 0, 'file_size_mb': 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== MULTI-DONOR: update_json_file now accepts donors array =====
def update_json_file(country, image, note, donor_name, currency_type, size, year, hidden_note="", shape="", thickness="", donors=None):
    """
    Update the coins.json file with the new entry.
    Supports multiple donors via the optional `donors` list.
    """
    with open(JSON_FILE_PATH, 'r') as f:
        data = json.load(f)

    # 🔍 Search for an existing "box" attribute for this country
    box_value = None
    for entry in data:
        if entry.get("country") == country and "box" in entry:
            box_value = entry["box"]
            break

    # Normalize donors (handles both single-donor and multi-donor input)
    primary_donor, donors_list = normalize_donors(donor_name, donors)

    # Create the new entry with proper UUID
    new_entry = {
        "id": str(uuid.uuid4()),
        "country": country,
        "image": image if image else "",
        "note": note,
        "donor_name": primary_donor,   # kept for backward compatibility
        "currency_type": currency_type,
        "size": size,
        "year": year,
        "timestamp": datetime.now().isoformat()
    }

    # Only store the donors array when there are 2+ donors
    if donors_list and len(donors_list) > 1:
        new_entry["donors"] = donors_list

    # Add optional fields if they have values
    if shape:
        new_entry["shape"] = shape
    if thickness:
        new_entry["thickness"] = thickness

    # ✅ Add "box" if it was found for the same country
    if box_value is not None:
        new_entry["box"] = box_value

    # Add hidden_note if provided
    if hidden_note:
        new_entry["hidden_note"] = hidden_note

    # Add the new entry
    data.append(new_entry)

    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)
    
    # Invalidate cache
    global json_cache
    json_cache['data'] = None
    json_cache['timestamp'] = 0
# ===== END MULTI-DONOR update_json_file =====

@app.route('/delete-image', methods=['POST'])
def delete_image():
    """Delete an image file from the server"""
    try:
        data = request.get_json()
        country = data.get('country')
        image = data.get('image')
        
        if not country or not image:
            return jsonify({"error": "Missing parameters"}), 400
        
        file_path = os.path.join(BASE_UPLOAD_FOLDER, country, image)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"message": "Image deleted successfully"}), 200
        else:
            return jsonify({"message": "Image file not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-raw-json', methods=['GET'])
def get_raw_json():
    try:
        return jsonify(load_json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_json_file():
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file) if os.stat(file_name).st_size > 0 else []

def write_json_file(data):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

# ===== MULTI-DONOR: add_to_json accepts donors =====
def add_to_json(country, image, note, donor_name, currency_type, size, year, donors=None):
    data = read_json_file()
    primary_donor, donors_list = normalize_donors(donor_name, donors)
    new_entry = {
        'id': os.path.splitext(image)[0],
        'country': country.title(),
        'image': image,
        'note': note,
        'donor_name': primary_donor,
        'currency_type': currency_type,
        'size': size,
        'year': year,
        "timestamp": datetime.now().isoformat()
    }
    if donors_list and len(donors_list) > 1:
        new_entry['donors'] = donors_list
    data.append(new_entry)
    write_json_file(data)
# ===== END MULTI-DONOR add_to_json =====

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

# ===== MULTI-DONOR: update_entry handles donors array =====
def update_entry(updated_entry):
    data = read_json_file()
    
    # 1. 🔍 Look for an existing "box" attribute for this country before updating
    target_country = updated_entry.get("country", "").replace('<br>', '').strip()
    box_value = None
    
    if target_country:
        for entry in data:
            if entry.get("country") == target_country and "box" in entry:
                box_value = entry["box"]
                break

    for entry in data:
        if entry['image'] == updated_entry['row_id']:
            entry.update({
                "id": (os.path.splitext(updated_entry.get("image", entry["image"]))[0]).replace('<br>', '') if updated_entry.get("image", entry["image"]) else entry["id"],
                "image": updated_entry.get("image", entry["image"]).replace('<br>', ''),
                "note": updated_entry.get("note", entry.get("note", "")).replace('<br>', ''),
                "country": updated_entry.get("country", entry["country"]).replace('<br>', ''),
                "donor_name": updated_entry.get("donor_name", entry["donor_name"]).replace('<br>', ''),
                "currency_type": updated_entry.get("currency_type", entry["currency_type"]).replace('<br>', ''),
                "size": updated_entry.get("size", entry.get("size", "")).replace('<br>', ''),
                "year": updated_entry.get("year", entry.get("year", "")).replace('<br>', '')
            })

            # ===== MULTI-DONOR: handle donors array in update =====
            if "donors" in updated_entry and isinstance(updated_entry["donors"], list):
                clean_donors = [d.replace('<br>', '').strip() for d in updated_entry["donors"] if d and str(d).strip()]
                if clean_donors and len(clean_donors) > 1:
                    entry["donors"] = clean_donors
                    entry["donor_name"] = clean_donors[0]  # keep primary in sync
                elif clean_donors and len(clean_donors) == 1:
                    entry["donor_name"] = clean_donors[0]
                    if "donors" in entry:
                        del entry["donors"]
                else:
                    if "donors" in entry:
                        del entry["donors"]
            # ===== END MULTI-DONOR update_entry =====

            # ✅ 2. Conditional "box" attribute handling
            if box_value is not None:
                entry["box"] = box_value
            else:
                # If no box value exists for this country, remove the attribute completely
                if "box" in entry:
                    del entry["box"]

            # Handle hidden_note
            if "hidden_note" in updated_entry:
                entry["hidden_note"] = updated_entry["hidden_note"].replace('<br>', '')
            elif "hidden_note" not in updated_entry and "hidden_note" in entry:
                del entry["hidden_note"]

    write_json_file(data)
# ===== END MULTI-DONOR update_entry =====

# ===== MULTI-DONOR: suggest_donors now scans donors array too =====
@app.route('/suggest-donors', methods=['GET'])
def suggest_donors():
    """
    Endpoint to suggest existing donor names that match a partial query string.
    Searches BOTH the legacy 'donor_name' field and the new 'donors' array.
    """
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    try:
        # Load your existing JSON list
        data = load_json()  # Uses your existing load_json() or read_json_file() function
        
        # Collect unique, non-empty donor names (from both formats)
        unique_donors = set()
        for entry in data:
            for donor in get_donors_from_entry(entry):
                if donor:
                    unique_donors.add(donor)
        
        # Filter names that partly match the user's text query
        matches = [donor for donor in unique_donors if query in donor.lower()]
        
        # Return top 10 matches sorted alphabetically
        return jsonify(sorted(matches)[:10])
        
    except Exception as e:
        print(f"Error fetching donor suggestions: {e}")
        return jsonify([]), 500
# ===== END MULTI-DONOR suggest_donors =====


def delete_entry(entry):
    data = read_json_file()
    updated_data = [item for item in data if item["image"] != entry["image"]]
    file_path = os.path.join(UPLOAD_FOLDER, entry["country"], entry["image"])
    if os.path.exists(file_path):
        os.remove(file_path)
    write_json_file(updated_data)

# Cache for JSON data with TTL (Time To Live)
json_cache = {
    'data': None,
    'timestamp': 0,
    'cache_duration': 30  # Cache for 30 seconds
}

def load_json():
    """Load JSON with caching for better performance"""
    current_time = time.time()
    if (json_cache['data'] is not None and 
        current_time - json_cache['timestamp'] < json_cache['cache_duration']):
        return json_cache['data']
    
    with file_lock:
        if os.path.exists(current_json_file_path):
            with open(current_json_file_path, 'r') as file:
                json_cache['data'] = json.load(file)
                json_cache['timestamp'] = current_time
                return json_cache['data']
    return []

def save_json(data):
    """Save JSON and handle image moves when country changes"""
    with file_lock:
        # Load existing JSON to compare old vs new
        old_data = []
        if os.path.exists(current_json_file_path):
            with open(current_json_file_path, 'r') as f:
                old_data = json.load(f)

        # Map old entries by image filename (skip empty images)
        old_map = {}
        for entry in old_data:
            image = entry.get("image")
            if image and image != "":  # Only map if image exists and not empty
                old_map[image] = entry

        for entry in data:
            image = entry.get("image")
            country = entry.get("country")

            # Skip entries without images or without countries
            if not image or not country or image == "":
                continue

            old_entry = old_map.get(image)
            if old_entry:
                old_country = old_entry.get("country")

                if old_country and old_country != country:
                    old_path = os.path.join(BASE_UPLOAD_FOLDER, old_country, image)
                    new_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
                    new_path = os.path.join(new_folder, image)

                    try:
                        os.makedirs(new_folder, exist_ok=True)
                        if os.path.exists(old_path):
                            os.rename(old_path, new_path)
                            print(f"Moved {image} from {old_country} to {country}")
                    except Exception as e:
                        print(f"Error moving file {image}: {e}")

        # Save updated JSON
        with open(current_json_file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Invalidate cache
        global json_cache
        json_cache['data'] = None
        json_cache['timestamp'] = 0

# Route to serve the ./index.html located in project root
@app.route('/root-index')
def root_index():
    return send_from_directory('.', 'index.html')

# Serve ./display.html
@app.route('/display.html')
def display_html():
    return send_from_directory('.', 'display.html')
    

# Serve ./compare.html
@app.route('/compare.html')
def compare_html():
    return send_from_directory('.', 'compare.html')


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


# Serve CSS files from style directory
@app.route('/style/<path:filename>')
def serve_style_css(filename):
    return send_from_directory('style', filename)

# Serve JavaScript files from style directory
@app.route('/script/<path:filename>')
def serve_script(filename):
    return send_from_directory('script', filename)

# Routes
@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="shortcut icon" href="#">
    <title>Amir's Python Functions Index</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
        href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Roboto:wght@300;400;700&display=swap"
        rel="stylesheet">
    <style>
        :root {
            --primary-color: #007bff;
            --secondary-color: #343a40;
            --background-color: #f0f2f5;
            --card-bg: #ffffff;
            --text-color: #495057;
            --light-text: #f8f9fa;
            --dark-text: #212529;
            --success-color: #28a745;
            --border-radius: 12px;
            --box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
            --hover-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            --transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Roboto', sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), #0056b3);
            padding: 4rem 0;
            text-align: center;
            color: var(--light-text);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            position: relative;
            overflow: hidden;
            margin-bottom: 3rem;
        }

        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.05);
            clip-path: polygon(0 0, 100% 0, 80% 100%, 0% 100%);
            opacity: 0.5;
        }

        h1 {
            font-family: 'Poppins', sans-serif;
            font-size: 3rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }

        .subtitle {
            font-size: 1.3rem;
            font-weight: 300;
            color: rgba(255, 255, 255, 0.9);
        }

        .container {
            flex: 1;
            width: 100%;
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 20px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 30px;
            margin-bottom: 3rem;
        }

        .card {
            background-color: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            overflow: hidden;
            transition: var(--transition);
            border: 1px solid #e9ecef;
        }

        .card:hover {
            transform: translateY(-10px);
            box-shadow: var(--hover-shadow);
        }

        .card-header {
            background: linear-gradient(90deg, var(--secondary-color), #495057);
            color: var(--light-text);
            padding: 1.5rem;
            font-family: 'Poppins', sans-serif;
            font-size: 1.4rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            border-bottom: 4px solid var(--primary-color);
        }

        .card-header i {
            margin-right: 15px;
            font-size: 1.8rem;
        }

        .card-body {
            padding: 2rem;
        }

        .function-list {
            list-style: none;
        }

        .function-item {
            margin-bottom: 1.2rem;
            position: relative;
        }

        .function-item:last-child {
            margin-bottom: 0;
        }

        .function-link {
            display: block;
            color: var(--text-color);
            text-decoration: none;
            font-weight: 500;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            transition: var(--transition);
            background-color: var(--background-color);
            position: relative;
            z-index: 1;
        }

        .function-link::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--primary-color);
            border-radius: 8px;
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.4s ease;
            z-index: -1;
        }

        .function-link:hover::before {
            transform: scaleX(1);
        }

        .function-link:hover {
            color: white;
            transform: translateX(5px);
        }

        .function-link i {
            margin-right: 10px;
            color: var(--primary-color);
            transition: color 0.4s ease;
        }

        .function-link:hover i {
            color: white;
        }

        .footer {
            background: var(--secondary-color);
            color: var(--light-text);
            padding: 2.5rem 0;
            text-align: center;
            margin-top: auto;
        }

        .footer-content {
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }

        .copyright {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.7);
        }

        .social-links {
            display: flex;
            gap: 25px;
        }

        .social-link {
            color: rgba(255, 255, 255, 0.8);
            font-size: 1.5rem;
            transition: color 0.3s ease, transform 0.3s ease;
        }

        .social-link:hover {
            color: var(--primary-color);
            transform: translateY(-3px);
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }

            h1 {
                font-size: 2.5rem;
            }

            .subtitle {
                font-size: 1.1rem;
            }

            .card-header {
                font-size: 1.2rem;
                padding: 1.2rem;
            }

            .card-header i {
                font-size: 1.5rem;
            }

            .card-body {
                padding: 1.5rem;
            }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .card {
            animation: fadeInUp 0.7s cubic-bezier(0.25, 0.8, 0.25, 1) forwards;
            opacity: 0;
        }

        .card:nth-child(1) {
            animation-delay: 0.1s;
        }

        .card:nth-child(2) {
            animation-delay: 0.2s;
        }

        .card:nth-child(3) {
            animation-delay: 0.3s;
        }
    </style>
</head>

<body>
    <header class="header">
        <h1>Python Functions Dashboard</h1>
        <p class="subtitle">A curated collection of robust utilities and tools</p>
    </header>

    <div class="container">
        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-code"></i>
                    JSON Management
                </div>
                <div class="card-body">
                    <ul class="function-list">
                        <li class="function-item">
                            <a href="/edit_json" target="_blank" class="function-link">
                                <i class="fas fa-edit"></i> Edit JSON Data
                            </a>
                        </li>
                        <li class="function-item">
                            <a href="/get-json" target="_blank" class="function-link">
                                <i class="fas fa-eye"></i> View JSON Data (Raw)
                            </a>
                        </li>
                        <li class="function-item">
                            <a href="/upload" target="_blank" class="function-link">
                                <i class="fas fa-upload"></i> Add/Upload Images & Update JSON
                            </a>
                        </li>
                        <li class="function-item">
                            <a href="/upload-form" target="_blank" class="function-link">
                                <i class="fas fa-file-upload"></i> Upload Form
                            </a>
                        </li>
                    </ul>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <i class="fas fa-image"></i>
                    Image Management
                </div>
                <div class="card-body">
                    <ul class="function-list">
                        <li class="function-item">
                            <a href="/manage_image" target="_blank" class="function-link">
                                <i class="fas fa-folder-open"></i> Manage Uploaded Images
                            </a>
                        </li>
                        <li class="function-item">
                            <a href="/merge-images" target="_blank" class="function-link">
                                <i class="fas fa-compress"></i> Merge Images
                            </a>
                        </li>
                        <li class="function-item">
                            <a href="/crop-image" target="_blank" class="function-link">
                                <i class="fas fa-crop-alt"></i> Crop Image
                            </a>
                        </li>
                    </ul>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <i class="fas fa-home"></i>
                    Root Index Page
                </div>
                <div class="card-body">
                    <ul class="function-list">
                        <li class="function-item">
                            <a href="/root-index" target="_blank" class="function-link">
                                <i class="fas fa-external-link-alt"></i> Open Root Index
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer">
        <div class="footer-content">
            <p class="copyright">&copy; 2025 Amiruzzaman. All rights reserved.</p>
            <div class="social-links">
                <a href="#" class="social-link"><i class="fab fa-github"></i></a>
                <a href="#" class="social-link"><i class="fab fa-linkedin"></i></a>
                <a href="#" class="social-link"><i class="fab fa-twitter"></i></a>
            </div>
        </div>
    </footer>
</body>

</html>
    '''
    

# ===== MULTI-DONOR: update_existing_item accepts donors array =====
@app.route('/update-existing-item', methods=['POST'])
def update_existing_item():
    """Update an existing item with full edit capabilities (supports multiple donors)"""
    try:
        # Get form data
        country = request.form.get('country')
        note = request.form.get('note')
        donor_name = request.form.get('donor_name')
        currency_type = request.form.get('currency_type')
        size = request.form.get('size', '')
        year = request.form.get('year', '')
        hidden_note = request.form.get('hidden_note', '')
        item_id = request.form.get('item_id', '')

        # NEW: parse the multi-donor JSON array if provided
        donors_json = request.form.get('donors', '')
        donors = []
        if donors_json:
            try:
                donors = json.loads(donors_json)
                if not isinstance(donors, list):
                    donors = []
            except json.JSONDecodeError:
                donors = []

        print(f"Updating item: ID={item_id}, country={country}, donor={donor_name}, donors={donors}, currency={currency_type}")
        
        # Validate required fields
        if not country:
            return jsonify({"message": "Country is required!"}), 400
        # Accept either a single donor_name or a donors array
        if not donor_name and not donors:
            return jsonify({"message": "At least one donor is required!"}), 400
        if not currency_type:
            return jsonify({"message": "Currency type is required!"}), 400
        if not item_id:
            return jsonify({"message": "Item ID is required!"}), 400
        
        file = request.files.get('file')
        
        # Load existing JSON
        data = load_json()
        
        # Find the entry by ID
        found_entry = None
        entry_index = -1
        for i, entry in enumerate(data):
            if entry.get('id') == item_id:
                found_entry = entry
                entry_index = i
                break
        
        if not found_entry:
            return jsonify({"message": f"Item with ID {item_id} not found!"}), 404
        
        original_image = found_entry.get('image', '')
        original_country = found_entry.get('country', '')
        
        # Handle file upload if provided
        file_name = original_image
        if file and file.filename != '' and allowed_file(file.filename):
            # Delete old image file if it exists and different from new
            if original_image and original_image != 'placeholder.jpg':
                old_file_path = os.path.join(BASE_UPLOAD_FOLDER, original_country, original_image)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        print(f"Deleted old image: {old_file_path}")
                    except Exception as e:
                        print(f"Error deleting old image: {e}")
            
            # Save new file
            file_path, file_name = save_file(file, country)
        
        # Normalize donors
        primary_donor, donors_list = normalize_donors(donor_name, donors)

        # Update the entry basic details
        data[entry_index]['country'] = country
        data[entry_index]['note'] = note
        data[entry_index]['donor_name'] = primary_donor
        data[entry_index]['currency_type'] = currency_type
        data[entry_index]['size'] = size
        data[entry_index]['year'] = year

        # Multi-donor array handling
        if donors_list and len(donors_list) > 1:
            data[entry_index]['donors'] = donors_list
        else:
            # Single donor — remove any stale donors array
            if 'donors' in data[entry_index]:
                del data[entry_index]['donors']
        
        # 🔍 Search for "box" value belonging to the newly specified country
        box_value = None
        for entry in data:
            if entry.get("country") == country and "box" in entry:
                box_value = entry["box"]
                break
        
        # ✅ Apply "box" logic based on search results
        if box_value is not None:
            data[entry_index]["box"] = box_value
        else:
            # If no box value exists for this country anymore, remove it from this object
            if "box" in data[entry_index]:
                del data[entry_index]["box"]

        # Update image if changed
        if file_name and file_name != original_image:
            data[entry_index]['image'] = file_name
        
        # Handle hidden_note
        if hidden_note:
            data[entry_index]['hidden_note'] = hidden_note
        elif 'hidden_note' in data[entry_index]:
            del data[entry_index]['hidden_note']
        
        # If country changed, we need to move the image file
        if country != original_country and file_name and file_name != 'placeholder.jpg':
            old_path = os.path.join(BASE_UPLOAD_FOLDER, original_country, file_name)
            new_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
            new_path = os.path.join(new_folder, file_name)
            
            try:
                os.makedirs(new_folder, exist_ok=True)
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                    print(f"Moved image from {original_country} to {country}")
            except Exception as e:
                print(f"Error moving file: {e}")
        
        # Save the updated JSON
        save_json(data)
        
        # Build response output dictionary dynamically
        response_data = {
            "message": "Item updated successfully!",
            "country": country,
            "note": note,
            "donor_name": primary_donor,
            "donors": donors_list,
            "currency_type": currency_type,
            "size": size,
            "year": year,
            "hidden_note": hidden_note,
            "image": file_name,
            "id": item_id
        }
        if box_value is not None:
            response_data["box"] = box_value
            
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error updating item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Server error!", "error": str(e)}), 500
# ===== END MULTI-DONOR update_existing_item =====


@app.route('/edit-item/<id>')
def edit_item_page(id):
    """Serve the edit item page with pre-loaded data"""
    # Load all data
    all_data = load_json()
    
    # Find the item
    item = None
    for entry in all_data:
        if entry.get('id') == id:
            item = entry
            break
    
    if not item:
        return "Item not found", 404
    
    # Return the edit page with the item data
    return render_edit_item_page(item)

# ===== MULTI-DONOR: render_edit_item_page has multi-donor UI =====
def render_edit_item_page(item):
    """Render the edit item page with pre-filled data (multi-donor support)"""
    # Load countries data for the dropdown
    countries_data = load_countries()
    
    # Create countries options HTML
    countries_options = ''
    for country in countries_data:
        selected = 'selected' if country.get('name') == item.get('country', '') else ''
        countries_options += f'<option value="{country.get("name")}" {selected}>{country.get("name")}</option>'
    
    # Collect existing donors (handles old + new formats)
    existing_donors = get_donors_from_entry(item)
    if not existing_donors:
        existing_donors = ['']
    donors_json = json.dumps(existing_donors)

    # Build initial donor items HTML (so the page renders even before JS boots)
    donor_items_html = ''
    for donor in existing_donors:
        donor_items_html += f'''
        <div class="donor-item">
            <input type="text" class="donor-input" value="{donor}" placeholder="Donor name" list="donor-suggestions">
            <button type="button" class="btn-remove-donor" title="Remove donor"><i class="fas fa-times"></i></button>
        </div>'''
    
    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Item - {item.get('country', 'Unknown')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}

        body {{
            background-color: #f8f9fa;
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }}

        .navigation-buttons {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eaeaea;
        }}

        .nav-btn {{
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .nav-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            background: linear-gradient(135deg, #5a6268 0%, #495057 100%);
            color: white;
            text-decoration: none;
        }}

        .nav-btn i {{
            margin-right: 8px;
        }}

        h1 {{
            text-align: center;
            margin-bottom: 25px;
            color: #2c3e50;
            font-weight: 600;
            font-size: 28px;
        }}

        .form-group {{
            margin-bottom: 20px;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #495057;
        }}

        .form-group input,
        .form-group select,
        .form-group textarea {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 15px;
            transition: border 0.3s;
        }}

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {{
            border-color: #007bff;
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
        }}

        .form-group textarea {{
            height: 80px;
            resize: vertical;
        }}

        /* ===== MULTI-DONOR styles ===== */
        .donors-container {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
        }}
        .donor-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            padding: 8px;
            background-color: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .donor-item:last-child {{ margin-bottom: 0; }}
        .donor-input {{
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .donor-input:focus {{ border-color: #007bff; outline: none; }}
        .btn-remove-donor {{
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
            border: none;
            border-radius: 4px;
            width: 32px;
            height: 32px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .btn-remove-donor:hover {{ background: linear-gradient(135deg, #c82333 0%, #a71e2a 100%); }}
        .btn-add-donor {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
        }}
        .btn-add-donor:hover {{ background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%); }}
        /* ===== END MULTI-DONOR styles ===== */

        .drop-area {{
            border: 2px dashed #ced4da;
            border-radius: 6px;
            padding: 25px;
            text-align: center;
            background-color: #f8f9fa;
            color: #6c757d;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .drop-area.highlight {{
            border-color: #007bff;
            background-color: #e9f0ff;
        }}

        .btn {{
            padding: 12px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            margin-right: 10px;
            transition: all 0.3s;
        }}

        .btn-primary {{
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
        }}

        .btn-primary:hover {{
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
        }}

        .btn-danger {{
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }}

        .btn-danger:hover {{
            background: linear-gradient(135deg, #c82333 0%, #a71e2a 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
        }}

        .image-preview {{
            max-width: 100%;
            max-height: 200px;
            margin-top: 10px;
            border-radius: 6px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}

        .current-image {{
            margin-top: 10px;
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 6px;
            text-align: center;
        }}

        .current-image img {{
            max-width: 100%;
            max-height: 150px;
            border-radius: 4px;
        }}

        .toast-message {{
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: rgba(40, 167, 69, 0.9);
            color: white;
            padding: 15px 20px;
            border-radius: 6px;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}

        .merge-controls {{
            margin-top: 25px;
            padding: 20px;
            border: 1px solid #eaeaea;
            border-radius: 8px;
            background-color: #f8f9fa;
        }}

        .merge-drop-area {{
            min-height: 100px;
            margin-bottom: 10px;
        }}

        .merge-options {{
            margin: 15px 0;
        }}

        .merge-options label {{
            display: inline-block;
            margin-right: 15px;
        }}

        #mergePreviewContainer {{
            margin-top: 15px;
        }}

        .merge-preview {{
            padding: 15px;
            border: 1px dashed #007bff;
            border-radius: 6px;
            background-color: #f8f9fa;
        }}

        .merge-preview img {{
            max-width: 100%;
            max-height: 150px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}

        .merge-size-info {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}

        .image-drop-areas-container {{
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }}

        .footer-buttons {{
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eaeaea;
        }}
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="navigation-buttons">
            <a href="/edit_json" class="nav-btn">
                <i class="fas fa-arrow-left"></i> Back to Editor
            </a>
            <a href="/upload-form" class="nav-btn" target="_blank">
                <i class="fas fa-plus"></i> Add New Item
            </a>
        </div>
        
        <h1><i class="fas fa-edit"></i> Edit Item</h1>
        
        <form id="editForm">
            <input type="hidden" id="itemId" name="item_id" value="{item.get('id', '')}">
            <input type="hidden" id="originalImage" name="original_image" value="{item.get('image', '')}">
            
            <div class="form-group">
                <label for="country">Country:</label>
                <select id="country" name="country" required>
                    <option value="">Select a country</option>
                    {countries_options}
                </select>
            </div>
            
            <div class="form-group">
                <label for="currencyType">Currency Type:</label>
                <select id="currencyType" name="currency_type" required>
                    <option value="coin" {'selected' if item.get('currency_type') == 'coin' else ''}>Coin</option>
                    <option value="paper-bill" {'selected' if item.get('currency_type') == 'paper-bill' else ''}>Paper Bill</option>
                    <option value="antique" {'selected' if item.get('currency_type') == 'antique' else ''}>Antique</option>
                </select>
            </div>
            
            <!-- ===== MULTI-DONOR UI ===== -->
            <div class="form-group">
                <label>Donors:</label>
                <div class="donors-container" id="donorsContainer">
                    {donor_items_html}
                </div>
                <button type="button" class="btn-add-donor" onclick="addDonor()">
                    <i class="fas fa-plus-circle"></i> Add Another Donor
                </button>
                <small style="color: #6c757d; display: block; margin-top: 5px;">
                    <i class="fas fa-info-circle"></i>
                    Add multiple donors if the item was donated by more than one person.
                </small>
            </div>
            <!-- ===== END MULTI-DONOR UI ===== -->
            
            <div class="form-group">
                <label for="note">Note:</label>
                <textarea id="note" name="note">{item.get('note', '')}</textarea>
            </div>
            
            <div class="form-group">
                <label for="size">Size:</label>
                <input type="text" id="size" name="size" value="{item.get('size', '')}">
            </div>
            
            <div class="form-group">
                <label for="year">Year:</label>
                <input type="text" id="year" name="year" value="{item.get('year', '')}">
            </div>
            
            <div class="form-group">
                <label for="hiddenNote">Hidden Note (Optional):</label>
                <textarea id="hiddenNote" name="hidden_note" placeholder="Not shown publicly">{item.get('hidden_note', '')}</textarea>
            </div>
            
            <div class="form-group">
                <label>Current Image:</label>
                <div class="current-image">
                    <img src="/images/{item.get('country', '')}/{item.get('image', '')}" alt="Current image" 
                         onerror="this.src='https://via.placeholder.com/150?text=Image+Not+Found'">
                    <p><small>{item.get('image', '')}</small></p>
                </div>
            </div>
            
            <div class="form-group">
                <label>Replace Image (Optional):</label>
                <div class="drop-area" id="imageDropArea">
                    <p>Drag & drop a new image here or click to select</p>
                    <input type="file" id="imageInput" accept="image/*" style="display: none;">
                </div>
                <img id="imagePreview" class="image-preview" style="display: none;">
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
            
            <div class="footer-buttons">
                <button type="submit" class="btn btn-primary">Save Changes</button>
                <button type="button" class="btn btn-danger" onclick="if(confirm('Are you sure?')) window.location.href='/edit_json'">Cancel</button>
            </div>
        </form>
    </div>
    
    <div id="toastMessage" class="toast-message"></div>
    <datalist id="donor-suggestions"></datalist>

    <script>
        let uploadedFile = null;
        let mergeImage1 = null;
        let mergeImage2 = null;

        // ===== MULTI-DONOR: donorsList state =====
        let donorsList = {donors_json};
        // ===== END MULTI-DONOR =====

        document.addEventListener('DOMContentLoaded', function() {{
            setupEventListeners();
            setupImageMerging();
            renderDonors();  // ===== MULTI-DONOR =====
        }});

        // ===== MULTI-DONOR functions =====
        function renderDonors() {{
            const container = document.getElementById('donorsContainer');
            if (!container) return;
            container.innerHTML = '';
            
            // Guarantee at least one row
            if (donorsList.length === 0) donorsList.push('');
            
            donorsList.forEach((donor, index) => {{
                const div = document.createElement('div');
                div.className = 'donor-item';
                
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'donor-input';
                input.value = donor || '';
                input.placeholder = 'Donor name';
                input.setAttribute('list', 'donor-suggestions');
                input.addEventListener('input', function() {{
                    donorsList[index] = this.value;
                    fetchDonorSuggestions(this.value);
                }});
                
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'btn-remove-donor';
                removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                removeBtn.title = 'Remove donor';
                removeBtn.onclick = function() {{ removeDonor(index); }};
                
                div.appendChild(input);
                div.appendChild(removeBtn);
                container.appendChild(div);
            }});
        }}

        function addDonor() {{
            donorsList.push('');
            renderDonors();
            const inputs = document.querySelectorAll('.donor-input');
            if (inputs.length) inputs[inputs.length - 1].focus();
        }}

        function removeDonor(index) {{
            if (donorsList.length <= 1) {{
                showToast('At least one donor is required', 'error');
                return;
            }}
            donorsList.splice(index, 1);
            renderDonors();
        }}

        function fetchDonorSuggestions(query) {{
            const datalist = document.getElementById('donor-suggestions');
            if (!query || query.trim().length < 2) {{
                datalist.innerHTML = '';
                return;
            }}
            fetch(`/suggest-donors?q=${{encodeURIComponent(query.trim())}}`)
                .then(r => r.json())
                .then(suggestions => {{
                    datalist.innerHTML = '';
                    suggestions.forEach(name => {{
                        const opt = document.createElement('option');
                        opt.value = name;
                        datalist.appendChild(opt);
                    }});
                }})
                .catch(err => console.error('Donor suggestions error:', err));
        }}
        // ===== END MULTI-DONOR functions =====

        function setupEventListeners() {{
            const dropArea = document.getElementById('imageDropArea');
            const fileInput = document.getElementById('imageInput');
            
            dropArea.addEventListener('click', () => fileInput.click());
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                dropArea.addEventListener(eventName, preventDefaults, false);
            }});
            
            ['dragenter', 'dragover'].forEach(eventName => {{
                dropArea.addEventListener(eventName, highlight, false);
            }});
            
            ['dragleave', 'drop'].forEach(eventName => {{
                dropArea.addEventListener(eventName, unhighlight, false);
            }});
            
            dropArea.addEventListener('drop', handleDrop, false);
            fileInput.addEventListener('change', handleFileSelect, false);
            document.getElementById('editForm').addEventListener('submit', handleFormSubmit);
        }}

        function setupImageMerging() {{
            const mergeDropArea1 = document.getElementById('mergeDropArea1');
            const mergeDropArea2 = document.getElementById('mergeDropArea2');
            const mergeImagesBtn = document.getElementById('mergeImagesBtn');
            const clearMergeBtn = document.getElementById('clearMergeBtn');
            
            setupMergeDropArea(mergeDropArea1, 1);
            setupMergeDropArea(mergeDropArea2, 2);
            
            mergeImagesBtn.addEventListener('click', function() {{
                if (!mergeImage1 || !mergeImage2) {{
                    showToast('Please upload both images first', 'error');
                    return;
                }}
                
                const mergeDirection = document.querySelector('input[name="mergeDirection"]:checked').value;
                const resizeOption = document.querySelector('input[name="resizeOption"]:checked').value;
                
                mergeImages(mergeImage1, mergeImage2, mergeDirection, resizeOption)
                    .then(result => {{
                        showToast(result.message);
                        
                        uploadedFile = result.file;
                        document.getElementById('imageDropArea').innerHTML = 
                            `<p>Merged image: ${{result.filename}}</p>`;
                        document.getElementById('imagePreview').src = URL.createObjectURL(result.file);
                        document.getElementById('imagePreview').style.display = 'block';
                        
                        clearMergeAreas();
                    }})
                    .catch(error => {{
                        console.error('Error merging images:', error);
                        showToast('Error merging images: ' + error.message, 'error');
                    }});
            }});
            
            clearMergeBtn.addEventListener('click', clearMergeAreas);
        }}

        function setupMergeDropArea(dropArea, imageNumber) {{
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
            
            dropArea.addEventListener('click', () => fileInput.click());
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                dropArea.addEventListener(eventName, preventDefaults, false);
            }});
            
            ['dragenter', 'dragover'].forEach(eventName => {{
                dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
            }});
            
            ['dragleave', 'drop'].forEach(eventName => {{
                dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
            }});
            
            dropArea.addEventListener('drop', function(e) {{
                handleMergeFileDrop(e, imageNumber);
            }}, false);
            
            fileInput.addEventListener('change', function(e) {{
                handleMergeFileSelect(e, imageNumber);
            }});
        }}

        function handleMergeFileDrop(e, imageNumber) {{
            const dt = e.dataTransfer;
            const files = dt.files;
            handleMergeFiles(files, imageNumber);
        }}

        function handleMergeFileSelect(e, imageNumber) {{
            const files = e.target.files;
            handleMergeFiles(files, imageNumber);
        }}

        function handleMergeFiles(files, imageNumber) {{
            if (files.length === 0) return;
            
            const file = files[0];
            if (!file.type.startsWith('image/')) {{
                showToast('Please select an image file', 'error');
                return;
            }}
            
            if (imageNumber === 1) {{
                mergeImage1 = file;
            }} else {{
                mergeImage2 = file;
            }}
            
            const reader = new FileReader();
            reader.onload = function(e) {{
                const htmlContent = '<img src="' + e.target.result + '" style="max-width: 100%; max-height: 70px;">' +
                                   '<div style="font-size: 10px; margin-top: 5px;">' +
                                   file.name + '<br>' + file.type + ' (' + Math.round(file.size / 1024) + 'KB)' +
                                   '</div>';
                
                if (imageNumber === 1) {{
                    document.getElementById('mergeDropArea1').innerHTML = htmlContent;
                }} else {{
                    document.getElementById('mergeDropArea2').innerHTML = htmlContent;
                }}
                
                if (mergeImage1 && mergeImage2) {{
                    document.getElementById('mergeImagesBtn').disabled = false;
                    showImagePreviews();
                }}
            }};
            reader.readAsDataURL(file);
        }}

        function showImagePreviews() {{
            const previewContainer = document.getElementById('mergePreviewContainer');
            const imagePreviews = document.getElementById('imagePreviews');
            const sizeInfo = document.getElementById('sizeInfo');
            
            previewContainer.style.display = 'block';
            imagePreviews.innerHTML = '';
            
            const reader1 = new FileReader();
            const reader2 = new FileReader();
            
            reader1.onload = function(e1) {{
                reader2.onload = function(e2) {{
                    const img1 = new Image();
                    const img2 = new Image();
                    
                    img1.onload = img2.onload = function() {{
                        imagePreviews.innerHTML = '<img src="' + e1.target.result + '" title="Image 1: ' + img1.width + '×' + img1.height + '">' +
                                                 '<img src="' + e2.target.result + '" title="Image 2: ' + img2.width + '×' + img2.height + '">';
                        
                        const direction = document.querySelector('input[name="mergeDirection"]:checked').value;
                        const resizeOption = document.querySelector('input[name="resizeOption"]:checked').value;
                        
                        if (resizeOption === 'equal') {{
                            if (direction === 'horizontal') {{
                                const targetHeight = Math.min(img1.height, img2.height);
                                const width1 = Math.round((targetHeight / img1.height) * img1.width);
                                const width2 = Math.round((targetHeight / img2.height) * img2.width);
                                sizeInfo.textContent = 'Merged size: ' + (width1 + width2) + '×' + targetHeight + ' pixels';
                            }} else {{
                                const targetWidth = Math.min(img1.width, img2.width);
                                const height1 = Math.round((targetWidth / img1.width) * img1.height);
                                const height2 = Math.round((targetWidth / img2.width) * img2.height);
                                sizeInfo.textContent = 'Merged size: ' + targetWidth + '×' + (height1 + height2) + ' pixels';
                            }}
                        }} else {{
                            if (direction === 'horizontal') {{
                                sizeInfo.textContent = 'Merged size: ' + (img1.width + img2.width) + '×' + Math.max(img1.height, img2.height) + ' pixels';
                            }} else {{
                                sizeInfo.textContent = 'Merged size: ' + Math.max(img1.width, img2.width) + '×' + (img1.height + img2.height) + ' pixels';
                            }}
                        }}
                    }};
                    
                    img1.src = e1.target.result;
                    img2.src = e2.target.result;
                }};
                reader2.readAsDataURL(mergeImage2);
            }};
            reader1.readAsDataURL(mergeImage1);
        }}

        function mergeImages(image1, image2, direction, resizeOption) {{
            return new Promise((resolve, reject) => {{
                const reader1 = new FileReader();
                const reader2 = new FileReader();
                
                reader1.onload = function(e1) {{
                    reader2.onload = function(e2) {{
                        const img1 = new Image();
                        const img2 = new Image();
                        
                        img1.onload = function() {{
                            img2.onload = function() {{
                                try {{
                                    const canvas = document.createElement('canvas');
                                    const ctx = canvas.getContext('2d');
                                    
                                    let width1 = img1.width;
                                    let height1 = img1.height;
                                    let width2 = img2.width;
                                    let height2 = img2.height;
                                    
                                    if (resizeOption === 'equal') {{
                                        if (direction === 'horizontal') {{
                                            const targetHeight = Math.min(height1, height2);
                                            width1 = Math.round((targetHeight / height1) * width1);
                                            height1 = targetHeight;
                                            width2 = Math.round((targetHeight / height2) * width2);
                                            height2 = targetHeight;
                                        }} else {{
                                            const targetWidth = Math.min(width1, width2);
                                            height1 = Math.round((targetWidth / width1) * height1);
                                            width1 = targetWidth;
                                            height2 = Math.round((targetWidth / width2) * height2);
                                            width2 = targetWidth;
                                        }}
                                    }}
                                    
                                    if (direction === 'horizontal') {{
                                        canvas.width = width1 + width2;
                                        canvas.height = Math.max(height1, height2);
                                    }} else {{
                                        canvas.width = Math.max(width1, width2);
                                        canvas.height = height1 + height2;
                                    }}
                                    
                                    if (direction === 'horizontal') {{
                                        ctx.drawImage(img1, 0, 0, width1, height1);
                                        ctx.drawImage(img2, width1, 0, width2, height2);
                                    }} else {{
                                        ctx.drawImage(img1, 0, 0, width1, height1);
                                        ctx.drawImage(img2, 0, height1, width2, height2);
                                    }}
                                    
                                    const outputFormat = image1.type === 'image/jpeg' && image2.type === 'image/jpeg' 
                                        ? 'image/jpeg' 
                                        : 'image/png';
                                    
                                    const fileExtension = outputFormat === 'image/jpeg' ? 'jpg' : 'png';
                                    
                                    canvas.toBlob(function(blob) {{
                                        const filename = `merged-${{Date.now()}}.${{fileExtension}}`;
                                        const file = new File([blob], filename, {{ type: outputFormat }});
                                        
                                        resolve({{
                                            message: 'Images merged successfully',
                                            filename: filename,
                                            file: file,
                                            format: outputFormat
                                        }});
                                    }}, outputFormat, 0.95);
                                    
                                }} catch (error) {{
                                    reject(new Error('Failed to merge images: ' + error.message));
                                }}
                            }};
                            
                            img2.onerror = function() {{
                                reject(new Error('Failed to load second image'));
                            }};
                            
                            img2.src = e2.target.result;
                        }};
                        
                        img1.onerror = function() {{
                            reject(new Error('Failed to load first image'));
                        }};
                        
                        img1.src = e1.target.result;
                    }};
                    
                    reader2.onerror = function() {{
                        reject(new Error('Failed to read second image file'));
                    }};
                    
                    reader2.readAsDataURL(image2);
                }};
                
                reader1.onerror = function() {{
                    reject(new Error('Failed to read first image file'));
                }};
                
                reader1.readAsDataURL(image1);
            }});
        }}

        function clearMergeAreas() {{
            mergeImage1 = null;
            mergeImage2 = null;
            document.getElementById('mergeDropArea1').innerHTML = '<p>Drag & drop first image here</p>';
            document.getElementById('mergeDropArea2').innerHTML = '<p>Drag & drop second image here</p>';
            document.getElementById('mergeImagesBtn').disabled = true;
            document.getElementById('mergePreviewContainer').style.display = 'none';
        }}

        function preventDefaults(e) {{
            e.preventDefault();
            e.stopPropagation();
        }}

        function highlight() {{
            document.getElementById('imageDropArea').classList.add('highlight');
        }}

        function unhighlight() {{
            document.getElementById('imageDropArea').classList.remove('highlight');
        }}

        function handleDrop(e) {{
            e.preventDefault();
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }}

        function handleFileSelect(e) {{
            const files = e.target.files;
            handleFiles(files);
        }}

        function handleFiles(files) {{
            if (files.length === 0) return;
            
            const file = files[0];
            const maxSize = 50 * 1024 * 1024;
            
            if (file.size > maxSize) {{
                showToast('File is too large. Maximum size is 50MB', 'error');
                return;
            }}
            
            if (!file.type.startsWith('image/')) {{
                showToast('Please select an image file', 'error');
                return;
            }}
            
            uploadedFile = file;
            
            const reader = new FileReader();
            reader.onload = function(e) {{
                const preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
                
                document.getElementById('imageDropArea').innerHTML = 
                    `<p>${{file.name}} (${{Math.round(file.size / 1024)}}KB)</p>`;
            }};
            reader.readAsDataURL(file);
        }}

        // ===== MULTI-DONOR: form submit now sends donors array =====
        function handleFormSubmit(e) {{
            e.preventDefault();
            
            const country = document.getElementById('country').value;
            const currencyType = document.getElementById('currencyType').value;
            
            // Filter out empty donors and validate
            const validDonors = donorsList.map(d => (d || '').trim()).filter(Boolean);
            
            if (!country || !currencyType) {{
                showToast('Please fill in all required fields', 'error');
                return;
            }}
            
            if (validDonors.length === 0) {{
                showToast('At least one donor is required', 'error');
                return;
            }}
            
            const formData = new FormData();
            formData.append('country', country);
            formData.append('currency_type', currencyType);
            formData.append('donor_name', validDonors[0]);           // primary, backward compat
            formData.append('donors', JSON.stringify(validDonors));  // full array
            formData.append('note', document.getElementById('note').value);
            formData.append('size', document.getElementById('size').value);
            formData.append('year', document.getElementById('year').value);
            formData.append('hidden_note', document.getElementById('hiddenNote').value);
            formData.append('item_id', document.getElementById('itemId').value);
            formData.append('original_image', document.getElementById('originalImage').value);
            
            if (uploadedFile) {{
                formData.append('file', uploadedFile);
            }}
            
            showToast('Updating item...');
            
            fetch('/update-existing-item', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.message) {{
                    showToast(data.message);
                    setTimeout(() => {{
                        window.location.href = '/edit_json';
                    }}, 1500);
                }} else {{
                    showToast(data.error || 'An error occurred', 'error');
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                showToast('Error updating item: ' + error.message, 'error');
            }});
        }}
        // ===== END MULTI-DONOR form submit =====

        function showToast(message, type = 'success') {{
            const toast = document.getElementById('toastMessage');
            toast.textContent = message;
            toast.style.backgroundColor = type === 'success' ? 'rgba(40, 167, 69, 0.9)' : 'rgba(220, 53, 69, 0.9)';
            toast.style.display = 'block';
            
            setTimeout(() => {{
                toast.style.display = 'none';
            }}, 3000);
        }}
    </script>
</body>
</html>
    '''
# ===== END MULTI-DONOR render_edit_item_page =====


@app.route('/upload')
@app.route("/", methods=["GET", "POST"])
def upload_form():
    return '''
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
    '''

# ===== MULTI-DONOR: /upload POST accepts donors array =====
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
        shape = request.form.get('shape', '')
        thickness = request.form.get('thickness', '')

        # NEW: parse donors array if sent
        donors_json = request.form.get('donors', '')
        donors = []
        if donors_json:
            try:
                donors = json.loads(donors_json)
                if not isinstance(donors, list):
                    donors = []
            except json.JSONDecodeError:
                donors = []
        
        print(f"Received form data: country={country}, donor={donor_name}, donors={donors}, currency={currency_type}, shape={shape}, thickness={thickness}")

        # Validate required fields
        if not country:
            return jsonify({"message": "Country is required!"}), 400
        if not donor_name and not donors:
            return jsonify({"message": "At least one donor is required!"}), 400
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
            # Update the JSON file with all fields including new ones
            update_json_file(country, file_name, note, donor_name, currency_type, size, year, hidden_note, shape, thickness, donors=donors)
            primary_donor, donors_list = normalize_donors(donor_name, donors)
            return jsonify({
                "id": os.path.splitext(os.path.basename(file_name))[0],
                "message": "File uploaded successfully!",
                "country": country,
                "note": note,
                "donor_name": primary_donor,
                "donors": donors_list,
                "currency_type": currency_type,
                "size": size,
                "year": year,
                "hidden_note": hidden_note,
                "shape": shape,
                "thickness": thickness,
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
# ===== END MULTI-DONOR /upload POST =====

@app.route('/upload-form')
def upload_form_page():
    """Serve the upload form page with image merging functionality, copy from existing, and multi-donor support"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload New Item</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background-color: #f8f9fa;
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }

        .navigation-buttons {
            display: flex;
            justify-content: space-between;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eaeaea;
        }

        .nav-btn {
            display: inline-flex;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .nav-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            background: linear-gradient(135deg, #5a6268 0%, #495057 100%);
            color: white;
            text-decoration: none;
        }

        .nav-btn i {
            margin-right: 8px;
        }

        h1 {
            text-align: center;
            margin-bottom: 25px;
            color: #2c3e50;
            font-weight: 600;
            font-size: 28px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #495057;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 15px;
            transition: border 0.3s;
        }

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            border-color: #007bff;
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
        }

        .form-group textarea {
            height: 80px;
            resize: vertical;
        }

        .drop-area {
            border: 2px dashed #ced4da;
            border-radius: 6px;
            padding: 25px;
            text-align: center;
            background-color: #f8f9fa;
            color: #6c757d;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.3s;
        }

        .drop-area.highlight {
            border-color: #007bff;
            background-color: #e9f0ff;
        }

        .btn {
            padding: 12px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            margin-right: 10px;
            transition: all 0.3s;
        }

        .btn-primary {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
        }

        .btn-primary:hover {
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
        }

        .btn-success {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
        }

        .btn-success:hover {
            background: linear-gradient(135deg, #1e7e34 0%, #155724 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
        }

        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }

        .btn-danger:hover {
            background: linear-gradient(135deg, #c82333 0%, #a71e2a 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
        }

        .btn-info {
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
        }

        .btn-info:hover {
            background: linear-gradient(135deg, #138496 0%, #117a8b 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(23, 162, 184, 0.3);
        }

        .btn-move {
            background: linear-gradient(135deg, #fd7e14 0%, #e8590c 100%);
        }

        .btn-move:hover {
            background: linear-gradient(135deg, #e8590c 0%, #d9480f 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(253, 126, 20, 0.3);
        }

        .image-preview {
            max-width: 100%;
            max-height: 200px;
            margin-top: 10px;
            display: none;
            border-radius: 6px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .toast-message {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: rgba(40, 167, 69, 0.95);
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            font-size: 14px;
            font-weight: 500;
            min-width: 250px;
            text-align: center;
            animation: slideIn 0.3s ease;
        }

        .toast-message.error {
            background-color: rgba(220, 53, 69, 0.95);
        }

        .toast-message.warning {
            background-color: rgba(255, 193, 7, 0.95);
            color: #333;
        }

        .toast-message.info {
            background-color: rgba(23, 162, 184, 0.95);
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }

        .merge-controls {
            margin-top: 25px;
            padding: 20px;
            border: 1px solid #eaeaea;
            border-radius: 8px;
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
            padding: 15px;
            border: 1px dashed #007bff;
            border-radius: 6px;
            background-color: #f8f9fa;
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
            color: #666;
            margin-top: 5px;
        }

        .image-drop-areas-container {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }

        .footer-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eaeaea;
        }

        .copy-section {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #e9ecef;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }

        .copy-section h4 {
            margin-bottom: 10px;
            color: #28a745;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .copy-section select {
            width: 100%;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #ced4da;
            margin-bottom: 10px;
        }

        .copy-btn {
            padding: 8px 16px;
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .copy-btn:hover {
            background: linear-gradient(135deg, #1e7e34 0%, #155724 100%);
            transform: translateY(-1px);
        }

        .copy-info {
            font-size: 12px;
            color: #6c757d;
            margin-top: 8px;
        }

        .hidden-note-container {
            display: flex;
            gap: 10px;
            align-items: flex-start;
        }
        
        .hidden-note-container textarea {
            flex: 1;
        }
        
        .scrape-btn {
            padding: 10px 15px;
            background: linear-gradient(135deg, #6f42c1 0%, #5a32a3 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .scrape-btn:hover {
            background: linear-gradient(135deg, #5a32a3 0%, #4a2885 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(111, 66, 193, 0.3);
        }
        
        .scrape-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .scrape-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .move-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
        }

        /* ===== MULTI-DONOR styles ===== */
        .donors-container {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
        }
        .donor-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            padding: 8px;
            background-color: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }
        .donor-item:last-child { margin-bottom: 0; }
        .donor-input {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .donor-input:focus { border-color: #007bff; outline: none; }
        .btn-remove-donor {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
            border: none;
            border-radius: 4px;
            width: 32px;
            height: 32px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .btn-remove-donor:hover { background: linear-gradient(135deg, #c82333 0%, #a71e2a 100%); }
        .btn-add-donor {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
        }
        .btn-add-donor:hover { background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%); }
        /* ===== END MULTI-DONOR styles ===== */
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="navigation-buttons">
            <a href="http://localhost:5000/edit_json" class="nav-btn" target="_blank">
                <i class="fas fa-edit"></i> JSON Editor
            </a>
            <a href="http://localhost:5000/root-index" class="nav-btn" target="_blank">
                <i class="fas fa-home"></i> Root Index
            </a>
        </div>
        
        <h1>Upload New Collection Item</h1>
        
        <div class="copy-section" style="border-left-color: #fd7e14; margin-bottom: 20px;">
            <h4 style="color: #fd7e14;">
                <i class="fas fa-folder-open"></i> Image Management
            </h4>
            <p style="margin-bottom: 15px; font-size: 14px; color: #666;">
                <i class="fas fa-info-circle"></i> Move all images from your Pictures folder to the "Done" subfolder.
                This helps organize your source images after uploading.
            </p>
            <button id="moveImagesBtn" class="copy-btn" style="background: linear-gradient(135deg, #fd7e14 0%, #e8590c 100%);">
                <i class="fas fa-arrow-right"></i> Move Images to Done Folder
            </button>
            <div id="moveStatus" style="margin-top: 10px; font-size: 13px; color: #666; display: none;">
                <i class="fas fa-spinner fa-spin"></i> <span id="moveStatusText">Processing...</span>
            </div>
        </div>
        
        <div class="copy-section" id="copySection" style="display: none;">
            <h4><i class="fas fa-copy"></i> Copy from Existing Item</h4>
            <select id="existingItemsSelect">
                <option value="">Select an existing item to copy from</option>
            </select>
            <button id="copyExistingBtn" class="copy-btn"><i class="fas fa-copy"></i> Copy Data</button>
            <div class="copy-info">
                <i class="fas fa-info-circle"></i> This will pre-fill the form with data from an existing item. 
                You'll still need to upload a new image.
            </div>
        </div>
        
        <form id="uploadForm">
            <div class="form-group">
                <label for="country">Country:</label>
                <select id="country" name="country" required>
                    <option value="">Select a country</option>
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
            
            <!-- ===== MULTI-DONOR UI ===== -->
            <div class="form-group">
                <label>Donors:</label>
                <div class="donors-container" id="donorsContainer"></div>
                <button type="button" class="btn-add-donor" onclick="addDonor()">
                    <i class="fas fa-plus-circle"></i> Add Another Donor
                </button>
                <small style="color: #6c757d; display: block; margin-top: 5px;">
                    <i class="fas fa-info-circle"></i>
                    Add multiple donors if the item was donated by more than one person.
                </small>
            </div>
            <!-- ===== END MULTI-DONOR UI =====-->
            
            <div class="form-group">
                <label for="note">Note:</label>
                <textarea id="note" name="note"></textarea>
            </div>
            
            <div class="form-group">
                <label for="shape">Shape:</label>
                <input type="text" id="shape" name="shape" placeholder="e.g., Round, Scalloped, Polygon, etc.">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="size">Size (Diameter/Width):</label>
                    <input type="text" id="size" name="size" placeholder="e.g., 23.5 mm">
                </div>
                <div class="form-group">
                    <label for="thickness">Thickness:</label>
                    <input type="text" id="thickness" name="thickness" placeholder="e.g., 1.8 mm">
                </div>
            </div>
            
            <div class="form-group">
                <label for="year">Year:</label>
                <input type="text" id="year" name="year" placeholder="e.g., 1967">
            </div>
            
            <div class="form-group">
                <label for="hiddenNote">Hidden Note (Numista URL or other info):</label>
                <div class="hidden-note-container">
                    <textarea id="hiddenNote" name="hidden_note" placeholder="https://en.numista.com/..."></textarea>
                    <button type="button" id="scrapeNumistaBtn" class="scrape-btn">
                        <i class="fas fa-globe"></i> Scrape Numista
                    </button>
                </div>
                <small style="color: #6c757d; display: block; margin-top: 5px;">
                    <i class="fas fa-info-circle"></i> Enter a Numista URL and click "Scrape Numista" to auto-fill fields
                </small>
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
            
            <div class="footer-buttons">
                <button type="submit" class="btn btn-primary">Upload Item</button>
                <button type="button" class="btn btn-danger" onclick="if(confirm('Are you sure?')) window.location.href='/edit_json'">Cancel</button>
            </div>
        </form>
    </div>
    
    <div id="toastMessage" class="toast-message"></div>
    <datalist id="donor-suggestions"></datalist>

    <script>
    let uploadedFile = null;
    let mergeImage1 = null;
    let mergeImage2 = null;
    let countriesData = [];
    let allJsonData = [];

    // ===== MULTI-DONOR state =====
    let donorsList = [''];
    // ===== END MULTI-DONOR =====

    function setupMoveImagesButton() {
        const moveBtn = document.getElementById('moveImagesBtn');
        const moveStatus = document.getElementById('moveStatus');
        const moveStatusText = document.getElementById('moveStatusText');
        
        moveBtn.addEventListener('click', async function() {
            const originalText = moveBtn.innerHTML;
            moveBtn.innerHTML = '<span class="move-spinner"></span> Moving...';
            moveBtn.disabled = true;
            
            moveStatus.style.display = 'block';
            moveStatusText.innerHTML = 'Scanning Pictures folder...';
            
            try {
                const response = await fetch('/move-images-to-done', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                
                if (result.error) {
                    showToast('Error: ' + result.error, 'error');
                    moveStatusText.innerHTML = '❌ Error: ' + result.error;
                    moveStatus.style.backgroundColor = 'rgba(220, 53, 69, 0.1)';
                    moveStatus.style.padding = '8px 12px';
                    moveStatus.style.borderRadius = '6px';
                } else {
                    showToast(result.message, 'success');
                    let statusHtml = `✅ ${result.message}<br>`;
                    statusHtml += `📁 Source: ${result.source_folder}<br>`;
                    statusHtml += `📂 Destination: ${result.destination_folder}`;
                    moveStatusText.innerHTML = statusHtml;
                    moveStatus.style.backgroundColor = 'rgba(40, 167, 69, 0.1)';
                    moveStatus.style.padding = '8px 12px';
                    moveStatus.style.borderRadius = '6px';
                    
                    setTimeout(() => {
                        moveStatus.style.display = 'none';
                        moveStatus.style.backgroundColor = '';
                    }, 8000);
                }
            } catch (error) {
                console.error('Move images error:', error);
                showToast('Error moving images: ' + error.message, 'error');
                moveStatusText.innerHTML = '❌ Error: ' + error.message;
                moveStatus.style.backgroundColor = 'rgba(220, 53, 69, 0.1)';
                moveStatus.style.padding = '8px 12px';
                moveStatus.style.borderRadius = '6px';
            } finally {
                moveBtn.innerHTML = originalText;
                moveBtn.disabled = false;
            }
        });
    }

    function showToast(message, type = 'success') {
        const toast = document.getElementById('toastMessage');
        if (!toast) return;
        
        toast.textContent = message;
        toast.className = 'toast-message';
        if (type === 'error') {
            toast.classList.add('error');
        } else if (type === 'warning') {
            toast.classList.add('warning');
        } else if (type === 'info') {
            toast.classList.add('info');
        }
        toast.style.display = 'block';
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                toast.style.display = 'none';
                toast.style.animation = '';
                toast.className = 'toast-message';
            }, 300);
        }, 4000);
    }

    // ===== MULTI-DONOR functions =====
    function renderDonors() {
        const container = document.getElementById('donorsContainer');
        if (!container) return;
        container.innerHTML = '';
        
        if (donorsList.length === 0) donorsList.push('');
        
        donorsList.forEach((donor, index) => {
            const div = document.createElement('div');
            div.className = 'donor-item';
            
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'donor-input';
            input.value = donor || '';
            input.placeholder = 'Donor name';
            input.setAttribute('list', 'donor-suggestions');
            input.autocomplete = 'off';
            input.addEventListener('input', function() {
                donorsList[index] = this.value;
                fetchDonorSuggestions(this.value);
            });
            
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn-remove-donor';
            removeBtn.innerHTML = '<i class="fas fa-times"></i>';
            removeBtn.title = 'Remove donor';
            removeBtn.onclick = function() { removeDonor(index); };
            
            div.appendChild(input);
            div.appendChild(removeBtn);
            container.appendChild(div);
        });
    }

    function addDonor() {
        donorsList.push('');
        renderDonors();
        const inputs = document.querySelectorAll('.donor-input');
        if (inputs.length) inputs[inputs.length - 1].focus();
    }

    function removeDonor(index) {
        if (donorsList.length <= 1) {
            showToast('At least one donor is required', 'error');
            return;
        }
        donorsList.splice(index, 1);
        renderDonors();
    }

    function fetchDonorSuggestions(query) {
        const datalist = document.getElementById('donor-suggestions');
        if (!query || query.trim().length < 2) {
            datalist.innerHTML = '';
            return;
        }
        fetch(`/suggest-donors?q=${encodeURIComponent(query.trim())}`)
            .then(r => r.json())
            .then(suggestions => {
                datalist.innerHTML = '';
                suggestions.forEach(name => {
                    const opt = document.createElement('option');
                    opt.value = name;
                    datalist.appendChild(opt);
                });
            })
            .catch(err => console.error('Donor suggestions error:', err));
    }
    // ===== END MULTI-DONOR functions =====

    document.addEventListener('DOMContentLoaded', function() {
        loadCountries();
        loadAllJsonData();
        setupEventListeners();
        setupImageMerging();
        setupScrapeButton();
        setupMoveImagesButton();
        renderDonors();  // ===== MULTI-DONOR =====
    });

    function setupScrapeButton() {
        const scrapeBtn = document.getElementById('scrapeNumistaBtn');
        
        scrapeBtn.addEventListener('click', async function() {
            const hiddenNote = document.getElementById('hiddenNote').value.trim();
            
            if (!hiddenNote) {
                showToast('Please enter a Numista URL in the Hidden Note field', 'error');
                return;
            }
            
            const originalText = scrapeBtn.innerHTML;
            scrapeBtn.innerHTML = '<i class="fas fa-spinner scrape-spinner"></i> Scraping...';
            scrapeBtn.disabled = true;
            
            try {
                const response = await fetch('/scrape-numista', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ url: hiddenNote })
                });
                
                const result = await response.json();
                
                if (result.error) {
                    showToast('Error: ' + result.error, 'error');
                } else if (result.data) {
                    fillFormWithScrapedData(result.data);
                    showToast('Successfully scraped data from Numista!', 'success');
                }
            } catch (error) {
                console.error('Scraping error:', error);
                showToast('Error scraping Numista: ' + error.message, 'error');
            } finally {
                scrapeBtn.innerHTML = originalText;
                scrapeBtn.disabled = false;
            }
        });
    }
    
    function fillFormWithScrapedData(data) {
        if (data.Value || data.Composition) {
            let noteParts = [];
            
            if (data.Value) {
                let cleanedValue = data.Value.replace(/\\n/g, ' ').replace(/&nbsp;/g, ' ').replace(/\\s+/g, ' ').trim();
                noteParts.push(cleanedValue);
            }
            
            if (data.Composition) {
                let cleanedComposition = data.Composition.toLowerCase();
                noteParts.push(`Composition ${cleanedComposition}`);
            }
            
            if (noteParts.length > 0) {
                document.getElementById('note').value = noteParts.join('. ');
            }
        }
        
        if (data.Thickness) {
            let thickness = data.Thickness.replace(/\\n/g, ' ').replace(/&nbsp;/g, ' ').replace(/\\s+/g, ' ').trim();
            document.getElementById('thickness').value = thickness;
        }
        
        if (data.Diameter) {
            let diameter = data.Diameter.replace(/\\n/g, ' ').replace(/&nbsp;/g, ' ').replace(/\\s+/g, ' ').trim();
            document.getElementById('size').value = diameter;
        } else if (data.Size) {
            let size = data.Size.replace(/\\n/g, ' ').replace(/&nbsp;/g, ' ').replace(/\\s+/g, ' ').trim();
            document.getElementById('size').value = size;
        }
        
        if (data.Shape) {
            let shape = data.Shape.replace(/\\n/g, ' ').replace(/&nbsp;/g, ' ').replace(/\\s+/g, ' ').trim();
            document.getElementById('shape').value = shape;
        }
        
        if (data.Year && !document.getElementById('year').value) {
            let year = data.Year.replace(/\\n/g, ' ').replace(/&nbsp;/g, ' ').replace(/\\s+/g, ' ').trim();
            const yearMatch = year.match(/\\b(\\d{4})\\b/);
            if (yearMatch) {
                document.getElementById('year').value = yearMatch[1];
            } else {
                document.getElementById('year').value = year;
            }
        }
        
        const fields = ['note', 'thickness', 'size', 'shape', 'year'];
        fields.forEach(field => {
            const element = document.getElementById(field);
            if (element && element.value) {
                element.style.backgroundColor = '#e8f5e9';
                setTimeout(() => {
                    element.style.backgroundColor = '';
                }, 1000);
            }
        });
    }

    function loadAllJsonData() {
        fetch('/get-all-json')
            .then(response => response.json())
            .then(data => {
                allJsonData = data;
                populateExistingItemsDropdown();
            })
            .catch(error => {
                console.error("Error loading JSON data:", error);
            });
    }

    function loadCountries() {
        fetch('/get-countries')
            .then(response => response.json())
            .then(data => {
                countriesData = data;
                populateCountryDropdown();
            })
            .catch(error => {
                console.error("Error loading countries:", error);
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

    function populateExistingItemsDropdown() {
        const existingItemsSelect = document.getElementById('existingItemsSelect');
        if (!existingItemsSelect) return;
        
        existingItemsSelect.innerHTML = '<option value="">Select an existing item to copy from</option>';
        allJsonData.forEach((item, index) => {
            const option = document.createElement('option');
            option.value = index;
            let label = `${item.country || 'Unknown'} - ${item.currency_type || 'Unknown type'} - ${item.donor_name || 'Unknown donor'}`;
            if (item.year) label += ` (${item.year})`;
            if (item.size) label += ` - ${item.size}`;
            option.textContent = label;
            option.dataset.item = JSON.stringify(item);
            existingItemsSelect.appendChild(option);
        });
    }

    function setupCountryCopyListener() {
        const countrySelect = document.getElementById('country');
        const copySection = document.getElementById('copySection');
        const existingItemsSelect = document.getElementById('existingItemsSelect');
        
        if (!countrySelect || !copySection || !existingItemsSelect) return;
        
        countrySelect.addEventListener('change', function() {
            const selectedCountry = this.value;
            
            if (!selectedCountry) {
                copySection.style.display = 'none';
                return;
            }
            
            const existingItems = allJsonData.filter(item => item.country === selectedCountry);
            
            if (existingItems.length > 0) {
                existingItemsSelect.innerHTML = '<option value="">Select an existing item to copy from</option>';
                existingItems.forEach((item, index) => {
                    const option = document.createElement('option');
                    option.value = index;
                    let label = `${item.currency_type || 'Unknown type'} - ${item.donor_name || 'Unknown donor'}`;
                    if (item.year) label += ` (${item.year})`;
                    if (item.size) label += ` - ${item.size}`;
                    option.textContent = label;
                    option.dataset.item = JSON.stringify(item);
                    existingItemsSelect.appendChild(option);
                });
                copySection.style.display = 'block';
            } else {
                copySection.style.display = 'none';
            }
        });
    }
    
    function setupCopyButton() {
        const copyBtn = document.getElementById('copyExistingBtn');
        const existingItemsSelect = document.getElementById('existingItemsSelect');
        
        if (!copyBtn || !existingItemsSelect) return;
        
        copyBtn.addEventListener('click', function() {
            const selectedOption = existingItemsSelect.options[existingItemsSelect.selectedIndex];
            if (!selectedOption.value || !selectedOption.dataset.item) {
                showToast('Please select an item to copy from', 'error');
                return;
            }
            
            const itemToCopy = JSON.parse(selectedOption.dataset.item);
            
            const currencyTypeEl = document.getElementById('currencyType');
            const noteEl = document.getElementById('note');
            const sizeEl = document.getElementById('size');
            const yearEl = document.getElementById('year');
            const hiddenNoteEl = document.getElementById('hiddenNote');
            const shapeEl = document.getElementById('shape');
            const thicknessEl = document.getElementById('thickness');
            
            if (currencyTypeEl) currencyTypeEl.value = itemToCopy.currency_type || 'coin';
            if (noteEl) noteEl.value = itemToCopy.note || '';
            if (sizeEl) sizeEl.value = itemToCopy.size || '';
            if (yearEl) yearEl.value = itemToCopy.year || '';
            if (hiddenNoteEl) hiddenNoteEl.value = itemToCopy.hidden_note || '';
            if (shapeEl && itemToCopy.shape) shapeEl.value = itemToCopy.shape;
            if (thicknessEl && itemToCopy.thickness) thicknessEl.value = itemToCopy.thickness;

            // ===== MULTI-DONOR: copy the donors array =====
            let donorsToCopy = [];
            if (Array.isArray(itemToCopy.donors) && itemToCopy.donors.length > 0) {
                donorsToCopy = itemToCopy.donors.filter(d => d && d.trim());
            } else if (itemToCopy.donor_name && itemToCopy.donor_name.trim()) {
                donorsToCopy = [itemToCopy.donor_name.trim()];
            }
            if (donorsToCopy.length > 0) {
                donorsList = donorsToCopy;
                renderDonors();
            }
            // ===== END MULTI-DONOR copy =====
            
            showToast(`Copied data from existing item for ${itemToCopy.country}`, 'success');
            
            const fields = ['currencyType', 'note', 'size', 'year', 'shape', 'thickness'];
            fields.forEach(field => {
                const element = document.getElementById(field);
                if (element && element.value) {
                    element.style.backgroundColor = '#e8f5e9';
                    setTimeout(() => {
                        element.style.backgroundColor = '';
                    }, 1000);
                }
            });
        });
    }

    function setupEventListeners() {
        const dropArea = document.getElementById('imageDropArea');
        const fileInput = document.getElementById('imageInput');
        
        if (!dropArea || !fileInput) return;
        
        dropArea.addEventListener('click', () => fileInput.click());
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        dropArea.addEventListener('drop', handleDrop, false);
        fileInput.addEventListener('change', handleFileSelect, false);
        document.getElementById('uploadForm').addEventListener('submit', handleFormSubmit);
        
        setupCountryCopyListener();
        setupCopyButton();
    }

    function setupImageMerging() {
        const mergeDropArea1 = document.getElementById('mergeDropArea1');
        const mergeDropArea2 = document.getElementById('mergeDropArea2');
        const mergeImagesBtn = document.getElementById('mergeImagesBtn');
        const clearMergeBtn = document.getElementById('clearMergeBtn');
        
        if (!mergeDropArea1 || !mergeDropArea2 || !mergeImagesBtn || !clearMergeBtn) return;
        
        setupMergeDropArea(mergeDropArea1, 1);
        setupMergeDropArea(mergeDropArea2, 2);
        
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
                    
                    uploadedFile = result.file;
                    document.getElementById('imageDropArea').innerHTML = 
                        `<p>Merged image: ${result.filename}</p>`;
                    document.getElementById('imagePreview').src = URL.createObjectURL(result.file);
                    document.getElementById('imagePreview').style.display = 'block';
                    
                    clearMergeAreas();
                })
                .catch(error => {
                    console.error('Error merging images:', error);
                    showToast('Error merging images: ' + error.message, 'error');
                });
        });
        
        clearMergeBtn.addEventListener('click', clearMergeAreas);
    }

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
            showToast('Please select an image file', 'error');
            return;
        }
        
        if (imageNumber === 1) {
            mergeImage1 = file;
        } else {
            mergeImage2 = file;
        }
        
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
            
            if (mergeImage1 && mergeImage2) {
                document.getElementById('mergeImagesBtn').disabled = false;
                showImagePreviews();
            }
        };
        reader.readAsDataURL(file);
    }

    function showImagePreviews() {
        const previewContainer = document.getElementById('mergePreviewContainer');
        const imagePreviews = document.getElementById('imagePreviews');
        const sizeInfo = document.getElementById('sizeInfo');
        
        if (!previewContainer || !imagePreviews || !sizeInfo) return;
        
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
                                const canvas = document.createElement('canvas');
                                const ctx = canvas.getContext('2d');
                                
                                let width1 = img1.width;
                                let height1 = img1.height;
                                let width2 = img2.width;
                                let height2 = img2.height;
                                
                                if (resizeOption === 'equal') {
                                    if (direction === 'horizontal') {
                                        const targetHeight = Math.min(height1, height2);
                                        width1 = Math.round((targetHeight / height1) * width1);
                                        height1 = targetHeight;
                                        width2 = Math.round((targetHeight / height2) * width2);
                                        height2 = targetHeight;
                                    } else {
                                        const targetWidth = Math.min(width1, width2);
                                        height1 = Math.round((targetWidth / width1) * height1);
                                        width1 = targetWidth;
                                        height2 = Math.round((targetWidth / width2) * height2);
                                        width2 = targetWidth;
                                    }
                                }
                                
                                if (direction === 'horizontal') {
                                    canvas.width = width1 + width2;
                                    canvas.height = Math.max(height1, height2);
                                } else {
                                    canvas.width = Math.max(width1, width2);
                                    canvas.height = height1 + height2;
                                }
                                
                                if (direction === 'horizontal') {
                                    ctx.drawImage(img1, 0, 0, width1, height1);
                                    ctx.drawImage(img2, width1, 0, width2, height2);
                                } else {
                                    ctx.drawImage(img1, 0, 0, width1, height1);
                                    ctx.drawImage(img2, 0, height1, width2, height2);
                                }
                                
                                const outputFormat = image1.type === 'image/jpeg' && image2.type === 'image/jpeg' 
                                    ? 'image/jpeg' 
                                    : 'image/png';
                                
                                const fileExtension = outputFormat === 'image/jpeg' ? 'jpg' : 'png';
                                
                                canvas.toBlob(function(blob) {
                                    const filename = `merged-${Date.now()}.${fileExtension}`;
                                    const file = new File([blob], filename, { type: outputFormat });
                                    
                                    resolve({
                                        message: 'Images merged successfully',
                                        filename: filename,
                                        file: file,
                                        format: outputFormat
                                    });
                                }, outputFormat, 0.95);
                                
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

    function clearMergeAreas() {
        mergeImage1 = null;
        mergeImage2 = null;
        document.getElementById('mergeDropArea1').innerHTML = '<p>Drag & drop first image here</p>';
        document.getElementById('mergeDropArea2').innerHTML = '<p>Drag & drop second image here</p>';
        document.getElementById('mergeImagesBtn').disabled = true;
        document.getElementById('mergePreviewContainer').style.display = 'none';
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        document.getElementById('imageDropArea').classList.add('highlight');
    }

    function unhighlight() {
        document.getElementById('imageDropArea').classList.remove('highlight');
    }

    function handleDrop(e) {
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
        const maxSize = 50 * 1024 * 1024;
        
        if (file.size > maxSize) {
            showToast('File is too large. Maximum size is 50MB', 'error');
            return;
        }
        
        if (!file.type.startsWith('image/')) {
            showToast('Please select an image file', 'error');
            return;
        }
        
        uploadedFile = file;
        
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

    // ===== MULTI-DONOR: submit sends donors array =====
    function handleFormSubmit(e) {
        e.preventDefault();
        
        const country = document.getElementById('country').value;
        const currencyType = document.getElementById('currencyType').value;
        
        const validDonors = donorsList.map(d => (d || '').trim()).filter(Boolean);
        
        if (!country || !currencyType) {
            showToast('Please fill in all required fields', 'error');
            return;
        }
        
        if (validDonors.length === 0) {
            showToast('At least one donor is required', 'error');
            return;
        }
        
        if (!uploadedFile) {
            showToast('Please upload an image', 'error');
            return;
        }
        
        const formData = new FormData();
        formData.append('country', country);
        formData.append('currency_type', currencyType);
        formData.append('donor_name', validDonors[0]);           // primary, backward compat
        formData.append('donors', JSON.stringify(validDonors));  // full array
        formData.append('note', document.getElementById('note').value);
        formData.append('size', document.getElementById('size').value);
        formData.append('year', document.getElementById('year').value);
        formData.append('hidden_note', document.getElementById('hiddenNote').value);
        formData.append('shape', document.getElementById('shape').value);
        formData.append('thickness', document.getElementById('thickness').value);
        formData.append('file', uploadedFile);
        
        showToast('Uploading item...', 'info');
        
        fetch('/upload', {
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
                loadAllJsonData();
            } else {
                showToast(data.error || 'An error occurred', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error uploading item: ' + error.message, 'error');
        });
    }
    // ===== END MULTI-DONOR submit =====

    function resetForm() {
        document.getElementById('uploadForm').reset();
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('imageDropArea').innerHTML = '<p>Drag & drop an image here or click to select</p>';
        uploadedFile = null;
        clearMergeAreas();
        const existingItemsSelect = document.getElementById('existingItemsSelect');
        if (existingItemsSelect) {
            existingItemsSelect.selectedIndex = 0;
        }
        // ===== MULTI-DONOR: reset donors =====
        donorsList = [''];
        renderDonors();
        // ===== END MULTI-DONOR reset =====
    }
</script>
</body>
</html>
    '''
# ===== END MULTI-DONOR upload form =====

@app.route('/move-images-to-done', methods=['POST'])
def move_images_to_done():
    """Move image files from Pictures folder to Done subfolder"""
    import os
    import shutil
    from pathlib import Path
    
    try:
        source_dir = Path(r"C:\Users\75MAMIRUZZAM\OneDrive - West Chester University of PA\Pictures")
        target_dir = source_dir / "Done"
        
        if not source_dir.exists():
            return jsonify({
                "error": f"Source folder not found: {source_dir}"
            }), 404
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        
        moved_count = 0
        moved_files = []
        skipped_files = []
        
        for file_path in source_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                destination = target_dir / file_path.name
                
                if destination.exists():
                    base = destination.stem
                    ext = destination.suffix
                    counter = 1
                    while destination.exists():
                        new_name = f"{base}_{counter}{ext}"
                        destination = target_dir / new_name
                        counter += 1
                
                shutil.move(str(file_path), str(destination))
                moved_count += 1
                moved_files.append(file_path.name)
                print(f"Moved: {file_path.name}")
        
        if moved_count > 0:
            message = f"Success! {moved_count} image(s) moved to Done folder."
            if moved_count == 1:
                message = f"Success! 1 image moved to Done folder."
        else:
            message = "No image files found to move."
        
        return jsonify({
            "message": message,
            "moved_count": moved_count,
            "moved_files": moved_files[:10],
            "source_folder": str(source_dir),
            "destination_folder": str(target_dir)
        }), 200
        
    except Exception as e:
        print(f"Error moving images: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Failed to move images: {str(e)}"
        }), 500

@app.route('/scrape-numista', methods=['POST'])
def scrape_numista():
    """Scrape Numista URL and return extracted data"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        print(f"Scraping Numista URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return jsonify({"error": f"Failed to load page. Status code: {response.status_code}"}), 400
        
        soup = BeautifulSoup(response.text, 'html.parser')
        features = {}
        
        features_table = soup.find('table', {'id': 'coin_features'})
        
        if not features_table:
            issuer_th = soup.find('th', string=lambda x: x and 'Issuer' in x)
            if issuer_th:
                features_table = issuer_th.find_parent('table')
        
        if features_table:
            for row in features_table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True).replace('\\xa0', ' ').replace("\n", " ").replace("&nbsp", " ").replace("mm", " ").strip()
                    features[key] = value
            
            result = {}
            
            field_mappings = {
                'Value': 'Value',
                'Composition': 'Composition',
                'Diameter': 'Diameter',
                'Size': 'Size',
                'Thickness': 'Thickness',
                'Shape': 'Shape',
                'Year': 'Year'
            }
            
            for numista_key, form_key in field_mappings.items():
                if numista_key in features:
                    result[form_key] = features[numista_key]
            
            return jsonify({
                "success": True,
                "data": result,
                "url": url
            })
        else:
            return jsonify({"error": "Could not find the Features section on this page."}), 404
            
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out. Please try again."}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/merge-images-upload', methods=['POST'])
def merge_images_upload():
    """Handle image merging for the upload form"""
    try:
        country = request.form.get('country')
        image1 = request.files.get('image1')
        image2 = request.files.get('image2')
        direction = request.form.get('direction', 'horizontal')
        
        if not all([country, image1, image2]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        img1 = Image.open(image1)
        img2 = Image.open(image2)
        
        output_format = 'PNG'
        if image1.content_type == 'image/jpeg' and image2.content_type == 'image/jpeg':
            output_format = 'JPEG'
        
        if direction == 'horizontal':
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

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/crop-image')
def crop_image():
    return render_template('crop.html')

@app.route('/crop/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/crop', methods=['POST'])
def upload_cropped_image():
    if 'image' not in request.files:
        return jsonify({'message': 'No image file provided'}), 400

    file = request.files['image']

    if file and allowed_image_file(file.filename):
        filename = file.filename
        file_path = os.path.join(IMAGE_FOLDER, filename)
        file.save(file_path)
        return jsonify({'message': f'Cropped image saved as {filename}', 'file_path': file_path}), 200
    else:
        return jsonify({'message': 'Invalid file type'}), 400

@app.route('/manage_image', methods=['GET', 'POST'])
def manage_image():
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if allowed_image_file(f)]

    if request.method == 'POST':
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename == '':
                flash('No selected file', 'error')
            elif file and allowed_image_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(IMAGE_FOLDER, filename))
                flash(f"Image uploaded successfully: {filename}", 'success')
                return redirect(url_for('manage_image'))

        if 'new_name' in request.form:
            image_file = request.form['image_file']
            new_name = request.form['new_name']
            if image_file and new_name:
                extension = os.path.splitext(image_file)[1]
                new_image_path = os.path.join(IMAGE_FOLDER, f'{new_name}{extension}')
                try:
                    os.rename(os.path.join(IMAGE_FOLDER, image_file), new_image_path)
                    flash(f"Image renamed successfully to {new_name}{extension}", 'success')
                except Exception as e:
                    flash(f"Error renaming image: {e}", 'error')
                return redirect(url_for('manage_image'))

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

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

@app.route('/get-countries', methods=['GET'])
def get_countries():
    countries = load_countries()
    return jsonify(countries)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    try:
        country = request.form.get('country')
        file = request.files.get('file')
        existing_image = request.form.get('existing_image')

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
                filename = existing_image
            else:
                filename = f"{uuid.uuid4()}.{file_ext}"
        else:
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
from flask import Flask, request, jsonify
# Define app, load_json, DEFAULT_JSON_FILE_PATH, current_json_file_path somewhere

@app.route('/edit_json')
def edit_json():
    global current_json_file_path
    current_json_file_path = DEFAULT_JSON_FILE_PATH
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    ajax = request.args.get('ajax', False, type=bool)
    
    all_data = load_json()
    total_items = len(all_data)
    
    total_pages = (total_items + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    current_page_data = all_data[start_idx:end_idx]
    
    if ajax:
        return jsonify({
            'data': current_page_data,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_items': total_items,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }})
    
    next_disabled = 'disabled' if page >= total_pages else ''
    prev_disabled = 'disabled' if page <= 1 else ''
    
    selected_10 = 'selected' if per_page == 10 else ''
    selected_20 = 'selected' if per_page == 20 else ''
    selected_50 = 'selected' if per_page == 50 else ''
    selected_100 = 'selected' if per_page == 100 else ''
    
    return f'''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="shortcut icon" href="#">
    <title>..::Amir's edit json::..</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }}

        body {{
            background-color: #72787e;
            color: #fff;
            padding: 20px;
        }}

        h1 {{
            text-align: center;
            margin-bottom: 20px;
            color: #ffc107;
        }}

        .container {{
            width: 80%;
            margin: 0 auto;
            padding: 20px;
            background-color: #495057;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }}

        #jsonTableContainer {{
            border: 2px solid #198754;
            padding: 10px;
            background-color: #6c757d;
            min-height: 100px;
            border-radius: 4px;
        }}

        .row {{
            display: flex;
            align-items: center;
            border-bottom: 1px solid #ddd;
            padding: 10px 0;
            transition: background-color 0.3s ease;
        }}

        .row:nth-child(odd) {{
            background-color: #6c757d;
        }}

        .row:hover {{
            background-color: #495057;
        }}

        .column {{
            flex: 1;
            text-align: center;
            padding: 5px;
            color: #fff;
        }}

        .thumbnail {{
            max-width: 50px;
            max-height: 50px;
            border-radius: 4px;
            cursor: pointer;
        }}

        .delete-btn {{
            color: #ff4d4d;
            cursor: pointer;
            font-weight: bold;
        }}

        a {{
            color: #ffc107;
            text-decoration: none;
        }}

        a:hover {{
            color: #fff;
            text-decoration: underline;
        }}

        .download-btn {{
            width: 100%;
            padding: 10px;
            background-color: #198754;
            color: #fff;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s ease;
        }}

        .download-btn:hover {{
            background-color: #145d37;
        }}

        .file-input {{
            margin-bottom: 20px;
            display: block;
            padding: 10px;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fff;
            color: #333;
        }}

        .header {{
            font-weight: bold;
            background-color: #198754;
            color: #fff;
        }}

        .add-row-btn {{
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
        }}

        .add-row-btn:hover {{
            background-color: #e0a800;
        }}

        .image-input {{
            width: 100%;
            padding: 5px;
            font-size: 14px;
            text-align: center;
        }}

        .modal {{
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
        }}

        .modal-content {{
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
        }}

        .modal img {{
            max-width: 100%;
            max-height: 400px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}

        .modal-close {{
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 20px;
            color: black;
            cursor: pointer;
        }}

        .modal h2,
        .modal p {{
            margin: 10px 0;
        }}

        .edit-form {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            text-align: left;
        }}

        .form-group {{
            margin-bottom: 15px;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}

        .form-group input,
        .form-group textarea,
        .form-group select {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}

        .form-group textarea {{
            height: 80px;
            resize: vertical;
        }}

        .save-btn {{
            grid-column: span 2;
            padding: 10px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }}

        .save-btn:hover {{
            background-color: #218838;
        }}

        .row.draggable {{
            cursor: move;
        }}

        .row.drag-over {{
            background-color: #495057;
        }}

        .image-filename {{
            margin-top: 10px;
            font-size: 14px;
            color: #333;
            text-align: center;
            font-weight: bold;
        }}

        .sortable {{
            cursor: pointer;
            position: relative;
        }}
        
        .sortable:after {{
            content: ' ⇅';
            font-size: 0.8em;
            color: #ccc;
            position: absolute;
            right: 5px;
        }}
        
        #uploadFileInput {{
            display: none;
        }}

        .btn-success {{
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
        }}

        .btn-success:hover {{
            background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
            text-decoration: none;
            color: white;
        }}

        .btn-success i {{
            margin-right: 8px;
            font-size: 16px;
        }}

        .btn-secondary {{
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
        }}

        .btn-secondary:hover {{
            background: linear-gradient(135deg, #5a6268 0%, #545b62 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(108, 117, 125, 0.4);
            color: white;
            text-decoration: none;
        }}

        .btn-secondary i {{
            margin-right: 8px;
            font-size: 16px;
        }}

        .file-input-label {{
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
        }}

        .file-input-label:hover {{
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.4);
        }}

        .file-input-label i {{
            margin-right: 8px;
        }}

        #uploadFileBtn {{
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
        }}

        #uploadFileBtn i {{
            margin-right: 8px;
        }}

        #uploadFileBtn:hover {{
            background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
        }}

        .delete-btn {{
            display: inline-flex;
            align-items: center;
            color: yellow;
            cursor: pointer;
            font-weight: bold;
        }}

        .delete-btn i {{
            margin-right: 8px;
        }}

        .delete-btn:hover {{
            color: red;
        }}

        .country-dropdown {{
            width: 100%;
            padding: 5px;
            font-size: 14px;
            text-align: center;
            background-color: #fff;
            color: #333;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}

        .drop-area {{
            border: 2px dashed #ccc;
            border-radius: 4px;
            padding: 20px;
            text-align: center;
            background-color: #f8f9fa;
            color: #333;
            margin: 10px 0;
            cursor: pointer;
        }}

        .drop-area.highlight {{
            border-color: #007bff;
            background-color: #e9f0ff;
        }}
        
        .currency-dropdown {{
            width: 100%;
            padding: 5px;
            font-size: 14px;
            text-align: center;
            background-color: #fff;
            color: #333;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        
        .image-drop-area {{
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
        }}

        .image-drop-area.highlight {{
            border-color: #007bff;
            background-color: #e9f0ff;
        }}

        .image-drop-area p {{
            margin: 0;
            font-size: 12px;
        }}
        
    .search-container {{
        margin-bottom: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }}

    .search-box {{
        width: 300px;
        padding: 10px;
        font-size: 16px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: #fff;
        color: #333;
    }}

    .search-box:focus {{
        outline: none;
        border-color: #007bff;
        box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
    }}

    .clear-search-btn {{
        padding: 10px;
        background-color: #dc3545;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .clear-search-btn:hover {{
        background-color: #c82333;
    }}
    
    .toast-message {{
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
    }}

    .filter-buttons {{
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-bottom: 20px;
    }}

    .filter-btn {{
        padding: 10px 15px;
        background-color: #6c757d;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        transition: background 0.3s ease;
    }}

    .filter-btn:hover {{
        background-color: #5a6268;
    }}

    .filter-btn.active {{
        background-color: #28a745;
    }}

    .search-container {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }}

    .search-box {{
        width: 100%;
        padding: 10px;
        font-size: 14px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: #fff;
        color: #333;
    }}

    .image-drop-areas-container {{
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }}

    .merge-drop-area {{
        flex: 1;
        min-height: 80px;
    }}

    .merge-options {{
        display: flex;
        gap: 15px;
        align-items: center;
        margin-bottom: 10px;
    }}

    .merge-options label {{
        display: flex;
        align-items: center;
        gap: 5px;
        color: #333;
        font-weight: normal;
    }}

    #mergeImagesBtn {{
        padding: 5px 10px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }}

    #mergeImagesBtn:disabled {{
        background-color: #6c757d;
        cursor: not-allowed;
    }}
    
    .merge-preview {{
        margin-top: 10px;
        padding: 10px;
        border: 2px dashed #007bff;
        border-radius: 5px;
        background-color: #f8f9fa;
    }}

    .merge-preview img {{
        max-width: 100%;
        max-height: 150px;
        margin: 5px;
        border: 1px solid #ddd;
    }}

    .merge-size-info {{
        font-size: 12px;
        color: #666;
        margin-top: 5px;
    }}

    .button-container {{
        display: flex;
        justify-content: center;
        gap: 10px;
        margin: 15px 0;
        flex-wrap: wrap;
    }}

        /* ===== MULTI-DONOR styles ===== */
        .donors-container {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
        }}
        .donor-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            padding: 8px;
            background-color: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .donor-item:last-child {{ margin-bottom: 0; }}
        .donor-input {{
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .donor-input:focus {{ border-color: #007bff; outline: none; }}
        .btn-remove-donor {{
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
            border: none;
            border-radius: 4px;
            width: 32px;
            height: 32px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .btn-remove-donor:hover {{ background: linear-gradient(135deg, #c82333 0%, #a71e2a 100%); }}
        .btn-add-donor {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
        }}
        .btn-add-donor:hover {{ background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%); }}
        /* ===== END MULTI-DONOR styles ===== */

        /* Add pagination styles */
        .pagination {{
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 20px 0;
    gap: 10px;
}}

.view-options {{
    display: flex;
    gap: 10px;
    margin-left: 20px;
}}

.show-all-btn, .show-pagination-btn {{
    padding: 8px 16px;
    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.3s ease;
}}

.show-all-btn:hover:not(:disabled), .show-pagination-btn:hover:not(:disabled) {{
    background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%);
    transform: translateY(-2px);
}}

.show-all-btn:disabled, .show-pagination-btn:disabled {{
    background: #6c757d;
    cursor: not-allowed;
    transform: none;
}}

.show-pagination-btn {{
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
}}

.show-pagination-btn:hover:not(:disabled) {{
    background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
}}

        .page-btn {{
            padding: 8px 16px;
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }}

        .page-btn:hover:not(:disabled) {{
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
            transform: translateY(-2px);
        }}

        .page-btn:disabled {{
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }}

        .page-info {{
            color: white;
            font-weight: bold;
            margin: 0 15px;
        }}

        .page-size-selector {{
            margin-left: 20px;
        }}

        .page-size-selector select {{
            padding: 5px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}

        .loading-spinner {{
            text-align: center;
            padding: 20px;
            color: white;
            font-size: 16px;
        }}

        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 2s linear infinite;
            margin: 0 auto 10px;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        .show-all-btn {{
    padding: 8px 16px;
    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.3s ease;
    margin-left: 10px;
}}

.show-all-btn:hover:not(:disabled) {{
    background: linear-gradient(135deg, #218838 0%, #1e9e8a 100%);
    transform: translateY(-2px);
}}

.show-all-btn:disabled {{
    background: #6c757d;
    cursor: not-allowed;
    transform: none;
}}

.show-pagination-btn {{
    padding: 8px 16px;
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.3s ease;
    margin-left: 10px;
}}

.show-pagination-btn:hover:not(:disabled) {{
    background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
    transform: translateY(-2px);
}}

.edit-btn:hover {{
    transform: scale(1.1);
    opacity: 0.8;
}}

@keyframes highlightRow {{
    0% {{
        background-color: #2c5530;
    }}
    100% {{
        background-color: transparent;
    }}
}}

.row-highlight {{
    animation: highlightRow 2s ease-out;
}}
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>

<body>
    <div id="toastMessage" class="toast-message">✅ Changes saved successfully!</div>

    <div class="container">
        <h1>JSON Viewer & Editor</h1>

        <div class="pagination" id="topPagination">
            <button class="page-btn" id="prevPage" {prev_disabled}>
                <i class="fas fa-chevron-left"></i> Previous
            </button>
            <span class="page-info" id="pageInfo">Page {page} of {total_pages}</span>
            <button class="page-btn" id="nextPage" {next_disabled}>
                Next <i class="fas fa-chevron-right"></i>
            </button>
            <div class="page-size-selector">
                <label for="pageSize" style="color: white;">Items per page:</label>
                <select id="pageSize">
                    <option value="10" {selected_10}>10</option>
                    <option value="20" {selected_20}>20</option>
                    <option value="50" {selected_50}>50</option>
                    <option value="100" {selected_100}>100</option>
                </select>
            </div>
            <div class="view-options">
                <button class="show-all-btn" id="showAllBtn">
                    <i class="fas fa-list"></i> Show All
                </button>
                <button class="show-pagination-btn" id="showPaginationBtn" style="display: none;">
                    <i class="fas fa-file-alt"></i> Show Pagination
                </button>
            </div>
        </div>

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

        <div id="jsonTableContainer">
            <div class="loading-spinner">
                <div class="spinner"></div>
                Loading data...
            </div>
        </div>

        <div class="pagination" id="bottomPagination">
            <button class="page-btn" id="prevPageBottom" {prev_disabled}>
                <i class="fas fa-chevron-left"></i> Previous
            </button>
            <span class="page-info" id="pageInfoBottom">Page {page} of {total_pages}</span>
            <button class="page-btn" id="nextPageBottom" {next_disabled}>
                Next <i class="fas fa-chevron-right"></i>
            </button>
            
            <div class="view-options">
                <button class="show-all-btn" id="showAllBtnBottom">
                    <i class="fas fa-list"></i> Show All
                </button>
                <button class="show-pagination-btn" id="showPaginationBtnBottom" style="display: none;">
                    <i class="fas fa-file-alt"></i> Show Pagination
                </button>
            </div>
        </div>

        <button class="add-row-btn" id="addRowBtn">Add New Row</button>
        <button class="download-btn" id="downloadBtn">Download Updated JSON</button>
        
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
                
                <!-- ===== MULTI-DONOR: donors UI in modal ===== -->
                <div class="form-group" style="grid-column: span 2;">
                    <label>Donors:</label>
                    <div class="donors-container" id="modalDonorsContainer"></div>
                    <button type="button" class="btn-add-donor" onclick="addModalDonor()">
                        <i class="fas fa-plus-circle"></i> Add Another Donor
                    </button>
                </div>
                <!-- ===== END MULTI-DONOR ===== -->
                
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
    
    <datalist id="modal-donor-suggestions"></datalist>

    <script>
// Global variables
let jsonData = [];
let sortOrder = 1;
let currentEditingIndex = -1;
let countriesData = [];
let activeFilters = {{
    country: '',
    size: '',
    yearFrom: '',
    yearTo: ''
}};
let isAddMode = false;

// ===== MULTI-DONOR: modal donors state =====
let modalDonorsList = [];
// ===== END MULTI-DONOR =====

// Pagination variables
let currentPage = {page};
let itemsPerPage = {per_page};
let totalPages = {total_pages};
let totalItems = {total_items};

function loadCountries() {{
    fetch('/get-countries')
        .then(response => response.json())
        .then(data => {{
            countriesData = data;
            populateCountryDropdowns();
        }})
        .catch(error => {{
            console.error("Error loading countries:", error);
        }});
}}

function populateCountryDropdowns() {{
    const editCountryDropdown = document.getElementById('editCountry');
    
    if (!editCountryDropdown) return;
    
    editCountryDropdown.innerHTML = '';
    
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select a country';
    editCountryDropdown.appendChild(defaultOption);
    
    countriesData.forEach(country => {{
        const option = document.createElement('option');
        option.value = country.name;
        option.textContent = country.name;
        editCountryDropdown.appendChild(option);
    }});
}}

function loadPageData(page = currentPage, perPage = itemsPerPage) {{
    showLoading();
    
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('per_page', perPage);
    params.append('ajax', 'true');
    
    if (activeFilters.country) params.append('country', activeFilters.country);
    if (activeFilters.size) params.append('size', activeFilters.size);
    if (activeFilters.yearFrom) params.append('yearFrom', activeFilters.yearFrom);
    if (activeFilters.yearTo) params.append('yearTo', activeFilters.yearTo);
    
    fetch(`/get-json?${{params.toString()}}`)
        .then(response => response.json())
        .then(data => {{
            jsonData = data.data;
            currentPage = data.pagination.current_page;
            itemsPerPage = data.pagination.per_page;
            totalPages = data.pagination.total_pages;
            totalItems = data.pagination.total_items;
            
            updatePaginationControls();
            renderTable(jsonData);
            hideLoading();
        }})
        .catch(error => {{
            console.error("Error fetching page data:", error);
            document.getElementById("jsonTableContainer").innerHTML = "Error loading data";
            hideLoading();
        }});
}}

function showLoading() {{
    const container = document.getElementById("jsonTableContainer");
    container.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            Loading data...
        </div>
    `;
}}

function hideLoading() {{
    // Loading is hidden when renderTable is called
}}

function updatePaginationControls() {{
    document.getElementById('pageInfo').textContent = `Page ${{currentPage}} of ${{totalPages}}`;
    document.getElementById('pageInfoBottom').textContent = `Page ${{currentPage}} of ${{totalPages}}`;
    
    document.getElementById('prevPage').disabled = currentPage <= 1;
    document.getElementById('prevPageBottom').disabled = currentPage <= 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages;
    document.getElementById('nextPageBottom').disabled = currentPage >= totalPages;
    
    document.getElementById('pageSize').value = itemsPerPage;
}}

function changePage(newPage) {{
    if (newPage < 1 || newPage > totalPages) return;
    
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('page', newPage);
    newUrl.searchParams.set('per_page', itemsPerPage);
    window.history.pushState({{}}, '', newUrl);
    
    loadPageData(newPage, itemsPerPage);
}}

function changePageSize(newSize) {{
    itemsPerPage = parseInt(newSize);
    
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('page', 1);
    newUrl.searchParams.set('per_page', itemsPerPage);
    window.history.pushState({{}}, '', newUrl);
    
    loadPageData(1, itemsPerPage);
}}

function renderTable(data) {{
    const tableContainer = document.getElementById("jsonTableContainer");
    if (!tableContainer) return;
    
    tableContainer.innerHTML = '';

    const headerRow = document.createElement('div');
    headerRow.classList.add('row', 'header');
    const headers = [
        {{ text: 'Country', key: 'country' }},
        {{ text: 'Currency Type', key: 'currency_type' }},
        {{ text: 'Donor Name', key: 'donor_name' }},
        {{ text: 'Image', key: 'image' }},
        {{ text: 'Note', key: 'note' }},
        {{ text: 'Size', key: 'size' }},
        {{ text: 'Year', key: 'year' }},
        {{ text: 'Actions', key: null }}
    ];
    
    headers.forEach(header => {{
        const column = document.createElement('div');
        column.classList.add('column');
        column.textContent = header.text;
        if (header.key) {{
            column.dataset.key = header.key;
            column.classList.add('sortable');
            column.addEventListener('click', () => {{
                sortTable(header.key);
            }});
        }}
        headerRow.appendChild(column);
    }});
    tableContainer.appendChild(headerRow);

    data.forEach((row, index) => {{
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

        countrySelect.addEventListener('change', function() {{
            const oldCountry = row.country;
            const newCountry = this.value;
            const image = row.image;

            if (!image || image === "" || image === "placeholder.jpg") {{
                row.country = newCountry;
                saveUpdates();
                return;
            }}

            fetch('/update-country', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    image: image,
                    old_country: oldCountry,
                    new_country: newCountry
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.error) {{
                    alert("Error: " + data.error);
                    this.value = oldCountry;
                }} else {{
                    console.log(data.message);
                    row.country = newCountry;
                    renderTable(jsonData);
                }}
            }})
            .catch(error => {{
                console.error("Error updating country:", error);
                this.value = oldCountry;
            }});
        }});

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select country';
        countrySelect.appendChild(defaultOption);
        
        countriesData.forEach(country => {{
            const option = document.createElement('option');
            option.value = country.name;
            option.textContent = country.name;
            if (row.country === country.name) {{
                option.selected = true;
            }}
            countrySelect.appendChild(option);
        }});
        
        if (row.country && !countriesData.some(c => c.name === row.country)) {{
            const option = document.createElement('option');
            option.value = row.country;
            option.textContent = row.country;
            option.selected = true;
            countrySelect.appendChild(option);
        }}
        
        countryColumn.appendChild(countrySelect);
        rowDiv.appendChild(countryColumn);
        
        // Currency type dropdown
        const currencyColumn = document.createElement('div');
        currencyColumn.classList.add('column');
        const currencySelect = document.createElement('select');
        currencySelect.classList.add('currency-dropdown');
        currencySelect.addEventListener('change', function() {{
            row.currency_type = this.value;
            saveUpdates();
        }});
        
        const currencyOptions = ['coin', 'paper-bill', 'antique'];
        currencyOptions.forEach(optionValue => {{
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionValue.charAt(0).toUpperCase() + optionValue.slice(1);
            if (row.currency_type === optionValue) {{
                option.selected = true;
            }}
            currencySelect.appendChild(option);
        }});
        
        currencyColumn.appendChild(currencySelect);
        rowDiv.appendChild(currencyColumn);
        
        // ===== MULTI-DONOR: donor column shows all donors =====
        const donorColumn = document.createElement('div');
        donorColumn.classList.add('column', 'editable');
        // Display all donors joined by comma; fallback to legacy donor_name
        let displayDonors = '';
        if (Array.isArray(row.donors) && row.donors.length > 0) {{
            displayDonors = row.donors.filter(d => d && d.trim()).join(', ');
        }} else if (row.donor_name) {{
            displayDonors = row.donor_name;
        }}
        donorColumn.textContent = displayDonors;
        donorColumn.contentEditable = true;
        donorColumn.addEventListener('blur', function() {{
            // When edited as a single string, split on commas to support multiple donors
            const rawValue = this.textContent || '';
            const splitDonors = rawValue.split(',').map(s => s.trim()).filter(Boolean);
            if (splitDonors.length > 1) {{
                row.donors = splitDonors;
                row.donor_name = splitDonors[0];
            }} else if (splitDonors.length === 1) {{
                row.donor_name = splitDonors[0];
                if ('donors' in row) delete row.donors;
            }} else {{
                row.donor_name = '';
                if ('donors' in row) delete row.donors;
            }}
            // Re-render the cell text to normalized form
            this.textContent = splitDonors.join(', ');
            saveUpdates();
        }});
        rowDiv.appendChild(donorColumn);
        // ===== END MULTI-DONOR donor column =====
        
        // Image column with drag and drop
        const imageColumn = document.createElement('div');
        imageColumn.classList.add('column');

        const dropArea = document.createElement('div');
        dropArea.classList.add('image-drop-area');
        dropArea.setAttribute('data-index', index);

        if (row.image && row.image !== '' && row.image !== 'placeholder.jpg') {{
            dropArea.innerHTML = `<img src="/images/${{row.country}}/${{row.image}}" 
                                    class="thumbnail" 
                                    data-index="${{index}}" 
                                    data-image="${{row.image}}"
                                    data-id="${{row.id}}"
                                    style="cursor: pointer; max-width: 50px; max-height: 50px;"
                                    onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'50\\' height=\\'50\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'%23999\\' stroke-width=\\'2\\' stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\'%3E%3Crect x=\\'3\\' y=\\'3\\' width=\\'18\\' height=\\'18\\' rx=\\'2\\' ry=\\'2\\'%3E%3C/rect%3E%3Ccircle cx=\\'8.5\\' cy=\\'8.5\\' r=\\'1.5\\'%3E%3C/circle%3E%3Cpolyline points=\\'21 15 16 10 5 21\\'%3E%3C/polyline%3E%3C/svg%3E'"
                                    onclick="event.stopPropagation(); editExistingItem('${{row.id}}')">`;
        }} else {{
            dropArea.innerHTML = `<div style="text-align: center; padding: 5px;">
                                    <i class="fas fa-plus-circle" style="font-size: 24px; color: #28a745; margin-bottom: 5px; display: block;"></i>
                                    <small style="color: #fff;">Click to add image</small>
                                  </div>`;
            dropArea.style.cursor = 'pointer';
            dropArea.onclick = (e) => {{
                e.stopPropagation();
                editExistingItem(row.id);
            }};
        }}

        setupImageDropArea(dropArea, row, index);
        imageColumn.appendChild(dropArea);
        rowDiv.appendChild(imageColumn);
        
        // Note (editable)
        const noteColumn = document.createElement('div');
        noteColumn.classList.add('column', 'editable');
        noteColumn.textContent = row.note || "";
        noteColumn.contentEditable = true;
        noteColumn.addEventListener('blur', function() {{
            row.note = this.textContent;
            saveUpdates();
        }});
        rowDiv.appendChild(noteColumn);
        
        // Size (editable)
        const sizeColumn = document.createElement('div');
        sizeColumn.classList.add('column', 'editable');
        sizeColumn.textContent = row.size || "";
        sizeColumn.contentEditable = true;
        sizeColumn.addEventListener('blur', function() {{
            row.size = this.textContent;
            saveUpdates();
        }});
        rowDiv.appendChild(sizeColumn);
        
        // Year (editable)
        const yearColumn = document.createElement('div');
        yearColumn.classList.add('column', 'editable');
        yearColumn.textContent = row.year || "";
        yearColumn.contentEditable = true;
        yearColumn.addEventListener('blur', function() {{
            row.year = this.textContent;
            saveUpdates();
        }});
        rowDiv.appendChild(yearColumn);
        
        // Actions
        const actionColumn = document.createElement('div');
        actionColumn.classList.add('column');
        
        const editBtn = document.createElement('span');
        editBtn.classList.add('edit-btn');
        editBtn.innerHTML = '<i class="fas fa-edit" style="color: #28a745; cursor: pointer; margin-right: 10px; font-size: 18px;"></i>';
        editBtn.addEventListener('click', function() {{
            editExistingItem(row.id);
        }});
        actionColumn.appendChild(editBtn);

        const deleteBtn = document.createElement('span');
        deleteBtn.classList.add('delete-btn');
        deleteBtn.innerHTML = '<i class="fas fa-trash" style="color: #ff4d4d; cursor: pointer; font-size: 18px;"></i>';
        deleteBtn.addEventListener('click', function() {{
            if (confirm('Are you sure you want to delete this entry?')) {{
                if (row.image && row.image !== '' && row.image !== 'placeholder.jpg') {{
                    fetch('/delete-image', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            country: row.country,
                            image: row.image
                        }})
                    }}).catch(err => console.error('Error deleting image:', err));
                }}
                jsonData.splice(index, 1);
                renderTable(jsonData);
                saveUpdates();
            }}
        }});
        actionColumn.appendChild(deleteBtn);
        rowDiv.appendChild(actionColumn);

        tableContainer.appendChild(rowDiv);
    }});
    
    lazyLoadImages();
}}

function lazyLoadImages() {{
    const imageObserver = new IntersectionObserver((entries, observer) => {{
        entries.forEach(entry => {{
            if (entry.isIntersecting) {{
                const img = entry.target;
                const dataSrc = img.getAttribute('data-src');
                if (dataSrc) {{
                    img.src = dataSrc;
                    img.removeAttribute('data-src');
                }}
                observer.unobserve(img);
            }}
        }});
    }});

    document.querySelectorAll('.thumbnail[data-src]').forEach(img => {{
        imageObserver.observe(img);
    }});
}}

function setupImageDropArea(dropArea, row, index) {{
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);
    
    dropArea.addEventListener('click', () => {{
        fileInput.click();
    }});
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
        dropArea.addEventListener(eventName, preventDefaults, false);
    }});
    
    function preventDefaults(e) {{
        e.preventDefault();
        e.stopPropagation();
    }}
    
    ['dragenter', 'dragover'].forEach(eventName => {{
        dropArea.addEventListener(eventName, highlight, false);
    }});
    
    ['dragleave', 'drop'].forEach(eventName => {{
        dropArea.addEventListener(eventName, unhighlight, false);
    }});
    
    function highlight() {{
        dropArea.classList.add('highlight');
    }}
    
    function unhighlight() {{
        dropArea.classList.remove('highlight');
    }}
    
    dropArea.addEventListener('drop', handleDropFile, false);
    
    fileInput.addEventListener('change', handleFileSelect, false);
    
    function handleDropFile(e) {{
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files, row, index);
    }}
    
    function handleFileSelect(e) {{
        const files = e.target.files;
        handleFiles(files, row, index);
    }}
    
    function handleFiles(files, row, index) {{
        if (files.length === 0) return;
        
        const file = files[0];
        const country = row.country;
        
        if (!country) {{
            alert('Please select a country first');
            return;
        }}
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('country', country);

        if (row.image && row.image !== "placeholder.jpg") {{
            formData.append('existing_image', row.image);
        }}

        fetch('/upload-image', {{
            method: 'POST',
            body: formData
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.error) {{
                alert('Error uploading image: ' + data.error);
            }} else {{
                jsonData[index].image = data.filename;
                renderTable(jsonData);
                saveUpdates();
            }}
        }})
        .catch(error => {{
            console.error('Error:', error);
            alert('Error uploading image');
        }});
    }}
}}

function sortTable(key) {{
    jsonData.sort((a, b) => {{
        if (a[key] < b[key]) return -1 * sortOrder;
        if (a[key] > b[key]) return 1 * sortOrder;
        return 0;
    }});
    sortOrder *= -1;
    renderTable(jsonData);
    
    fetch('/update-json', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
        }},
        body: JSON.stringify(jsonData)
    }})
    .then(response => response.json())
    .then(data => {{
        if (data.message) {{
            console.log('Backend JSON updated successfully:', data.message);
        }} else {{
            console.error('Error updating JSON:', data.error);
            alert(`Error updating JSON: ${{data.error}}`);
        }}
    }})
    .catch(error => {{
        console.error('Error with fetch request:', error);
        alert('An error occurred while updating the JSON file.');
    }});
}}

function handleDragStart(e) {{
    e.dataTransfer.setData('text/plain', e.target.getAttribute('data-index'));
}}

function handleDragOver(e) {{
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}}

function handleDrop(e) {{
    e.preventDefault();
    const draggedIndex = e.dataTransfer.getData('text/plain');
    const targetIndex = e.target.closest('.row').getAttribute('data-index');

    if (draggedIndex !== targetIndex) {{
        const draggedItem = jsonData.splice(draggedIndex, 1)[0];
        jsonData.splice(targetIndex, 0, draggedItem);
        renderTable(jsonData);
        saveUpdates();
    }}
}}

function showToast(message) {{
    const toast = document.getElementById("toastMessage");
    if (!toast) return;
    
    toast.textContent = "✅ " + message;
    toast.style.display = "block";
    toast.style.opacity = "1";

    setTimeout(() => {{
        toast.style.opacity = "0";
    }}, 3000);

    setTimeout(() => {{
        toast.style.display = "none";
    }}, 4000);
}}

function saveUpdates() {{
    fetch('/update-json', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(jsonData),
    }})
    .then(response => response.json())
    .then(data => {{
        if (data.message) {{
            console.log(data.message);
            showToast(data.message || "Changes saved!");
        }} else if (data.error) {{
            console.error("Error:", data.error);
            showToast("❌ Error saving changes: " + data.error, 'error');
        }}
    }})
    .catch(error => {{
        console.error("Error:", error);
        showToast("❌ Error saving changes!", 'error');
    }});
}}

function filterTable() {{
    console.log('Using server-side filtering');
}}

function applyFilters() {{
    const countryFilter = document.getElementById('countrySearch').value;
    const sizeFilter = document.getElementById('sizeSearch').value;
    const yearFromFilter = document.getElementById('yearFromSearch').value;
    const yearToFilter = document.getElementById('yearToSearch').value;
    
    const params = new URLSearchParams();
    if (countryFilter) params.append('country', countryFilter);
    if (sizeFilter) params.append('size', sizeFilter);
    if (yearFromFilter) params.append('yearFrom', yearFromFilter);
    if (yearToFilter) params.append('yearTo', yearToFilter);
    params.append('ajax', 'true');
    params.append('page', '1');
    params.append('per_page', itemsPerPage);
    
    showLoading();
    
    fetch(`/get-json?${{params.toString()}}`)
        .then(response => response.json())
        .then(result => {{
            jsonData = result.data;
            currentPage = result.pagination.current_page;
            itemsPerPage = result.pagination.per_page;
            totalPages = result.pagination.total_pages;
            totalItems = result.pagination.total_items;
            
            updatePaginationControls();
            renderTable(jsonData);
            hideLoading();
            
            activeFilters = {{
                country: countryFilter,
                size: sizeFilter,
                yearFrom: yearFromFilter,
                yearTo: yearToFilter
            }};
            
            if (countryFilter || sizeFilter || yearFromFilter || yearToFilter) {{
                showToast(`Filters applied. Found ${{totalItems}} items.`);
            }}
        }})
        .catch(error => {{
            console.error("Error applying filters:", error);
            document.getElementById("jsonTableContainer").innerHTML = "Error applying filters";
            hideLoading();
        }});
}}

function clearFilters() {{
    document.getElementById('countrySearch').value = '';
    document.getElementById('sizeSearch').value = '';
    document.getElementById('yearFromSearch').value = '';
    document.getElementById('yearToSearch').value = '';
    
    activeFilters = {{
        country: '',
        size: '',
        yearFrom: '',
        yearTo: ''
    }};
    
    showLoading();
    
    fetch(`/get-json?page=1&per_page=${{itemsPerPage}}&ajax=true`)
        .then(response => response.json())
        .then(result => {{
            jsonData = result.data;
            currentPage = result.pagination.current_page;
            itemsPerPage = result.pagination.per_page;
            totalPages = result.pagination.total_pages;
            totalItems = result.pagination.total_items;
            
            updatePaginationControls();
            renderTable(jsonData);
            hideLoading();
            showToast('Filters cleared');
        }})
        .catch(error => {{
            console.error("Error clearing filters:", error);
            document.getElementById("jsonTableContainer").innerHTML = "Error loading data";
            hideLoading();
        }});
}}

function toggleAddMode() {{
    isAddMode = !isAddMode;
    const button = document.getElementById('toggleAddMode');
    
    if (isAddMode) {{
        button.classList.add('active');
        button.textContent = 'Exit Add Mode';
        document.body.style.backgroundColor = '#2c5530';
    }} else {{
        button.classList.remove('active');
        button.textContent = 'Add New Mode';
        document.body.style.backgroundColor = '#72787e';
    }}
}}

// ===== MULTI-DONOR: modal donor rendering =====
function renderModalDonors() {{
    const container = document.getElementById('modalDonorsContainer');
    if (!container) return;
    container.innerHTML = '';
    
    if (modalDonorsList.length === 0) modalDonorsList.push('');
    
    modalDonorsList.forEach((donor, index) => {{
        const div = document.createElement('div');
        div.className = 'donor-item';
        
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'donor-input';
        input.value = donor || '';
        input.placeholder = 'Donor name';
        input.setAttribute('list', 'modal-donor-suggestions');
        input.addEventListener('input', function() {{
            modalDonorsList[index] = this.value;
            // Live-update the underlying row data
            if (currentEditingIndex !== -1) {{
                const cleaned = modalDonorsList.map(d => (d || '').trim()).filter(Boolean);
                if (cleaned.length > 1) {{
                    jsonData[currentEditingIndex].donors = cleaned;
                    jsonData[currentEditingIndex].donor_name = cleaned[0];
                }} else if (cleaned.length === 1) {{
                    jsonData[currentEditingIndex].donor_name = cleaned[0];
                    delete jsonData[currentEditingIndex].donors;
                }}
            }}
            fetchModalDonorSuggestions(this.value);
        }});
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn-remove-donor';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.title = 'Remove donor';
        removeBtn.onclick = function() {{ removeModalDonor(index); }};
        
        div.appendChild(input);
        div.appendChild(removeBtn);
        container.appendChild(div);
    }});
}}

function addModalDonor() {{
    modalDonorsList.push('');
    renderModalDonors();
    const inputs = document.querySelectorAll('#modalDonorsContainer .donor-input');
    if (inputs.length) inputs[inputs.length - 1].focus();
}}

function removeModalDonor(index) {{
    if (modalDonorsList.length <= 1) {{
        showToast('At least one donor is required', 'error');
        return;
    }}
    modalDonorsList.splice(index, 1);
    renderModalDonors();
    // Sync back to underlying row
    if (currentEditingIndex !== -1) {{
        const cleaned = modalDonorsList.map(d => (d || '').trim()).filter(Boolean);
        if (cleaned.length > 1) {{
            jsonData[currentEditingIndex].donors = cleaned;
            jsonData[currentEditingIndex].donor_name = cleaned[0];
        }} else if (cleaned.length === 1) {{
            jsonData[currentEditingIndex].donor_name = cleaned[0];
            delete jsonData[currentEditingIndex].donors;
        }}
    }}
    saveUpdates();
}}

function fetchModalDonorSuggestions(query) {{
    const datalist = document.getElementById('modal-donor-suggestions');
    if (!query || query.trim().length < 2) {{
        datalist.innerHTML = '';
        return;
    }}
    fetch(`/suggest-donors?q=${{encodeURIComponent(query.trim())}}`)
        .then(r => r.json())
        .then(suggestions => {{
            datalist.innerHTML = '';
            suggestions.forEach(name => {{
                const opt = document.createElement('option');
                opt.value = name;
                datalist.appendChild(opt);
            }});
        }})
        .catch(err => console.error('Modal donor suggestions error:', err));
}}
// ===== END MULTI-DONOR modal donor rendering =====

document.addEventListener("DOMContentLoaded", function () {{
    document.getElementById('showAllBtn').addEventListener('click', showAllEntries);
    document.getElementById('showAllBtnBottom').addEventListener('click', showAllEntries);
    document.getElementById('showPaginationBtn').addEventListener('click', showPaginationView);
    document.getElementById('showPaginationBtnBottom').addEventListener('click', showPaginationView);

    loadPageData(currentPage, itemsPerPage);
    loadCountries();

    document.getElementById('prevPage').addEventListener('click', () => changePage(currentPage - 1));
    document.getElementById('nextPage').addEventListener('click', () => changePage(currentPage + 1));
    document.getElementById('prevPageBottom').addEventListener('click', () => changePage(currentPage - 1));
    document.getElementById('nextPageBottom').addEventListener('click', () => changePage(currentPage + 1));
    document.getElementById('pageSize').addEventListener('change', (e) => changePageSize(e.target.value));

    document.getElementById("uploadFileBtn").addEventListener("click", function () {{
        const fileInput = document.getElementById("uploadFileInput");
        const file = fileInput.files[0];

        if (!file) {{
            alert("Please select a file to upload.");
            return;
        }}

        const formData = new FormData();
        formData.append("file", file);

        fetch('/upload-json', {{
            method: 'POST',
            body: formData
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.message) {{
                alert(data.message);
                fetch('/get-json')
                    .then(response => response.json())
                    .then(newData => {{
                        jsonData = newData;
                        renderTable(jsonData);
                    }});
            }} else {{
                alert(data.error || "An error occurred.");
            }}
        }})
        .catch(error => {{
            console.error("Error:", error);
            alert("An error occurred while uploading the file.");
        }});
    }});

document.getElementById("addRowBtn").addEventListener("click", function () {{

    function generateUUID() {{
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        }});
    }}
    
    const newId = generateUUID();

    const newRow = {{
        id: newId,
        country: "",
        currency_type: "coin",
        donor_name: "",
        image: "",
        note: "",
        size: "",
        year: "",
        hidden_note: "",
        timestamp: new Date().toISOString()
    }};
    
    jsonData.unshift(newRow);
    renderTable(jsonData);
    
    fetch('/update-json', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(jsonData),
    }})
    .then(response => response.json())
    .then(data => {{
        if (data.message) {{
            showToast("✓ New row created and saved!");
            console.log("New row saved with ID:", newId);
            verifySave(newId);
        }} else {{
            showToast("⚠ Row created but save may have failed");
        }}
    }})
    .catch(error => {{
        console.error("Error saving new row:", error);
        showToast("❌ Error saving new row!", 'error');
    }});
    
    setTimeout(() => {{
        const rows = document.querySelectorAll('.row');
        if (rows.length > 1) {{
            rows[1].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            rows[1].style.backgroundColor = '#2c5530';
            setTimeout(() => {{
                if (rows[1]) rows[1].style.backgroundColor = '';
            }}, 2000);
        }}
    }}, 100);
}});

function verifySave(newId) {{
    setTimeout(() => {{
        fetch('/get-json')
            .then(response => response.json())
            .then(data => {{
                const found = data.some(item => item.id === newId);
                if (found) {{
                    console.log("✓ Verified: New row with ID", newId, "exists in the JSON file");
                }} else {{
                    console.error("✗ Warning: New row with ID", newId, "not found in JSON file");
                }}
            }});
    }}, 1000);
}}

    document.getElementById("downloadBtn").addEventListener("click", function () {{
        const jsonString = JSON.stringify(jsonData, null, 2);
        const blob = new Blob([jsonString], {{ type: "application/json" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "coins.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }});

    document.getElementById("closeModal").addEventListener("click", function () {{
        document.getElementById("imageModal").style.display = "none";
    }});

    document.getElementById("applyFilters").addEventListener("click", applyFilters);
    document.getElementById("clearFilters").addEventListener("click", clearFilters);
    document.getElementById("toggleAddMode").addEventListener("click", toggleAddMode);
    document.getElementById("clearSearch").addEventListener("click", clearFilters);

    document.getElementById("countrySearch").addEventListener("input", applyFilters);
    document.getElementById("sizeSearch").addEventListener("input", applyFilters);
    document.getElementById("yearFromSearch").addEventListener("input", applyFilters);
    document.getElementById("yearToSearch").addEventListener("input", applyFilters);

    document.getElementById("uploadFileInput").addEventListener("change", function (event) {{
        const file = event.target.files[0];

        if (!file) {{
            alert("No file selected. Please select a JSON file.");
            return;
        }}

        if (file.type !== "application/json") {{
            alert("Invalid file type. Please upload a valid JSON file.");
            return;
        }}

        const reader = new FileReader();
        reader.onload = function (e) {{
            try {{
                jsonData = JSON.parse(e.target.result);
                renderTable(jsonData);
            }} catch (error) {{
                alert("Error parsing JSON file. Please check the file format.");
                console.error("JSON Parsing Error:", error);
            }}
        }};

        reader.onerror = function () {{
            alert("Error reading the file. Please try again.");
        }};

        reader.readAsText(file);
    }});

    // Modal click - open editor
    document.addEventListener("click", function (event) {{
        if (event.target.classList.contains("thumbnail")) {{
            const index = event.target.getAttribute("data-index");
            const row = jsonData[index];
            
            document.getElementById("modalImage").src = `images/${{row.country}}/${{row.image}}`;
            document.getElementById("imageFileName").textContent = row.image;
            
            document.getElementById("editCountry").value = row.country || "";
            document.getElementById("editCurrencyType").value = row.currency_type || "";
            document.getElementById("editNote").value = row.note || "";
            document.getElementById("editSize").value = row.size || "";
            document.getElementById("editYear").value = row.year || "";
            document.getElementById("editHiddenNote").value = row.hidden_note || "";

            // ===== MULTI-DONOR: load donors into modal =====
            if (Array.isArray(row.donors) && row.donors.length > 0) {{
                modalDonorsList = row.donors.filter(d => d && d.trim());
            }} else if (row.donor_name && row.donor_name.trim()) {{
                modalDonorsList = [row.donor_name.trim()];
            }} else {{
                modalDonorsList = [''];
            }}
            renderModalDonors();
            // ===== END MULTI-DONOR =====
            
            currentEditingIndex = index;
            document.getElementById("imageModal").style.display = "flex";
            
            document.getElementById('mergeDropArea1').innerHTML = '<p>Drag & drop first image here</p>';
            document.getElementById('mergeDropArea2').innerHTML = '<p>Drag & drop second image here</p>';
            document.getElementById('modalMergeImagesBtn').disabled = true;
        }}
    }});

    function setupModalAutoSave() {{
        const fields = [
            {{ id: "editCountry", key: "country", type: "select" }},
            {{ id: "editCurrencyType", key: "currency_type", type: "select" }},
            {{ id: "editNote", key: "note", type: "textarea" }},
            {{ id: "editSize", key: "size", type: "input" }},
            {{ id: "editYear", key: "year", type: "input" }},
            {{ id: "editHiddenNote", key: "hidden_note", type: "textarea" }}
        ];

        fields.forEach(field => {{
            const element = document.getElementById(field.id);
            if (!element) return;

            if (field.type === "select") {{
                element.addEventListener("change", function() {{
                    if (currentEditingIndex !== -1) {{
                        jsonData[currentEditingIndex][field.key] = this.value;
                        saveUpdates();
                    }}
                }});
            }} else {{
                element.addEventListener("blur", function() {{
                    if (currentEditingIndex !== -1) {{
                        jsonData[currentEditingIndex][field.key] = this.value;
                        saveUpdates();
                    }}
                }});
            }}
        }});
    }}

    function setupModalImageUpload() {{
        const dropArea = document.getElementById('modalImageDropArea');
        const fileInput = document.getElementById('editImageInput');
        
        if (!dropArea || !fileInput) return;
        
        dropArea.addEventListener('click', () => {{
            fileInput.click();
        }});
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
            dropArea.addEventListener(eventName, preventDefaults, false);
        }});
        
        function preventDefaults(e) {{
            e.preventDefault();
            e.stopPropagation();
        }}
        
        ['dragenter', 'dragover'].forEach(eventName => {{
            dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
        }});
        
        ['dragleave', 'drop'].forEach(eventName => {{
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
        }});
        
        dropArea.addEventListener('drop', handleDropFile, false);
        fileInput.addEventListener('change', handleFileSelect, false);
        
        function handleDropFile(e) {{
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }}
        
        function handleFileSelect(e) {{
            const files = e.target.files;
            handleFiles(files);
        }}
        
        function handleFiles(files) {{
            if (files.length === 0) return;
            
            const file = files[0];
            const country = document.getElementById('editCountry').value;
            
            if (!country) {{
                alert('Please select a country first');
                return;
            }}
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('country', country);
            
            if (currentEditingIndex !== -1 && jsonData[currentEditingIndex].image && jsonData[currentEditingIndex].image !== "placeholder.jpg") {{
                formData.append('existing_image', jsonData[currentEditingIndex].image);
            }}
            
            fetch('/upload-image', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.error) {{
                    alert('Error uploading image: ' + data.error);
                }} else {{
                    if (currentEditingIndex !== -1) {{
                        jsonData[currentEditingIndex].image = data.filename;
                        renderTable(jsonData);
                        saveUpdates();
                        document.getElementById("modalImage").src = `images/${{country}}/${{data.filename}}`;
                        document.getElementById("imageFileName").textContent = data.filename;
                    }}
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                alert('Error uploading image');
            }});
        }}
    }}

    function setupModalImageMerging() {{
        let mergeImage1 = null;
        let mergeImage2 = null;

        const mergeDropArea1 = document.getElementById('mergeDropArea1');
        const mergeDropArea2 = document.getElementById('mergeDropArea2');
        const mergeImagesBtn = document.getElementById('modalMergeImagesBtn');

        function setupMergeDropArea(dropArea, imageNumber) {{
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
            
            dropArea.addEventListener('click', () => fileInput.click());
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                dropArea.addEventListener(eventName, preventDefaults, false);
            }});
            
            ['dragenter', 'dragover'].forEach(eventName => {{
                dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
            }});
            
            ['dragleave', 'drop'].forEach(eventName => {{
                dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
            }});
            
            dropArea.addEventListener('drop', function(e) {{
                handleMergeFileDrop(e, imageNumber);
            }}, false);
            
            fileInput.addEventListener('change', function(e) {{
                handleMergeFileSelect(e, imageNumber);
            }});

            function preventDefaults(e) {{
                e.preventDefault();
                e.stopPropagation();
            }}

            function handleMergeFileDrop(e, imageNumber) {{
                const dt = e.dataTransfer;
                const files = dt.files;
                handleMergeFiles(files, imageNumber);
            }}

            function handleMergeFileSelect(e, imageNumber) {{
                const files = e.target.files;
                handleMergeFiles(files, imageNumber);
            }}

            function handleMergeFiles(files, imageNumber) {{
                if (files.length === 0) return;
                
                const file = files[0];
                if (!file.type.startsWith('image/')) {{
                    alert('Please select an image file');
                    return;
                }}
                
                const reader = new FileReader();
                reader.onload = function(e) {{
                    const fileSizeKB = Math.round(file.size / 1024);
                    const htmlContent = '<img src="' + e.target.result + '" style="max-width: 100%; max-height: 70px;">' +
                                       '<div style="font-size: 10px; margin-top: 5px;">' +
                                       file.name + '<br>' + file.type + ' (' + fileSizeKB + 'KB)' +
                                       '</div>';
                    
                    if (imageNumber === 1) {{
                        mergeImage1 = file;
                        mergeDropArea1.innerHTML = htmlContent;
                    }} else {{
                        mergeImage2 = file;
                        mergeDropArea2.innerHTML = htmlContent;
                    }}
                    
                    if (mergeImage1 && mergeImage2) {{
                        mergeImagesBtn.disabled = false;
                    }}
                }};
                reader.readAsDataURL(file);
            }}
        }}

        setupMergeDropArea(mergeDropArea1, 1);
        setupMergeDropArea(mergeDropArea2, 2);

        mergeImagesBtn.addEventListener('click', function() {{
            if (!mergeImage1 || !mergeImage2) {{
                alert('Please upload both images first');
                return;
            }}
            
            const mergeDirection = document.querySelector('input[name="mergeDirection"]:checked').value;
            const resizeOption = document.querySelector('input[name="resizeOption"]:checked').value;
            const country = document.getElementById('editCountry').value;
            
            if (!country) {{
                alert('Please select a country first');
                return;
            }}

            const formData = new FormData();
            formData.append('image1', mergeImage1);
            formData.append('image2', mergeImage2);
            formData.append('direction', mergeDirection);
            formData.append('country', country);
            formData.append('resizeOption', resizeOption);

            const originalText = mergeImagesBtn.textContent;
            mergeImagesBtn.textContent = 'Merging...';
            mergeImagesBtn.disabled = true;

            fetch('/merge-images-upload', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.error) {{
                    alert('Error merging images: ' + data.error);
                }} else {{
                    alert('Images merged successfully!');
                    if (currentEditingIndex !== -1) {{
                        jsonData[currentEditingIndex].image = data.filename;
                        renderTable(jsonData);
                        saveUpdates();
                        document.getElementById("modalImage").src = `images/${{country}}/${{data.filename}}`;
                        document.getElementById("imageFileName").textContent = data.filename;
                    }}
                    mergeImage1 = null;
                    mergeImage2 = null;
                    mergeDropArea1.innerHTML = '<p>Drag & drop first image here</p>';
                    mergeDropArea2.innerHTML = '<p>Drag & drop second image here</p>';
                    mergeImagesBtn.disabled = true;
                }}
            }})
            .catch(error => {{
                console.error('Error merging images:', error);
                alert('Error merging images: ' + error.message);
            }})
            .finally(() => {{
                mergeImagesBtn.textContent = originalText;
                mergeImagesBtn.disabled = false;
            }});
        }});
    }}

    setupModalAutoSave();
    setupModalImageUpload();
    setupModalImageMerging();
}});

function showAllEntries() {{
    fetch('/get-json-stats')
        .then(response => response.json())
        .then(stats => {{
            if (stats.total_items > 500) {{
                if (!confirm(`⚠️ Warning: This will load ${{stats.total_items}} items (${{stats.file_size_mb}} MB).\\n\\nThis might be very slow on large collections.\\n\\nContinue anyway?`)) {{
                    return;
                }}
            }}
            loadAllEntries();
        }})
        .catch(() => {{
            if (confirm('⚠️ Loading all items may be slow. Continue?')) {{
                loadAllEntries();
            }}
        }});
}}

function loadAllEntries() {{
    showLoading();
    
    fetch('/get-all-json')
        .then(response => response.json())
        .then(data => {{
            if (data.error) {{
                throw new Error(data.error);
            }}
            
            jsonData = data;
            renderTable(jsonData);
            
            document.getElementById('prevPage').style.display = 'none';
            document.getElementById('nextPage').style.display = 'none';
            document.getElementById('prevPageBottom').style.display = 'none';
            document.getElementById('nextPageBottom').style.display = 'none';
            document.getElementById('pageInfo').style.display = 'none';
            document.getElementById('pageInfoBottom').style.display = 'none';
            document.getElementById('pageSize').style.display = 'none';
            document.querySelector('.page-size-selector label').style.display = 'none';
            
            document.getElementById('showAllBtn').style.display = 'none';
            document.getElementById('showAllBtnBottom').style.display = 'none';
            document.getElementById('showPaginationBtn').style.display = 'inline-block';
            document.getElementById('showPaginationBtnBottom').style.display = 'inline-block';
            
            const existingCount = document.getElementById('allItemsCount');
            if (existingCount) {{
                existingCount.remove();
            }}
            
            const itemCount = document.createElement('div');
            itemCount.id = 'allItemsCount';
            itemCount.style.cssText = 'text-align: center; color: white; font-weight: bold; margin: 10px 0; padding: 10px; background-color: rgba(0,0,0,0.3); border-radius: 4px;';
            itemCount.textContent = `📊 Showing all ${{jsonData.length}} items`;
            
            const tableContainer = document.getElementById('jsonTableContainer');
            tableContainer.parentNode.insertBefore(itemCount, tableContainer);
            
            hideLoading();
            showToast(`Loaded all ${{jsonData.length}} items`);
        }})
        .catch(error => {{
            console.error("Error fetching all data:", error);
            document.getElementById("jsonTableContainer").innerHTML = `
                <div style="text-align: center; color: #ff6b6b; padding: 20px;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 10px;"></i>
                    <h3>Error loading data</h3>
                    <p>${{error.message || 'Failed to load all items'}}</p>
                    <button onclick="showPaginationView()" class="btn-success" style="margin-top: 10px;">
                        <i class="fas fa-file-alt"></i> Return to Pagination View
                    </button>
                </div>
            `;
            hideLoading();
        }});
}}

function showPaginationView() {{
    document.getElementById('prevPage').style.display = 'inline-block';
    document.getElementById('nextPage').style.display = 'inline-block';
    document.getElementById('prevPageBottom').style.display = 'inline-block';
    document.getElementById('nextPageBottom').style.display = 'inline-block';
    document.getElementById('pageInfo').style.display = 'inline-block';
    document.getElementById('pageInfoBottom').style.display = 'inline-block';
    document.getElementById('pageSize').style.display = 'inline-block';
    document.querySelector('.page-size-selector label').style.display = 'inline-block';
    
    document.getElementById('showAllBtn').style.display = 'inline-block';
    document.getElementById('showAllBtnBottom').style.display = 'inline-block';
    document.getElementById('showPaginationBtn').style.display = 'none';
    document.getElementById('showPaginationBtnBottom').style.display = 'none';
    
    const itemCount = document.getElementById('allItemsCount');
    if (itemCount) {{
        itemCount.remove();
    }}
    
    loadPageData(1, itemsPerPage);
    showToast('Switched to pagination view');
}}

function editExistingItem(Id) {{
    window.open(`/edit-item/${{Id}}`, '_blank');
}}
</script>
 
</body>

</html>
    '''

@app.route('/box_country_list.html')
def box_country_list():
    return send_from_directory('.', 'box_country_list.html')

@app.route('/get-json', methods=['GET'])
def get_json():
    """Get JSON data with pagination support"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    ajax = request.args.get('ajax', False, type=bool)
    
    filters = {}
    country = request.args.get('country', '')
    size = request.args.get('size', '')
    year_from = request.args.get('yearFrom', '')
    year_to = request.args.get('yearTo', '')
    
    if country:
        filters['country'] = country
    if size:
        filters['size'] = size
    if year_from:
        filters['yearFrom'] = year_from
    if year_to:
        filters['yearTo'] = year_to
    
    result = get_paginated_data(page, per_page, filters if filters else None)
    
    if ajax:
        return jsonify(result)
    
    return jsonify(result['data'])


def get_paginated_data(page=1, per_page=20, filters=None):
    """Get paginated data with optional filtering"""
    all_data = load_json()
    
    if filters:
        all_data = apply_filters_to_data(all_data, filters)
    
    total_items = len(all_data)
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    page_data = all_data[start_idx:end_idx]
    
    return {
        'data': page_data,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    }

def apply_filters_to_data(data, filters):
    """Apply filters to data efficiently"""
    if not filters:
        return data
    
    filtered_data = []
    country_filter = filters.get('country', '').lower()
    size_filter = filters.get('size', '').lower()
    year_from = filters.get('yearFrom')
    year_to = filters.get('yearTo')
    
    for item in data:
        if country_filter and country_filter not in item.get('country', '').lower():
            continue
            
        if size_filter and size_filter not in item.get('size', '').lower():
            continue
            
        year = item.get('year', '')
        if year and str(year).isdigit():
            year_num = int(year)
            if year_from and year_num < int(year_from):
                continue
            if year_to and year_num > int(year_to):
                continue
        elif (year_from or year_to):
            continue
        
        filtered_data.append(item)
    
    return filtered_data

@app.route('/get-all-json', methods=['GET'])
def get_all_json():
    """Get all JSON data - use sparingly for large datasets"""
    try:
        all_data = load_json()
        if len(all_data) > 500:
            response = jsonify(all_data)
            response.headers['X-Warning'] = 'Large dataset - consider using pagination'
            return response
        return jsonify(all_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update-json', methods=['POST'])
def update_json():
    """
    Intelligently saves updates from a filtered or paginated view on the frontend,
    preserving all items/countries that weren't visible on the screen.
    """
    try:
        incoming_data = request.get_json()
        if not isinstance(incoming_data, list):
            return jsonify({"error": "Invalid data format. Expected a list."}), 400

        full_data = load_json()

        incoming_keys = { (item.get('id'), item.get('image')) for item in incoming_data if item.get('id') }

        updated_full_data = []
        incoming_inserted = False

        for item in full_data:
            item_key = (item.get('id'), item.get('image'))
            
            if item_key in incoming_keys:
                if not incoming_inserted:
                    updated_full_data.extend(incoming_data)
                    incoming_inserted = True
                continue
            else:
                updated_full_data.append(item)

        if not incoming_inserted:
            updated_full_data.extend(incoming_data)

        save_json(updated_full_data)

        return jsonify({"message": "JSON file updated successfully! All other countries preserved."}), 200

    except Exception as e:
        print(f"Error merging sequence updates: {str(e)}")
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
            if filters.get('country') and filters['country'].lower() not in item.get('country', '').lower():
                continue
                
            if filters.get('size') and filters['size'].lower() not in item.get('size', '').lower():
                continue
                
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


@app.route('/merge-images', methods=['POST'])
def merge_images():
    """Merge two images together"""
    try:
        data = request.get_json()
        
        image1_data = data.get('image1')
        image2_data = data.get('image2')
        direction = data.get('direction', 'horizontal')
        country = data.get('country')
        
        if not all([image1_data, image2_data, country]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        if 'base64,' in image1_data:
            image1_data = image1_data.split('base64,')[1]
        if 'base64,' in image2_data:
            image2_data = image2_data.split('base64,')[1]
        
        image1 = Image.open(io.BytesIO(base64.b64decode(image1_data)))
        image2 = Image.open(io.BytesIO(base64.b64decode(image2_data)))
        
        output_format = 'PNG'
        
        has_transparency = (
            (image1.mode in ('RGBA', 'LA') or 
             (image1.mode == 'P' and 'transparency' in image1.info)) or
            (image2.mode in ('RGBA', 'LA') or 
             (image2.mode == 'P' and 'transparency' in image2.info))
        )
        
        if not has_transparency:
            try:
                if hasattr(image1, 'format') and image1.format:
                    first_format = image1.format.upper()
                    if first_format == 'JPEG':
                        output_format = 'JPEG'
            except:
                pass
        
        if direction == 'horizontal':
            max_height = max(image1.height, image2.height)
            image1 = ImageOps.contain(image1, (image1.width, max_height))
            image2 = ImageOps.contain(image2, (image2.width, max_height))
            
            new_width = image1.width + image2.width
            if has_transparency:
                merged_image = Image.new('RGBA', (new_width, max_height))
            else:
                merged_image = Image.new('RGB', (new_width, max_height))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (image1.width, 0))
        else:
            max_width = max(image1.width, image2.width)
            image1 = ImageOps.contain(image1, (max_width, image1.height))
            image2 = ImageOps.contain(image2, (max_width, image2.height))
            
            new_height = image1.height + image2.height
            if has_transparency:
                merged_image = Image.new('RGBA', (max_width, new_height))
            else:
                merged_image = Image.new('RGB', (max_width, new_height))
            merged_image.paste(image1, (0, 0))
            merged_image.paste(image2, (0, image1.height))
        
        buffer = io.BytesIO()
        
        save_kwargs = {}
        if output_format == 'JPEG':
            save_kwargs['quality'] = 95
            file_ext = 'jpg'
        else:
            file_ext = 'png'
            if has_transparency:
                merged_image = merged_image.convert('RGBA')
        
        merged_image.save(buffer, format=output_format, **save_kwargs)
        buffer.seek(0)
        
        file_uuid = str(uuid.uuid4())
        filename = f"{file_uuid}.{file_ext}"
        country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)
        
        os.makedirs(country_folder, exist_ok=True)
        
        file_path = os.path.join(country_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        invalidate_json_cache()
        
        return jsonify({
            "message": "Images merged and saved successfully",
            "filename": filename,
            "filepath": file_path,
            "format": output_format
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def invalidate_json_cache():
    """Invalidate the JSON cache"""
    global json_cache
    json_cache['data'] = None
    json_cache['timestamp'] = 0


@app.route('/get-countries', methods=['GET'])
def get_countries_list():
    """API endpoint to get countries list for dropdowns"""
    try:
        countries = load_countries()
        return jsonify(countries)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import webbrowser
    import threading
    import time
    import os
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:5000/upload-form', new=2)
        time.sleep(0.5)
        webbrowser.open('http://localhost:5000/edit_json', new=2)
    
    debug_mode = True
    if debug_mode and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        threading.Thread(target=open_browser, daemon=True).start()
        print("🌐 Browser will open automatically...")
    else:
        print("🚀 Server running at http://localhost:5000/upload-form")
    
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)