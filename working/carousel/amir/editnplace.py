from flask import Flask, render_template, request, jsonify, send_file
import os
import uuid
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'images'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_safe_country_name(country):
    """Convert country name to a safe folder name"""
    return "".join(c for c in country if c.isalnum() or c in (' ', '-', '_')).rstrip()

@app.route('/')
def index():
    return render_template('dragndrop.html')

@app.route('/edit')
def edit():
    return render_template('editnplace.html')

@app.route('/get-countries')
def get_countries():
    try:
        with open('static/countries.json', 'r') as f:
            countries = json.load(f)
        return jsonify(countries)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-images')
def get_images():
    try:
        images = []
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for file in files:
                if file.lower().endswith(tuple(app.config['ALLOWED_EXTENSIONS'])):
                    rel_path = os.path.relpath(os.path.join(root, file), app.config['UPLOAD_FOLDER'])
                    country = rel_path.split(os.sep)[0] if os.sep in rel_path else 'unknown'
                    images.append({
                        'name': file,
                        'path': rel_path.replace('\\', '/'),  # Convert Windows paths to Unix-style
                        'country': country
                    })
        return jsonify({"images": images})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-image')
def get_image():
    path = request.args.get('path')
    if not path:
        return jsonify({"error": "No path provided"}), 400
    
    safe_path = os.path.join(app.config['UPLOAD_FOLDER'], *path.split('/'))
    if not os.path.exists(safe_path):
        return jsonify({"error": "Image not found"}), 404
    
    return send_file(safe_path, mimetype='image/jpeg')

@app.route('/save-image', methods=['POST'])
def save_image():
    if 'image' not in request.files or 'path' not in request.form or 'filename' not in request.form or 'country' not in request.form:
        return jsonify({"error": "Missing required fields"}), 400
    
    file = request.files['image']
    path = request.form['path']
    filename = request.form['filename']
    country = request.form['country']
    
    if not path or not filename or not country:
        return jsonify({"error": "Invalid parameters"}), 400
    
    # Create safe paths
    safe_country = get_safe_country_name(country)
    country_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_country)
    os.makedirs(country_folder, exist_ok=True)
    
    safe_path = os.path.join(country_folder, secure_filename(filename))
    
    try:
        # Save the new image (overwrite the original)
        file.save(safe_path)
        return jsonify({
            "success": True, 
            "message": "Image saved successfully",
            "path": f"{safe_country}/{filename}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # Get form data
        country = request.form.get('country')
        currency_type = request.form.get('currency_type')
        donor_name = request.form.get('donor_name')
        note = request.form.get('note')
        
        if not all([country, currency_type, donor_name]):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Handle file upload
        if 'image' not in request.files:
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        if file and allowed_file(file.filename):
            # Generate unique filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            
            # Create country folder if it doesn't exist
            safe_country = get_safe_country_name(country)
            country_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_country)
            os.makedirs(country_folder, exist_ok=True)
            
            # Save file
            filepath = os.path.join(country_folder, filename)
            file.save(filepath)
            
            # Create new entry with relative path
            new_entry = {
                "country": country,
                "currency_type": currency_type,
                "donor_name": donor_name,
                "image": f"{safe_country}/{filename}",  # Store relative path
                "note": note
            }
            
            # Update coins.json
            coins_path = os.path.join(app.config['UPLOAD_FOLDER'], 'coins.json')
            try:
                if os.path.exists(coins_path):
                    with open(coins_path, 'r') as f:
                        coins_data = json.load(f)
                else:
                    coins_data = []
                
                coins_data.append(new_entry)
                
                with open(coins_path, 'w') as f:
                    json.dump(coins_data, f, indent=4)
                
                return jsonify({
                    "success": True, 
                    "message": "Data saved successfully",
                    "image_path": new_entry["image"]
                })
            except Exception as e:
                # Clean up the uploaded file if JSON update fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "File type not allowed"}), 400

if __name__ == '__main__':
    app.run(debug=True)