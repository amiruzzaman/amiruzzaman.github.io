"""
Complete Flask Web Scraper Application
Single file containing backend and frontend code
"""

from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import base64
import re
from urllib.parse import urljoin, urlparse
import time

app = Flask(__name__)

# HTML Template with CSS and JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Page Extractor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .input-section {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        
        .url-form {
            display: flex;
            gap: 10px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .url-form input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .url-form input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .url-form button {
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
        }
        
        .url-form button:hover {
            background: #5a67d8;
            transform: translateY(-2px);
        }
        
        .url-form button:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            display: none;
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 30px;
            border-left: 4px solid #c33;
        }
        
        .error.active {
            display: block;
        }
        
        .results {
            padding: 30px;
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 30px;
        }
        
        .images-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .images-section h2 {
            margin-bottom: 20px;
            color: #333;
            font-size: 1.5em;
        }
        
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 15px;
        }
        
        .image-item {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .image-item:hover {
            transform: scale(1.05);
        }
        
        .image-item img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            display: block;
        }
        
        .image-item p {
            padding: 8px;
            font-size: 12px;
            text-align: center;
            background: white;
            margin: 0;
            color: #666;
            border-top: 1px solid #eee;
        }
        
        .info-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
        }
        
        .info-section h2 {
            margin-bottom: 20px;
            color: #333;
            font-size: 1.5em;
        }
        
        .info-content {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            min-height: 400px;
        }
        
        .info-content pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: inherit;
            line-height: 1.6;
            color: #333;
        }
        
        .fullscreen-image {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .fullscreen-image.active {
            display: flex;
        }
        
        .fullscreen-image img {
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
        }
        
        .close-button {
            position: absolute;
            top: 20px;
            right: 20px;
            color: white;
            font-size: 30px;
            cursor: pointer;
            width: 40px;
            height: 40px;
            background: rgba(0,0,0,0.5);
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .close-button:hover {
            background: rgba(0,0,0,0.8);
        }
        
        @media (max-width: 768px) {
            .results {
                grid-template-columns: 1fr;
            }
            
            .url-form {
                flex-direction: column;
            }
            
            .url-form button {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Web Page Extractor</h1>
            <p>Extract text content and images from any webpage</p>
        </div>
        
        <div class="input-section">
            <form class="url-form" id="urlForm">
                <input type="url" id="urlInput" placeholder="Enter URL to extract (e.g., https://en.numista.com/210867)" required>
                <button type="submit" id="extractBtn">Extract Content</button>
            </form>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Extracting content, please wait...</p>
        </div>
        
        <div class="error" id="error">
            <p id="errorMessage"></p>
        </div>
        
        <div class="results" id="results" style="display: none;">
            <div class="images-section">
                <h2>Images Found</h2>
                <div class="image-grid" id="imageGrid">
                    <!-- Images will be inserted here -->
                </div>
            </div>
            
            <div class="info-section">
                <h2>Extracted Information</h2>
                <div class="info-content">
                    <pre id="extractedInfo"></pre>
                </div>
            </div>
        </div>
    </div>
    
    <div class="fullscreen-image" id="fullscreenImage">
        <span class="close-button" id="closeFullscreen">&times;</span>
        <img id="fullscreenImg" src="" alt="Fullscreen view">
    </div>
    
    <script>
        document.getElementById('urlForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = document.getElementById('urlInput').value;
            const extractBtn = document.getElementById('extractBtn');
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');
            const results = document.getElementById('results');
            
            // Reset UI
            error.classList.remove('active');
            results.style.display = 'none';
            loading.classList.add('active');
            extractBtn.disabled = true;
            
            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to extract content');
                }
                
                // Display extracted information
                document.getElementById('extractedInfo').textContent = data.info;
                
                // Display images
                const imageGrid = document.getElementById('imageGrid');
                imageGrid.innerHTML = '';
                
                data.images.forEach((image, index) => {
                    const imageItem = document.createElement('div');
                    imageItem.className = 'image-item';
                    
                    const img = document.createElement('img');
                    img.src = image.data;
                    img.alt = image.alt || `Image ${index + 1}`;
                    
                    const p = document.createElement('p');
                    p.textContent = truncateText(image.alt || `Image ${index + 1}`, 30);
                    
                    imageItem.appendChild(img);
                    imageItem.appendChild(p);
                    
                    imageItem.addEventListener('click', () => {
                        showFullscreen(image.data);
                    });
                    
                    imageGrid.appendChild(imageItem);
                });
                
                results.style.display = 'grid';
                
            } catch (err) {
                document.getElementById('errorMessage').textContent = err.message;
                error.classList.add('active');
            } finally {
                loading.classList.remove('active');
                extractBtn.disabled = false;
            }
        });
        
        function truncateText(text, maxLength) {
            if (text.length <= maxLength) return text;
            return text.substr(0, maxLength) + '...';
        }
        
        function showFullscreen(src) {
            document.getElementById('fullscreenImg').src = src;
            document.getElementById('fullscreenImage').classList.add('active');
        }
        
        document.getElementById('closeFullscreen').addEventListener('click', () => {
            document.getElementById('fullscreenImage').classList.remove('active');
        });
        
        document.getElementById('fullscreenImage').addEventListener('click', (e) => {
            if (e.target === document.getElementById('fullscreenImage')) {
                document.getElementById('fullscreenImage').classList.remove('active');
            }
        });
    </script>
</body>
</html>
'''

def extract_website_content(url):
    """
    Extract text content and images from a website
    """
    try:
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text content (remove script and style elements)
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Extract images
        images = []
        for img in soup.find_all('img'):
            img_url = img.get('src')
            if img_url:
                # Make URL absolute
                img_url = urljoin(url, img_url)
                
                # Get image alt text
                alt_text = img.get('alt', '')
                
                # Try to download and encode the image
                try:
                    img_response = requests.get(img_url, headers=headers, timeout=5)
                    if img_response.status_code == 200:
                        img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                        content_type = img_response.headers.get('content-type', 'image/jpeg')
                        img_data = f"data:{content_type};base64,{img_base64}"
                        
                        images.append({
                            'url': img_url,
                            'alt': alt_text,
                            'data': img_data
                        })
                except:
                    # If image download fails, skip it
                    continue
        
        return {
            'success': True,
            'text': text[:5000] + ('...' if len(text) > 5000 else ''),  # Limit text length
            'images': images
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"Failed to fetch URL: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error processing content: {str(e)}"
        }

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Add http:// if no protocol is specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    result = extract_website_content(url)
    
    if result['success']:
        return jsonify({
            'info': result['text'],
            'images': result['images']
        })
    else:
        return jsonify({'error': result['error']}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)