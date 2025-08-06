import os
import uuid
import json
from flask import Flask, flash, request, redirect, render_template, url_for, session
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask import jsonify

app = Flask(__name__, static_url_path='/static')
CORS(app)

# App configuration
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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

    file_ext = url.split('.')[-1]  # Extract file extension from URL
    file_uuid = str(uuid.uuid4())  # Generate a random UUID
    country_folder = os.path.join(BASE_UPLOAD_FOLDER, country)

    # Ensure the country folder exists
    os.makedirs(country_folder, exist_ok=True)

    file_path = os.path.join(country_folder, f"{file_uuid}.{file_ext}")
    with open(file_path, 'wb') as f:
        f.write(response.content)
    return file_path, f"{file_uuid}.{file_ext}"


def update_json_file(country, image, note):
    """
    Update the coins.json file with the new entry.
    """
    with open(JSON_FILE_PATH, 'r') as f:
        data = json.load(f)

    # Add the new entry
    data.append({
        "country": country,
        "image": image,
        "note": note
    })

    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)


@app.route('/upload', methods=['POST'])
def upload_file():
    country = request.form.get('country')
    note = request.form.get('note')

    # Validate the country field
    if not country:
        return jsonify({"message": "Country is required!"}), 400

    file = request.files.get('file')
    file_url = request.form.get('file-url')

    # Handle local file upload
    if file:
        try:
            file_path, file_name = save_file(file, country)
            update_json_file(country, file_name, note)  # Update the JSON file
            return jsonify({
                "message": "File uploaded successfully!",
                "country": country,
                "note": note,
                "file_path": file_path
            })
        except Exception as e:
            return jsonify({"message": "Error saving file!", "error": str(e)}), 500

    # Handle file upload via URL
    if file_url:
        try:
            file_path, file_name = download_file_from_url(file_url, country)
            update_json_file(country, file_name, note)  # Update the JSON file
            return jsonify({
                "message": "File fetched and saved successfully!",
                "country": country,
                "note": note,
                "file_path": file_path
            })
        except requests.RequestException as e:
            return jsonify({"message": "Error fetching the file from URL!", "error": str(e)}), 400

    return jsonify({"message": "No file or URL provided!"}), 400


# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_json_file():
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file) if os.stat(file_name).st_size > 0 else []

def write_json_file(data):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

def add_to_json(country, image, note):
    data = read_json_file()
    data.append({'country': country.title(), 'image': image, 'note': note})
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
                "country": updated_entry.get("country", entry["country"]).replace('<br>', '')
            })
    write_json_file(data)

def delete_entry(entry):
    data = read_json_file()
    updated_data = [item for item in data if item["image"] != entry["image"]]
    file_path = os.path.join(UPLOAD_FOLDER, entry["country"], entry["image"])
    if os.path.exists(file_path):
        os.remove(file_path)
    write_json_file(updated_data)

# Routes
# @app.route('/upload')
# @app.route("/", methods=["GET", "POST"])
# def upload():
#     if request.method == "POST":
#         country = request.form.get("country")
#         note = request.form.get("note")
#         file = request.files.get("file")

#         if file and country and note:
#             if allowed_file(file.filename):
#                 filename = secure_filename(file.filename)
#                 filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 file.save(filepath)

#                 new_entry = {
#                     "country": country,
#                     "note": note,
#                     "file_path": f"uploads/{filename}"
#                 }

#                 # Update JSON file
#                 with open(file_name, 'r+') as f:
#                     data = json.load(f)
#                     data.append(new_entry)
#                     f.seek(0)
#                     json.dump(data, f, indent=4)

#                 flash("File uploaded successfully!")
#                 return render_template(
#                     "upload.html",
#                     uploaded_file=filename,
#                     uploaded_country=country,
#                     uploaded_note=note,
#                     uploaded_path=url_for('static', filename=f'uploads/{filename}')
#                 )
#             else:
#                 flash("Invalid file type!")
#         else:
#             flash("All fields are required!")

#         return redirect(url_for("upload"))

#     return render_template("upload.html")



# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if not session.get('id'):
#         return render_template('login.html')
#     try:
#         # Your logic for handling the uploaded file
#         # For example, saving the file and extracting data from the form
#         country = request.form.get("country")
#         note = request.form.get("note")
#         file = request.files.get("file")
        
#         if not file or not allowed_file(file.filename):
#             flash('Invalid file type or no file selected')
#             return redirect(request.url)
        
#         filename = f"{uuid.uuid4().hex}{os.path.splitext(file.filename)[1]}"
#         country_path = os.path.join(UPLOAD_FOLDER, country)
#         os.makedirs(country_path, exist_ok=True)
#         file.save(os.path.join(country_path, filename))
        
#         add_to_json(country, filename, note)
#         flash('File successfully uploaded')
                  
        
#         # Simulate file saving and processing
#         file_path = f"{country}/{filename}"
        
#         # Returning a success message as JSON
#         return jsonify({
#             'message': 'File uploaded successfully!',
#             'country': country,
#             'note': note,
#             'file_path': file_path
#         })
#     except Exception as e:
#         # Handling errors by returning a JSON response with the error message
#         return jsonify({'message': f'Error: {str(e)}'}), 500
    
    
# Serve the HTML form
@app.route('/')
@app.route('/upload')
@app.route("/", methods=["GET", "POST"])
def upload_form():
    return render_template('upload.html')

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

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
