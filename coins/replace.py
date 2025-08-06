import os
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure the images directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('replace.html')

@app.route('/get_folders')
def get_folders():
    try:
        folders = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                 if os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], f))]
        return jsonify({'folders': folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_images/<folder>')
def get_images(folder):
    try:
        target_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if not os.path.exists(target_folder):
            return jsonify({'error': 'Folder does not exist'}), 404
        
        images = [f for f in os.listdir(target_folder)
                 if os.path.isfile(os.path.join(target_folder, f)) and allowed_file(f)]
        
        return jsonify({
            'images': images,
            'folder': folder
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/images/<folder>/<filename>')
def serve_image(folder, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder), filename)

@app.route('/replace_image', methods=['POST'])
def replace_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        folder = request.form.get('folder')
        target_filename = request.form.get('target_filename')
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not folder or not target_filename:
            return jsonify({'error': 'Missing folder or target filename'}), 400
        
        if not allowed_file(file.filename) or not allowed_file(target_filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        target_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if not os.path.exists(target_folder):
            return jsonify({'error': 'Folder does not exist'}), 404
        
        # Save the new file with the target filename
        file.save(os.path.join(target_folder, target_filename))
        
        return jsonify({
            'message': 'Image replaced successfully',
            'filename': target_filename,
            'folder': folder
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)