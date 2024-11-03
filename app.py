import logging
import re
import requests
from flask import Flask, request, jsonify, render_template
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# Konfiguracja loggera
logging.basicConfig(
    level=logging.DEBUG,  # Ustawienie poziomu logowania na DEBUG, aby uzyskać jak najwięcej informacji
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format logów z timestampem, nazwą loggera, poziomem logowania i wiadomością
    handlers=[
        logging.StreamHandler()  # Logowanie do konsoli (logi będą widoczne w Render, jak i lokalnie)
    ]
)
logger = logging.getLogger(__name__)  # Utworzenie instancji loggera

# Tworzenie aplikacji Flask
app = Flask(__name__)

# Endpoint do wyświetlenia strony głównej
@app.route('/')
def home():
    logger.info("Rendering the index.html page")
    return render_template('index.html')

# Endpoint do pobierania transkrypcji
@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    data = request.get_json()  # Odczytanie danych z żądania POST
    url = data.get('url')  # Pobranie URL wideo z danych
    logger.info("Received request for URL: %s", url)

    # Wydobycie ID wideo z URL
    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Invalid YouTube URL provided: %s", url)
        return jsonify({"error": "Invalid YouTube URL"}), 400

    logger.info("Extracted video ID: %s", video_id)

    # Próba uzyskania dostępu do strony wideo za pomocą User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    try:
        logger.info("Attempting to check video access for video ID: %s", video_id)
        response = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers)
        if response.status_code == 200:
            logger.info("Successfully accessed video page for video ID: %s", video_id)
        else:
            logger.error("Failed to access video page for video ID %s. Status code: %s", video_id, response.status_code)
            return jsonify({"error": f"Failed to access video page. Status code: {response.status_code}"}), 500
    except Exception as e:
        logger.error("Error accessing video page for video ID %s: %s", video_id, str(e))
        return jsonify({"error": "Could not access video page. Reason: " + str(e)}), 500

    # Próba listowania dostępnych transkrypcji
    try:
        logger.info("Listing available transcripts for video ID: %s", video_id)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_transcripts = []
        for transcript in transcript_list:
            available_transcripts.append({
                'language': transcript.language,
                'is_generated': transcript.is_generated,
                'is_translatable': transcript.is_translatable,
                'translation_languages': transcript.translation_languages
            })
        logger.info("Available transcripts: %s", available_transcripts)
    except Exception as e:
        logger.error("Error listing transcripts for video ID %s: %s", video_id, str(e))
        return jsonify({"error": "Could not list transcripts for the video. Reason: " + str(e)}), 500

    # Próba pobrania transkrypcji
    try:
        logger.info("Attempting to fetch transcript for video ID: %s", video_id)
        # Próba pobrania transkrypcji za pomocą youtube_transcript_api
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        logger.info("Successfully fetched transcript for video ID: %s", video_id)

        transcript_text = ""
        for entry in transcript:
            timestamp = f"[{entry['start']:.2f}]"
            text = entry['text']
            transcript_text += f"{timestamp} {text}\n"

        logger.debug("Generated transcript (first 100 chars): %s", transcript_text[:100])  # Log tylko pierwszych 100 znaków
        return jsonify({"transcript": transcript_text}), 200

    except TranscriptsDisabled:
        logger.error("Subtitles are disabled for video ID %s", video_id)
        return jsonify({"error": "Subtitles are disabled for this video."}), 500
    except NoTranscriptFound:
        logger.error("No transcript found for video ID %s", video_id)
        return jsonify({"error": "No transcript found for this video."}), 500
    except Exception as e:
        logger.error("Error fetching transcript for video ID %s: %s", video_id, str(e))
        return jsonify({"error": "Could not retrieve a transcript for the video. Reason: " + str(e)}), 500

# Funkcja do wydobywania ID wideo z URL
def extract_video_id(url):
    logger.info("Extracting video ID from URL: %s", url)
    reg_exp = r'^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*'
    match = re.match(reg_exp, url)
    if match and len(match.groups()) >= 7:
        video_id = match[7]
        logger.info("Video ID extracted: %s", video_id)
        return video_id
    logger.warning("Failed to extract video ID from URL: %s", url)
    return None

# Dodatkowa funkcja do sprawdzenia żądania za pomocą User-Agent
@app.route('/check_video_access', methods=['POST'])
def check_video_access():
    data = request.get_json()
    url = data.get('url')
    logger.info("Received request to check access for URL: %s", url)
    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Invalid YouTube URL provided: %s", url)
        return jsonify({"error": "Invalid YouTube URL"}), 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    try:
        logger.info("Attempting to check video access for video ID: %s", video_id)
        response = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers)
        if response.status_code == 200:
            logger.info("Successfully accessed video page for video ID: %s", video_id)
            return jsonify({"message": "Video page accessible."}), 200
        else:
            logger.error("Failed to access video page for video ID %s. Status code: %s", video_id, response.status_code)
            return jsonify({"error": f"Failed to access video page. Status code: {response.status_code}"}), 500
    except Exception as e:
        logger.error("Error accessing video page for video ID %s: %s", video_id, str(e))
        return jsonify({"error": "Could not access video page. Reason: " + str(e)}), 500

# Uruchomienie serwera lokalnie
if __name__ == '__main__':
    app.run(debug=True)
