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


@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('id'):
        return render_template('login.html')
    try:
        # Your logic for handling the uploaded file
        # For example, saving the file and extracting data from the form
        country = request.form.get("country")
        note = request.form.get("note")
        file = request.files.get("file")
        
        if not file or not allowed_file(file.filename):
            flash('Invalid file type or no file selected')
            return redirect(request.url)
        
        filename = f"{uuid.uuid4().hex}{os.path.splitext(file.filename)[1]}"
        country_path = os.path.join(UPLOAD_FOLDER, country)
        os.makedirs(country_path, exist_ok=True)
        file.save(os.path.join(country_path, filename))
        
        add_to_json(country, filename, note)
        flash('File successfully uploaded')
                  
        
        # Simulate file saving and processing
        file_path = f"{country}/{filename}"
        
        # Returning a success message as JSON
        return jsonify({
            'message': 'File uploaded successfully!',
            'country': country,
            'note': note,
            'file_path': file_path
        })
    except Exception as e:
        # Handling errors by returning a JSON response with the error message
        return jsonify({'message': f'Error: {str(e)}'}), 500
    
    
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
