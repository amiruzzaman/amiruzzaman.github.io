import os
import sys
import json
import shutil
import cv2
import uuid
import time
import threading
from flask import Flask, request, jsonify, render_template_string, send_from_directory, Response
from moviepy import VideoFileClip, concatenate_videoclips

app = Flask(__name__)

# Configure storage directories
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'video_editor_data')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global variable to track compilation progress (0 to 100)
progress_percentage = 0
progress_lock = threading.Lock()

# HTML, CSS, and JS combined into a single template string
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Multi-Slider Video Editor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #1a1a1a;
            color: #ffffff;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            max-width: 900px;
            width: 100%;
            background: #2d2d2d;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        h1 { margin-top: 0; color: #4af; text-align: center; }
        .upload-section {
            border: 2px dashed #4af;
            padding: 20px;
            text-align: center;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        video {
            width: 100%;
            max-height: 380px;
            background: #000;
            border-radius: 4px;
        }
        
        .timeline-overview {
            width: 100%;
            height: 15px;
            background: #444;
            margin-top: 20px;
            border-radius: 4px;
            position: relative;
            overflow: hidden;
        }
        .overview-cut-chunk {
            position: absolute;
            height: 100%;
            background: rgba(235, 85, 85, 0.6);
        }

        .slider-card {
            background: #222;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            border-left: 4px solid #e55;
        }
        .slider-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .slider-track-container {
            position: relative;
            width: 100%;
            height: 30px;
            background: #333;
            border-radius: 4px;
        }
        .slider-inputs {
            position: relative;
            width: 100%;
            height: 30px;
        }
        .slider-inputs input[type="range"] {
            position: absolute;
            width: 100%;
            height: 30px;
            top: 0;
            left: 0;
            background: transparent;
            -webkit-appearance: none;
            appearance: none;
            margin: 0;
            pointer-events: none;
        }
        
        .slider-inputs input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 30px;
            border-radius: 3px;
            background: #e55;
            cursor: pointer;
            pointer-events: auto;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
        }
        
        .slider-inputs input[type="range"]::-moz-range-thumb {
            width: 20px;
            height: 30px;
            border: none;
            border-radius: 3px;
            background: #e55;
            cursor: pointer;
            pointer-events: auto;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
        }
        
        .highlight-bar {
            position: absolute;
            height: 100%;
            background: rgba(230, 85, 85, 0.3);
            border-left: 2px solid #e55;
            border-right: 2px solid #e55;
            pointer-events: none;
            top: 0;
        }

        .controls {
            margin-top: 25px;
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        button {
            background: #4af;
            color: #fff;
            border: none;
            padding: 10px 18px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #39d; }
        button.danger { background: #e55; }
        button:disabled { background: #555; cursor: not-allowed; }
        
        .progress-container {
            margin-top: 25px;
            background: #222;
            padding: 15px;
            border-radius: 6px;
            display: none;
        }
        progress {
            width: 100%;
            height: 20px;
            accent-color: #2e7;
        }
        .progress-text {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Concurrent Multi-Slider Video Editor</h1>
    
    <div class="upload-section" onclick="document.getElementById('fileInput').click()">
        <p id="uploadText">Click to browse and upload a video file</p>
        <input type="file" id="fileInput" accept="video/*" style="display:none" onchange="uploadVideo(this)">
    </div>

    <div id="editorWorkspace" style="display:none;">
        <video id="videoPlayer" controls></video>
        
        <h3>Global Visual Timeline Map</h3>
        <div class="timeline-overview" id="timelineOverview"></div>

        <div id="slidersList">
            </div>

        <div class="controls">
            <button onclick="createNewSliderCard()">➕ Add Another Cut Slider</button>
            <button style="background:#2e7" id="saveBtn" onclick="processVideo()">Render & Compile Master Video</button>
        </div>

        <div class="progress-container" id="progressWrapper">
            <div class="progress-text">
                <span id="progressStatus">Initializing pipeline...</span>
                <span id="progressPercent">0%</span>
            </div>
            <progress id="compileProgressBar" value="0" max="100"></progress>
        </div>
    </div>
</div>

<script>
    let currentFilename = "";
    let videoDuration = 0;
    let sliderCounter = 0;
    const player = document.getElementById('videoPlayer');

    function uploadVideo(input) {
        if (!input.files.length) return;
        
        const file = input.files[0];
        const formData = new FormData();
        formData.append('video', file);
        
        document.getElementById('uploadText').innerText = "Uploading track data...";
        
        fetch('/upload', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                alert(data.error);
                return;
            }
            currentFilename = data.filename;
            videoDuration = data.duration;
            
            player.src = `/videos/${currentFilename}`;
            document.getElementById('editorWorkspace').style.display = 'block';
            document.getElementById('uploadText').innerText = `Active File: ${file.name}`;
            
            document.getElementById('slidersList').innerHTML = "";
            sliderCounter = 0;
            createNewSliderCard();
        })
        .catch(err => alert("Error transferring data."));
    }

    function createNewSliderCard() {
        sliderCounter++;
        const id = sliderCounter;
        
        const defaultStart = 0;
        const defaultEnd = (videoDuration * 0.20).toFixed(2);

        const cardHtml = `
            <div class="slider-card" id="card_${id}" data-slider-id="${id}">
                <div class="slider-header">
                    <strong>🚫 Cut Zone Configuration #${id}</strong>
                    <button class="danger" style="padding:4px 8px; font-size:0.85em;" onclick="removeSliderCard(${id})">Remove This Slider</button>
                </div>
                <div class="slider-track-container">
                    <div class="highlight-bar" id="highlight_${id}"></div>
                    <div class="slider-inputs">
                        <input type="range" id="start_${id}" min="0" max="${videoDuration}" value="${defaultStart}" step="0.01" oninput="syncSliders(${id}, 'start')" onmousedown="bringToFront(this)" ontouchstart="bringToFront(this)">
                        <input type="range" id="end_${id}" min="0" max="${videoDuration}" value="${defaultEnd}" step="0.01" oninput="syncSliders(${id}, 'end')" onmousedown="bringToFront(this)" ontouchstart="bringToFront(this)">
                    </div>
                </div>
                <div style="margin-top:8px; font-size:0.9em; color:#aaa; text-align:center">
                    Time block: <span id="lbl_start_${id}">0.00</span>s to <span id="lbl_end_${id}">${defaultEnd}</span>s
                </div>
            </div>
        `;
        
        document.getElementById('slidersList').insertAdjacentHTML('beforeend', cardHtml);
        syncSliders(id, 'start');
    }

    function bringToFront(element) {
        const inputs = element.parentElement.querySelectorAll('input');
        inputs.forEach(input => input.style.zIndex = "10");
        element.style.zIndex = "20";
    }

    function removeSliderCard(id) {
        const card = document.getElementById(`card_${id}`);
        if(card) card.remove();
        refreshGlobalTimelineMap();
    }

    function syncSliders(id, origin) {
        const rStart = document.getElementById(`start_${id}`);
        const rEnd = document.getElementById(`end_${id}`);
        const hl = document.getElementById(`highlight_${id}`);
        
        if(!rStart || !rEnd) return;
        
        let valStart = parseFloat(rStart.value);
        let valEnd = parseFloat(rEnd.value);
        
        if (origin === 'start' && valStart >= valEnd) {
            rEnd.value = valStart;
            valEnd = valStart;
        } else if (origin === 'end' && valEnd <= valStart) {
            rStart.value = valEnd;
            valStart = valEnd;
        }
        
        document.getElementById(`lbl_start_${id}`).innerText = valStart.toFixed(2);
        document.getElementById(`lbl_end_${id}`).innerText = valEnd.toFixed(2);
        
        const pctStart = (valStart / videoDuration) * 100;
        const pctEnd = (valEnd / videoDuration) * 100;
        
        if(hl) {
            hl.style.left = pctStart + "%";
            hl.style.width = (pctEnd - pctStart) + "%";
        }
        
        player.currentTime = (origin === 'start') ? valStart : valEnd;
        refreshGlobalTimelineMap();
    }

    function refreshGlobalTimelineMap() {
        const overview = document.getElementById('timelineOverview');
        overview.innerHTML = "";
        
        const cards = document.querySelectorAll('.slider-card');
        cards.forEach(card => {
            const id = card.getAttribute('data-slider-id');
            const startInput = document.getElementById(`start_${id}`);
            const endInput = document.getElementById(`end_${id}`);
            
            if(startInput && endInput) {
                const start = parseFloat(startInput.value);
                const end = parseFloat(endInput.value);
                
                const pctStart = (start / videoDuration) * 100;
                const pctEnd = (end / videoDuration) * 100;
                
                const block = document.createElement('div');
                block.className = "overview-cut-chunk";
                block.style.left = pctStart + "%";
                block.style.width = (pctEnd - pctStart) + "%";
                overview.appendChild(block);
            }
        });
    }

    function processVideo() {
        const cards = document.querySelectorAll('.slider-card');
        let cuts = [];
        
        cards.forEach(card => {
            const id = card.getAttribute('data-slider-id');
            const startInput = document.getElementById(`start_${id}`);
            const endInput = document.getElementById(`end_${id}`);
            if(startInput && endInput) {
                cuts.push({
                    start: parseFloat(startInput.value),
                    end: parseFloat(endInput.value)
                });
            }
        });
        
        cuts.sort((a, b) => a.start - b.start);

        document.getElementById('progressWrapper').style.display = "block";
        document.getElementById('saveBtn').disabled = true;
        
        // Poll for progress
        const progressInterval = setInterval(() => {
            fetch('/progress')
                .then(res => res.json())
                .then(data => {
                    const pct = data.progress;
                    document.getElementById('compileProgressBar').value = pct;
                    document.getElementById('progressPercent').innerText = pct + "%";
                    if (pct < 100) {
                        document.getElementById('progressStatus').innerText = "Rendering video...";
                    } else {
                        document.getElementById('progressStatus').innerText = "Complete!";
                    }
                    if (pct >= 100) {
                        clearInterval(progressInterval);
                    }
                })
                .catch(err => console.error('Progress fetch error:', err));
        }, 500);

        fetch('/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: currentFilename, cuts: cuts })
        })
        .then(res => res.json())
        .then(data => {
            clearInterval(progressInterval);
            document.getElementById('saveBtn').disabled = false;
            
            if (data.error) {
                alert("Processing Error: " + data.error);
                document.getElementById('progressStatus').innerText = "Process aborted.";
                document.getElementById('progressWrapper').style.display = "none";
            } else {
                document.getElementById('compileProgressBar').value = 100;
                document.getElementById('progressPercent').innerText = "100%";
                document.getElementById('progressStatus').innerText = "Done! Download started.";
                setTimeout(() => {
                    window.location.href = `/download/${data.output_file}`;
                }, 1000);
            }
        })
        .catch(err => {
            clearInterval(progressInterval);
            document.getElementById('saveBtn').disabled = false;
            alert("Error processing video: " + err);
            document.getElementById('progressWrapper').style.display = "none";
        });
    }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return jsonify({'error': 'No file element present'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = "input_" + file.filename.replace(" ", "_")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    cap = cv2.VideoCapture(filepath)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()

    return jsonify({'filename': filename, 'duration': duration})

@app.route('/progress')
def get_progress():
    global progress_percentage
    with progress_lock:
        return jsonify({'progress': progress_percentage})

@app.route('/edit', methods=['POST'])
def edit_video():
    global progress_percentage
    with progress_lock:
        progress_percentage = 0
    
    data = request.json or {}
    filename = data.get('filename')
    raw_cuts = data.get('cuts', [])

    if not isinstance(raw_cuts, list):
        raw_cuts = []

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename if filename else "")
    
    unique_id = str(uuid.uuid4())[:8]
    output_filename = f"edited_{unique_id}_{filename}" if filename else f"edited_{unique_id}.mp4"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

    if not filename or not os.path.exists(input_path):
        return jsonify({'error': 'Source video file path reference not found'}), 404

    try:
        print(f"Starting video processing for {input_path}")
        
        # Load video
        video = VideoFileClip(input_path)
        
        if video is None:
            return jsonify({'error': 'Failed to load video file'}), 500
            
        total_duration = video.duration
        print(f"Video loaded. Duration: {total_duration} seconds")
        
        if total_duration is None or total_duration <= 0:
            video.close()
            return jsonify({'error': 'Invalid video duration'}), 500

        # Validate cuts
        valid_cuts = []
        for c in raw_cuts:
            if isinstance(c, dict) and 'start' in c and 'end' in c:
                try:
                    start = max(0, min(float(c['start']), total_duration))
                    end = max(0, min(float(c['end']), total_duration))
                    if start < end and (end - start) > 0.01:
                        valid_cuts.append({'start': start, 'end': end})
                except (ValueError, TypeError):
                    continue

        print(f"Valid cuts: {valid_cuts}")

        # If no cuts, copy the file
        if not valid_cuts:
            with progress_lock:
                progress_percentage = 100
            shutil.copy2(input_path, output_path)
            video.close()
            print("No cuts, copied original file")
            return jsonify({'output_file': output_filename})

        # Merge overlapping cuts
        merged_cuts = []
        for current in sorted(valid_cuts, key=lambda x: x['start']):
            if not merged_cuts:
                merged_cuts.append(current.copy())
            else:
                last = merged_cuts[-1]
                if current['start'] <= last['end'] + 0.01:
                    last['end'] = max(last['end'], current['end'])
                else:
                    merged_cuts.append(current.copy())

        print(f"Merged cuts: {merged_cuts}")

        # Calculate segments to keep
        keep_segments = []
        last_end = 0.0
        
        for cut in merged_cuts:
            if cut['start'] > last_end + 0.01:
                keep_segments.append((last_end, cut['start']))
            last_end = max(last_end, cut['end'])
        
        if last_end < total_duration - 0.01:
            keep_segments.append((last_end, total_duration))

        print(f"Keep segments: {keep_segments}")

        if not keep_segments:
            video.close()
            return jsonify({'error': 'All video content would be removed by the cuts'}), 400

        # Extract and collect clips
        clips_to_stitch = []
        total_segments = len(keep_segments)
        
        for idx, (start, end) in enumerate(keep_segments):
            if end - start > 0.05:
                try:
                    print(f"Extracting segment {idx+1}/{total_segments}: {start} to {end}")
                    subclip = video.subclipped(start, end)
                    if subclip and subclip.duration and subclip.duration > 0:
                        clips_to_stitch.append(subclip)
                        print(f"  Segment duration: {subclip.duration}")
                    else:
                        if subclip:
                            subclip.close()
                except Exception as e:
                    print(f"Error creating subclip {idx}: {e}")
                    continue
            
            # Update progress based on segment extraction
            with progress_lock:
                progress_percentage = int((idx + 1) / total_segments * 30)  # First 30% for extraction

        if not clips_to_stitch:
            video.close()
            return jsonify({'error': 'Failed to create any valid video segments'}), 400

        print(f"Created {len(clips_to_stitch)} clips to stitch")

        # Concatenate clips
        with progress_lock:
            progress_percentage = 40
        
        try:
            # Try different concatenation methods
            final_clip = None
            print("Concatenating clips...")
            try:
                final_clip = concatenate_videoclips(clips_to_stitch, method="compose")
                print("Using compose method")
            except Exception as e:
                print(f"Compose method failed: {e}")
                try:
                    final_clip = concatenate_videoclips(clips_to_stitch, method="chain")
                    print("Using chain method")
                except Exception as e2:
                    raise Exception(f"Failed to concatenate clips: {str(e2)}")
            
            if final_clip is None:
                raise Exception("Failed to create final clip")
            
            print(f"Final clip duration: {final_clip.duration}")
            
            # Write the final video
            with progress_lock:
                progress_percentage = 50
            
            print("Starting video encoding...")
            print(f"Output path: {output_path}")
            print("This may take a while depending on video size...")
            
            # Create a progress update thread
            import threading
            import time
            
            stop_progress = threading.Event()
            
            def update_progress():
                global progress_percentage
                while not stop_progress.is_set():
                    time.sleep(2)
                    # Just keep showing encoding progress
                    with progress_lock:
                        current_progress = progress_percentage
                        if current_progress < 95:
                            progress_percentage = min(progress_percentage + 2, 95)
            
            progress_thread = threading.Thread(target=update_progress)
            progress_thread.daemon = True
            progress_thread.start()
            
            try:
                # Write the video file
                final_clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    logger=None,
                    preset='medium',  # Balance between speed and quality
                    bitrate='5000k'   # Reasonable bitrate
                )
                print("Video encoding completed successfully!")
            except Exception as e:
                print(f"Error during write_videofile: {e}")
                raise
            finally:
                stop_progress.set()
                progress_thread.join(timeout=5)
            
            with progress_lock:
                progress_percentage = 100
            
                
        except Exception as e:
            print(f"Error in video processing: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error writing video: {str(e)}")
        finally:
            # Clean up
            if final_clip:
                final_clip.close()
                print("Closed final clip")
            for c in clips_to_stitch:
                try:
                    c.close()
                except:
                    pass
            video.close()
            print("Closed video")

        # Verify output file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"Output file created: {output_path} ({file_size:.2f} MB)")
        else:
            print(f"ERROR: Output file not created at {output_path}")
            return jsonify({'error': 'Output file was not created'}), 500

        return jsonify({'output_file': output_filename})

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR DETAILS:\n{error_details}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)