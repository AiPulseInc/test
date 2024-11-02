from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Nieprawidłowy URL YouTube")

def get_available_transcript(video_id):
    """Get available transcript with priority languages"""
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    
    # Lista priorytetowych języków
    priority_languages = ['pl', 'en']
    
    # Próbuj znaleźć transkrypcję w kolejności priorytetowej
    for lang in priority_languages:
        try:
            return transcript_list.find_transcript([lang])
        except:
            continue
    
    # Jeśli nie znaleziono priorytetowych języków, spróbuj pobrać domyślną transkrypcję
    try:
        # Pobierz manualnie utworzoną transkrypcję w języku angielskim
        return transcript_list.find_manually_created_transcript(['en'])
    except:
        try:
            # Spróbuj pobrać automatycznie wygenerowaną transkrypcję w języku angielskim
            return transcript_list.find_generated_transcript(['en'])
        except:
            # Jeśli nadal nie ma, pobierz pierwszą dostępną transkrypcję
            available_transcripts = transcript_list.manual_transcripts
            if available_transcripts:
                return list(available_transcripts.values())[0]
            
            available_transcripts = transcript_list.generated_transcripts
            if available_transcripts:
                return list(available_transcripts.values())[0]
    
    raise ValueError("Nie znaleziono dostępnej transkrypcji")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL jest wymagany'}), 400
        
        video_id = extract_video_id(url)
        transcript = get_available_transcript(video_id)
        transcript_data = transcript.fetch()
        
        formatted_transcript = []
        for entry in transcript_data:
            start_time = int(entry['start'])
            minutes = start_time // 60
            seconds = start_time % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            formatted_transcript.append(f"{timestamp} {entry['text']}")
        
        return jsonify({
            'transcript': '\n'.join(formatted_transcript)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)