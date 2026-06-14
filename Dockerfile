# Use official Python runtime as a parent image
FROM python:3.9-slim

# Install FFmpeg (required for video/audio processing)
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Railway provides
EXPOSE $PORT

# Run gunicorn to serve the Flask app
CMD gunicorn -b 0.0.0.0:${PORT:-10000} --timeout 120 app:app
