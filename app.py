import os
import subprocess
import uuid
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

# Folder to store temporary processing files
app.config['UPLOAD_FOLDER'] = 'temp_files'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

    if use_beginning or not start_time.strip():
        start_time = "00:00"

    job_id = str(uuid.uuid4())
    vid_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_in.mp4")
    aud_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_aud.m4a")
    out_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_out.mp4")

    video.save(vid_path)

    try:
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 
            'default=noprint_wrappers=1:nokey=1', vid_path
        ]
        duration = float(subprocess.check_output(duration_cmd).strip())

        yt_cmd = [
            'yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio', 
            '--outtmpl', aud_path
        ]
        
        if os.path.exists('cookies.txt'):
            yt_cmd.extend(['--cookies', 'cookies.txt'])
            
        yt_cmd.append(yt_url) 
        
        subprocess.run(yt_cmd, check=True, capture_output=True, text=True)

        merge_cmd = [
            'ffmpeg', '-y', 
            '-i', vid_path,           
            '-ss', start_time,        
            '-t', str(duration),      
            '-i', aud_path,           
            '-c:v', 'copy',           
            '-c:a', 'aac',            
            '-map', '0:v:0',          
            '-map', '1:a:0',          
            out_path
        ]
        subprocess.run(merge_cmd, check=True, capture_output=True, text=True)

        os.remove(vid_path)
        os.remove(aud_path)

        return send_file(out_path, as_attachment=True, download_name="Naya_Video.mp4")

    except subprocess.CalledProcessError as e:
        print("\n---- PROCESS ERROR ----")
        print(f"Command failed: {' '.join(e.cmd)}")
        print(f"Error output: {e.stderr}")
        print("-----------------------\n")
        
        if os.path.exists(vid_path): os.remove(vid_path)
        if os.path.exists(aud_path): os.remove(aud_path)
        
        return f"Video processing failed. Please check the logs on Railway.", 500
        
    except Exception as e:
        print(f"General Error: {e}")
        return "An unexpected error occurred.", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
