import os
import subprocess
import threading
import time
import requests
import uuid
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

# Folder to store temporary processing files
app.config['UPLOAD_FOLDER'] = 'temp_files'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Keep-Alive Cron Mechanism ---
def ping_website():
    while True:
        try:
            # Railway sets RAILWAY_PUBLIC_DOMAIN, Render uses RENDER_EXTERNAL_URL
            domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RENDER_EXTERNAL_URL')
            
            if domain:
                # Ensure it has https://
                url = domain if domain.startswith('http') else f"https://{domain}"
                requests.get(f"{url}/keep-alive")
            else:
                requests.get("http://localhost:10000/keep-alive")
        except:
            pass
        # Ping every 10 minutes (600 seconds)
        time.sleep(600)

# Start the background pinging thread
threading.Thread(target=ping_website, daemon=True).start()

@app.route('/keep-alive')
def keep_alive():
    return "Still awake!", 200

# --- Core Web Application ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    if 'video' not in request.files:
        return "No video uploaded", 400
    
    video = request.files['video']
    yt_url = request.form.get('yt_url')
    start_time = request.form.get('start_time')
    use_beginning = request.form.get('use_beginning')

    # Default to 00:00 if they checked the box or left it blank
    if use_beginning or not start_time.strip():
        start_time = "00:00"

    # Generate unique IDs so multiple users don't overwrite each other's files
    job_id = str(uuid.uuid4())
    vid_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_in.mp4")
    aud_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_aud.m4a")
    out_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_out.mp4")

    # Save the user's uploaded video
    video.save(vid_path)

    try:
        # 1. Get exact duration of the uploaded video
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 
            'default=noprint_wrappers=1:nokey=1', vid_path
        ]
        duration = float(subprocess.check_output(duration_cmd).strip())

        # 2. Download only the audio from the YouTube link
        yt_cmd = [
            'yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio', 
            '--outtmpl', aud_path
        ]
        
        # If the cookies.txt file exists, use it to bypass YouTube's block!
        if os.path.exists('cookies.txt'):
            yt_cmd.extend(['--cookies', 'cookies.txt'])
            
        yt_cmd.append(yt_url) # Add the URL at the very end
        
        # Run yt-dlp and capture any errors for the Railway logs
        subprocess.run(yt_cmd, check=True, capture_output=True, text=True)

        # 3. Cut the audio and merge it with the video
        merge_cmd = [
            'ffmpeg', '-y', 
            '-i', vid_path,           # Input 1: Video
            '-ss', start_time,        # Start point for audio
            '-t', str(duration),      # Duration to cut audio
            '-i', aud_path,           # Input 2: Audio
            '-c:v', 'copy',           # Copy video without re-encoding (FAST)
            '-c:a', 'aac',            # Format audio to AAC
            '-map', '0:v:0',          # Take video from input 1
            '-map', '1:a:0',          # Take audio from input 2
            out_path
        ]
        subprocess.run(merge_cmd, check=True, capture_output=True, text=True)

        # 4. Clean up original temp files to save disk space
        os.remove(vid_path)
        os.remove(aud_path)

        # 5. Send the final video to the user
        return send_file(out_path, as_attachment=True, download_name="Naya_Video.mp4")

    except subprocess.CalledProcessError as e:
        # This will print the EXACT error from yt-dlp or ffmpeg into your Railway logs
        print("\n---- PROCESS ERROR ----")
        print(f"Command failed: {' '.join(e.cmd)}")
        print(f"Error output: {e.stderr}")
        print("-----------------------\n")
        
        # Clean up files if they exist so we don't clog up the server on a failure
        if os.path.exists(vid_path): os.remove(vid_path)
        if os.path.exists(aud_path): os.remove(aud_path)
        
        return f"Video processing failed. Please check the logs on Railway.", 500
        
    except Exception as e:
        print(f"General Error: {e}")
        return "An unexpected error occurred.", 500

if __name__ == '__main__':
    # Railway passes the port automatically via the PORT environment variable
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
