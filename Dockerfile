FROM python:3.9-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
CMD gunicorn -b 0.0.0.0:$PORT --timeout 120 app:app
