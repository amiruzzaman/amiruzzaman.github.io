import os
from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename
import uuid
import json

app=Flask(__name__)

app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

path = os.getcwd()
# file Upload
UPLOAD_FOLDER = os.path.join(path, 'images')

if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


def add_to_json(cnt, img, nt):
    with open('images/coins.json', mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
    with open('images/coins.json', mode='w', encoding='utf-8') as feedsjson:
        entry = {'country': cnt.lower(), 'image': img, 'note':nt}
        feeds.append(entry)
        json.dump(feeds, feedsjson, sort_keys=True, indent=4, separators=(',', ': '))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload_form():
    return render_template('upload.html')


@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        note = request.form.get("note")
        country = request.form.get("country")
        print(country)
        cp = os.path.join(UPLOAD_FOLDER, country)
        if not os.path.isdir(cp):
            os.mkdir(cp)
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename_, file_extension = os.path.splitext(filename)
            print(filename_, file_extension, uuid.uuid4().hex)
            #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            fn = str(uuid.uuid4().hex) + file_extension
            file.save(os.path.join(cp, fn))
            add_to_json(country, fn, note)
            flash('File successfully uploaded')
            return redirect('/')
        else:
            flash('Allowed file types are txt, pdf, png, jpg, jpeg, gif')
            return redirect(request.url)


if __name__ == "__main__":
    app.run(host = '127.0.0.1',port = 5000, debug = True)