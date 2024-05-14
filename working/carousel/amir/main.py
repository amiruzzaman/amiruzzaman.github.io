import os
from flask import Flask, flash, request, redirect, render_template, url_for
from werkzeug.utils import secure_filename
import uuid
import json

#from flask import Flask, render_template, redirect, url_for, request


app=Flask(__name__, static_url_path='/static')
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

file_name = 'static/coins.json'

path = os.getcwd()
# file Upload
UPLOAD_FOLDER = os.path.join(path, 'images')

if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])




# read file
with open(file_name, 'r') as myfile:
    coins = myfile.read()

def add_to_json(cnt, img, nt):
    with open(file_name, mode='r', encoding='utf-8') as feedsjson:
        if os.stat(file_name).st_size == 0:
            feeds = []
            print('empty: ', feeds)
        else:
            feeds = json.load(feedsjson)
            print('not empty: ', feeds)
            if not feeds:
                feeds = []
                print('inside: ', feeds)
    with open(file_name, mode='w', encoding='utf-8') as feedsjson:
        entry = {'country': cnt.lower(), 'image': img, 'note':nt}
        feeds.append(entry)
        print(entry)
        json.dump(feeds, feedsjson, sort_keys=True, indent=4, separators=(',', ': '))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def edit_delete(act, val):
    print(act, val)
    #obj  = json.load(open("./images/coins.json"))
    with open(file_name, "r") as fp:
        obj = json.load(fp)
        # Iterate through the objects in the JSON and pop (remove)
        # the obj once we find it.
        for i in range(len(obj)):
            if act == 'delete':
                if obj[i]["image"] == val:
                    obj.pop(i)
                    break
            if act == 'edit':
                print('obj', obj)
        #print(obj)
    # Output the updated file with pretty JSON
    open(file_name, "w").write(
        json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
    )
    #with open('./images/coins.json', 'r') as myfile:
    #    coins1 = myfile.read()
    
    #return render_template('edit.html', title="page", jsonfile=json.dumps(obj))
        
    
@app.route('/upload')
def upload_form():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
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
            return redirect('/upload')
        else:
            flash('Allowed file types are txt, pdf, png, jpg, jpeg, gif')
            return redirect(request.url)
      
@app.route("/edit", methods =["GET", "POST"])
def edit():
    if request.method == 'GET':
        with open(file_name, 'r') as myfile:
            coins = myfile.read()
            #print(coins)
        return render_template('edit.html', title="page", jsonfile=json.dumps(coins))
        # https://stackoverflow.com/questions/67912140/how-do-i-in-flask-get-what-of-two-buttons-in-same-form-has-been-clicked-to-perfo
    if request.method == "POST":
        if request.form.get('delete') != None:
            vald = request.form.get('delete')
            print('delete: ', vald)
            edit_delete('delete', vald)
        if request.form.get('edit') is not None:
            vale = request.form.get('edit')
            print('edit: ', vale)
            print('**********')
            dd = request.form
            for d in dd:
                print(d)
            #print('all: ', request.form)
            print('**********')
            edit_delete('edit', vale)
        with open(file_name, 'r') as myfile:
            coinsed = myfile.read()
            #print(coinsed)
        return render_template('edit.html', title="page", jsonfile=json.dumps(coinsed))


@app.route('/edit_table')
def edit_table():
    return render_template('edit_table.html')


def find_update(ob):
    with open(file_name, 'r') as f:
        json_data = json.load(f)
        for entry in json_data:
            if ob['row_id'] == entry['image']:
                # update 
                #print('found', entry)
                if "image" in ob: entry["image"] = ob["image"].replace('<br>', '')
                if "note" in ob: entry["note"] = ob["note"].replace('<br>', '')
                if "country" in ob: entry["country"] = ob["country"].replace('<br>', '')
                
                
        #json_data['b'] = "9"
    
    with open(file_name, 'w') as f:
        f.write(json.dumps(json_data,sort_keys=True, indent=4, separators=(',', ': ')))

@app.route('/test', methods =["GET", "POST"])
def test():
    data = request.get_json()
    print('*************data***********')
    print(data, data['row_id'])
    print('*************data***********')
    find_update(data)
    return render_template('edit_table.html')

def find_delete(ob):
    with open(file_name, "r") as fp:
        obj = json.load(fp)
        # Iterate through the objects in the JSON and pop (remove)
        # the obj once we find it.
        try:
            for i in range(len(obj)):
                if obj[i]["image"] == ob["image"]:
                    obj.pop(i)
                    country = ob["country"]
                    img = ob["image"]
                    cp = os.path.join(UPLOAD_FOLDER, country)
                    rm_file = os.path.join(cp, img)
                    #rm_file = "images/"+country+"/"+img
                    print("file path", rm_file)
                    if os.path.isfile(rm_file):
                        os.remove(rm_file)
                        print("file path to delete", rm_file)
                    else:
                        print("file does not exist", rm_file)
                    break
            print('obj', obj)
        except:
            print("could not delete")
        
    # save updated information to a json file
    open(file_name, "w").write(
        json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
    )
    

@app.route('/testdelete', methods =["GET", "POST"])
def testdelete():
    data = request.get_json()
    print('*************data***********')
    print('testdelete', data, data['image'])
    print('*************data***********')
    find_delete(data)
    return render_template('edit_table.html')


# Route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            return redirect(url_for('upload_form'))
    return render_template('login.html', error=error)


if __name__ == "__main__":
    app.run(host = '127.0.0.1',port = 5000, debug = True)