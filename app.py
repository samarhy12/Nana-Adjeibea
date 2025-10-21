from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
application = app

# Security: Use environment variables
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
GHANANLP_API_KEY = os.getenv('GHANANLP_API_KEY', '')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """
    Translate text using GhanaNLP API
    Supports: English <-> Twi, Ewe, Ga, Dagbani, Akuapem Twi, Fante, etc.
    """
    try:
        data = request.json
        text = data.get('text', '')
        source_lang = data.get('source', 'en')
        target_lang = data.get('target', 'tw')
        
        if not text:
            return jsonify({'error': 'Missing text'}), 400
        
        # Check if API key is configured
        if not GHANANLP_API_KEY:
            return jsonify({
                'error': 'API key not configured',
                'details': 'Please add your GhanaNLP API key to .env file. Get one at https://translation.ghananlp.org'
            }), 401
        
        # GhanaNLP language code mapping
        lang_map = {
            'en': 'en',
            'tw': 'tw',  # Asante Twi
            'twi_akuapem': 'ak',  # Akuapem Twi
            'ewe': 'ee',
            'ga': 'gaa',
            'dagbani': 'dag',
            'fante': 'fat',
            'kikuyu': 'ki'  # Added Kikuyu support
        }
        
        source = lang_map.get(source_lang, source_lang)
        target = lang_map.get(target_lang, target_lang)
        
        # Call GhanaNLP Translation API
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': GHANANLP_API_KEY
        }
        
        payload = {
            'in': text,
            'lang': f"{source}-{target}"
        }
        
        print(f"Translating: {source} -> {target}")
        
        response = requests.post(
            "https://translation-api.ghananlp.org/v1/translate",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Handle different response formats from GhanaNLP
            if isinstance(result, dict):
                translated_text = result.get('out', result.get('translation', result.get('translatedText', '')))
            elif isinstance(result, str):
                translated_text = result
            else:
                translated_text = str(result)
            
            if not translated_text:
                return jsonify({
                    'error': 'Empty translation received',
                    'details': 'The API returned an empty translation. Please try again.'
                }), 500
            
            return jsonify({
                'success': True,
                'translated_text': translated_text,
                'original_text': text,
                'source_language': source_lang,
                'target_language': target_lang,
                'provider': 'GhanaNLP'
            })
        else:
            error_msg = f"API returned status {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', error_data.get('message', error_msg))
            except:
                error_msg = response.text or error_msg
            
            return jsonify({
                'error': error_msg,
                'details': 'Please check your API key and try again.'
            }), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Translation request timed out',
            'details': 'The server took too long to respond. Please try again.'
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'details': 'Unable to connect to GhanaNLP API. Please check your internet connection.'
        }), 503
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': 'An unexpected error occurred. Please try again.'
        }), 500

