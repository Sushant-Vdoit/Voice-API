from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, emit
from openai import OpenAI
from dotenv import load_dotenv
import wave
import openai
import time
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("No OpenAI key found in env")

client = openai.OpenAI(api_key=api_key)

def save_to_wav(audio_chunks, filename='output.wav'):
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)

        for chunk in audio_chunks:
            wav_file.writeframes(chunk)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tts', methods=['POST'])
def tts_post():
    # Get raw text data from the request body
    text = request.get_data(as_text=True)
    
    if not text:
        return {"error": "No text provided"}, 400

    # Split the text into sentences (e.g., split by period)
    sentences = text.split('. ')
    all_chunks = []

    # Generate audio chunks for each sentence using OpenAI API
    for sentence in sentences:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=sentence
        )
        for chunk in response.iter_bytes():
            all_chunks.append(chunk)
            time.sleep(0)  # Optional: Small delay between chunks

    # Save the combined audio chunks into a WAV file
    output_wav = 'output_post.wav'
    save_to_wav(all_chunks, filename=output_wav)

    # Return the generated WAV file as a downloadable response
    return send_file(output_wav, as_attachment=True, download_name='output.wav')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('tts')
def handle_tts(data):
    text = data.get('text', '')
    if not text:
        emit('error', {'message': 'No text provided'})
        return

    sentences = text.split('. ')
    all_chunks = []

    for sentence in sentences:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=sentence
        )
        for chunk in response.iter_bytes():
            socketio.emit('audio_chunk', chunk)
            all_chunks.append(chunk)
            time.sleep(0)

    save_to_wav(all_chunks)

if __name__ == '__main__':
    socketio.run(app, debug=True)
