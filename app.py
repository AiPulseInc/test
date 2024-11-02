from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re
import logging
import sys

# Konfiguracja logowania
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            logger.info(f"Extracted video ID: {match.group(1)}")
            return match.group(1)
    
    logger.error(f"Could not extract video ID from URL: {url}")
    raise ValueError("Nieprawidłowy URL YouTube")

def get_available_transcript(video_id):
    """Get available transcript with priority languages"""
    try:
        logger.info(f"Attempting to get transcript list for video ID: {video_id}")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        logger.info("Successfully retrieved transcript list")
        
        # Lista priorytetowych języków
        priority_languages = ['pl', 'en']
        
        # Próbuj znaleźć transkrypcję w kolejności priorytetowej
        for lang in priority_languages:
            try:
                logger.info(f"Attempting to find transcript in {lang}")
                transcript = transcript_list.find_transcript([lang])
                logger.info(f"Found transcript in {lang}")
                return transcript
            except Exception as e:
                logger.warning(f"Could not find transcript in {lang}: {str(e)}")
                continue
        
        # Jeśli nie znaleziono priorytetowych języków, spróbuj pobrać domyślną transkrypcję
        try:
            logger.info("Attempting to find manually created English transcript")
            return transcript_list.find_manually_created_transcript(['en'])
        except Exception as e:
            logger.warning(f"Could not find manually created English transcript: {str(e)}")
            try:
                logger.info("Attempting to find generated English transcript")
                return transcript_list.find_generated_transcript(['en'])
            except Exception as e:
                logger.warning(f"Could not find generated English transcript: {str(e)}")
                
                # Sprawdź dostępne transkrypcje
                available_transcripts = transcript_list.manual_transcripts
                if available_transcripts:
                    logger.info("Found manual transcripts")
                    return list(available_transcripts.values())[0]
                
                available_transcripts = transcript_list.generated_transcripts
                if available_transcripts:
                    logger.info("Found generated transcripts")
                    return list(available_transcripts.values())[0]
        
        logger.error("No available transcripts found")
        raise ValueError("Nie znaleziono dostępnej transkrypcji")
        
    except Exception as e:
        logger.error(f"Error in get_available_transcript: {str(e)}")
        raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            logger.error("No URL provided")
            return jsonify({'error': 'URL jest wymagany'}), 400
        
        logger.info(f"Processing URL: {url}")
        video_id = extract_video_id(url)
        transcript = get_available_transcript(video_id)
        
        logger.info("Fetching transcript data")
        transcript_data = transcript.fetch()
        
        formatted_transcript = []
        for entry in transcript_data:
            start_time = int(entry['start'])
            minutes = start_time // 60
            seconds = start_time % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            formatted_transcript.append(f"{timestamp} {entry['text']}")
        
        logger.info("Successfully processed transcript")
        return jsonify({
            'transcript': '\n'.join(formatted_transcript)
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({'error': f"Error: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True)