@app.route('/api/languages', methods=['GET'])
def get_languages():
    """Get available language pairs"""
    languages = [
        {'code': 'en', 'name': 'English', 'flag': '🇬🇧', 'native': 'English', 'tts': True},
        {'code': 'tw', 'name': 'Twi (Asante)', 'flag': '🇬🇭', 'native': 'Twi', 'tts': True},
        {'code': 'ewe', 'name': 'Ewe', 'flag': '🇬🇭', 'native': 'Eʋegbe', 'tts': True},
        {'code': 'kikuyu', 'name': 'Kikuyu', 'flag': '🇰🇪', 'native': 'Gĩkũyũ', 'tts': True},
        {'code': 'twi_akuapem', 'name': 'Twi (Akuapem)', 'flag': '🇬🇭', 'native': 'Akuapem', 'tts': False},
        {'code': 'ga', 'name': 'Ga', 'flag': '🇬🇭', 'native': 'Gã', 'tts': False},
        {'code': 'dagbani', 'name': 'Dagbani', 'flag': '🇬🇭', 'native': 'Dagbanli', 'tts': False},
        {'code': 'fante', 'name': 'Fante', 'flag': '🇬🇭', 'native': 'Mfantse', 'tts': False}
    ]
    return jsonify({'languages': languages})

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """
    Convert text to speech using GhanaNLP TTS API
    Returns audio data as base64 for direct playback in browser
    Supported: Twi (6 speakers), Ewe (2 speakers), Kikuyu (2 speakers)
    """
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'tw')
        
        if not text:
            return jsonify({'error': 'Missing text'}), 400
        
        # Check if API key is configured
        if not GHANANLP_API_KEY:
            return jsonify({
                'error': 'API key not configured',
                'details': 'Please add your GhanaNLP API key to .env file'
            }), 401
        
        # TTS API endpoint
        TTS_API_URL = "https://translation-api.ghananlp.org/tts/v1/synthesize"
        
        # Speaker mapping based on GhanaNLP API response
        speaker_map = {
            'tw': ['twi_speaker_4', 'twi_speaker_5', 'twi_speaker_6', 'twi_speaker_7', 'twi_speaker_8', 'twi_speaker_9'],
            'ewe': ['ewe_speaker_3', 'ewe_speaker_4'],
            'kikuyu': ['kikuyu_speaker_1', 'kikuyu_speaker_5']
        }
        
        # Language codes for TTS
        tts_lang_map = {
            'tw': 'tw',
            'ewe': 'ee',
            'kikuyu': 'ki'
        }
        
        # Check if language has TTS support
        if language not in speaker_map:
            return jsonify({
                'error': 'TTS not available',
                'details': f'Text-to-speech is not available for {language}. Supported languages: Twi, Ewe, Kikuyu.',
                'use_browser_tts': language == 'en'
            }), 400
        
        lang_code = tts_lang_map.get(language, language)
        # Use the first speaker by default (best quality)
        speaker_id = speaker_map[language][0]
        
        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': GHANANLP_API_KEY
        }
        
        payload = {
            'text': text,
            'language': lang_code,
            'speaker_id': speaker_id
        }
        
        print(f"TTS Request - Language: {lang_code}, Speaker: {speaker_id}")
        
        response = requests.post(TTS_API_URL, json=payload, headers=headers, timeout=30)
        
        print(f"TTS Response status: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Check if response is audio data
            if 'audio' in content_type or 'octet-stream' in content_type or len(response.content) > 1000:
                import base64
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                
                print(f"✅ Audio data successfully encoded: {len(audio_base64)} chars")
                
                return jsonify({
                    'success': True,
                    'audio_data': audio_base64,
                    'audio_format': 'audio/wav',
                    'language': language,
                    'speaker_id': speaker_id,
                    'text': text
                })
            else:
                # Try parsing as JSON
                try:
                    result = response.json()
                    audio_data = result.get('audio', result.get('audio_content', result.get('audio_base64', '')))
                    audio_url = result.get('audio_url', result.get('url', ''))
                    
                    if audio_data:
                        return jsonify({
                            'success': True,
                            'audio_data': audio_data,
                            'audio_format': 'audio/wav',
                            'language': language,
                            'speaker_id': speaker_id,
                            'text': text
                        })
                    elif audio_url:
                        # Fetch audio from URL
                        audio_response = requests.get(audio_url, timeout=30)
                        if audio_response.status_code == 200:
                            import base64
                            audio_base64 = base64.b64encode(audio_response.content).decode('utf-8')
                            return jsonify({
                                'success': True,
                                'audio_data': audio_base64,
                                'audio_format': 'audio/wav',
                                'language': language,
                                'speaker_id': speaker_id,
                                'text': text
                            })
                except ValueError:
                    pass
                
                return jsonify({
                    'error': 'No audio data in response',
                    'details': 'The TTS API did not return audio data.'
                }), 500
        
        elif response.status_code == 401:
            return jsonify({
                'error': 'Authentication failed',
                'details': 'Your GhanaNLP API key is invalid or expired.'
            }), 401
        
        elif response.status_code == 403:
            return jsonify({
                'error': 'Access forbidden',
                'details': 'TTS access is not enabled for your API key.'
            }), 403
        
        else:
            error_msg = f"TTS API returned status {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', error_data.get('message', error_msg))
            except:
                error_msg = response.text[:200] if response.text else error_msg
            
            return jsonify({
                'error': error_msg,
                'details': f'Status code: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'TTS request timed out',
            'details': 'The speech generation took too long. Try with shorter text.'
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'details': 'Unable to connect to GhanaNLP TTS API.'
        }), 503
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'details': 'An unexpected error occurred during speech generation'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if API key is configured"""
    is_configured = bool(GHANANLP_API_KEY)
    return jsonify({
        'status': 'configured' if is_configured else 'needs_setup',
        'message': 'Ready to translate!' if is_configured else 'Please configure your GhanaNLP API key in .env file'
    })

if __name__ == '__main__':
    app.run(debug=False)