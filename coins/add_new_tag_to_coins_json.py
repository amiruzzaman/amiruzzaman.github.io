import json
import os
import http.server
import socketserver
import webbrowser
import threading
from urllib.parse import parse_qs, urlparse

# Configuration
PORT = 8000
JSON_FILE = './images/coins.json'

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Serve the HTML interface
            html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON Tag Editor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        #status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 4px;
            display: none;
        }
        .success {
            background-color: #dff0d8;
            color: #3c763d;
            border: 1px solid #d6e9c6;
        }
        .error {
            background-color: #f2dede;
            color: #a94442;
            border: 1px solid #ebccd1;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Add New Tag to coins.json</h1>
        <form id="tagForm">
            <div class="form-group">
                <label for="key_name">Key Name:</label>
                <input type="text" id="key_name" name="key_name" required placeholder="Enter the new key name">
            </div>
            <div class="form-group">
                <label for="default_value">Default Value:</label>
                <input type="text" id="default_value" name="default_value" required placeholder="Enter the default value">
            </div>
            <button type="submit">Add Tag</button>
        </form>
        <div id="status"></div>
    </div>

    <script>
        document.getElementById('tagForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const keyName = document.getElementById('key_name').value;
            const defaultValue = document.getElementById('default_value').value;
            const statusDiv = document.getElementById('status');
            
            // Create form data
            const formData = new URLSearchParams();
            formData.append('key_name', keyName);
            formData.append('default_value', defaultValue);
            
            // Send POST request
            fetch('/add_tag', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    statusDiv.className = 'success';
                    statusDiv.textContent = data.message;
                    statusDiv.style.display = 'block';
                    
                    // Clear form
                    document.getElementById('tagForm').reset();
                } else {
                    statusDiv.className = 'error';
                    statusDiv.textContent = 'Error: ' + data.message;
                    statusDiv.style.display = 'block';
                }
            })
            .catch(error => {
                statusDiv.className = 'error';
                statusDiv.textContent = 'Error: ' + error;
                statusDiv.style.display = 'block';
            });
        });
    </script>
</body>
</html>
"""
            self.wfile.write(html_content.encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/add_tag':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)
            
            key_name = params.get('key_name', [''])[0]
            default_value = params.get('default_value', [''])[0]
            
            # Process the JSON file
            try:
                with open(JSON_FILE, 'r') as f:
                    data = json.load(f)
                
                # Add the new tag
                if isinstance(data, list):
                    for d in data:
                        d[key_name] = default_value
                else:
                    data[key_name] = default_value
                
                # Write the updated JSON data back to the file
                with open(JSON_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'success', 'message': f'Successfully added "{key_name}" with default value "{default_value}"'}
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
        print(f"Server started at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == '__main__':
    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Open the browser
    webbrowser.open(f'http://localhost:{PORT}')
    
    # Keep the main thread alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down server...")