import os
import yaml
import uuid
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from utils.claude_client import process_with_claude
import logging

# Configure logging for production
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log startup configuration
logger.info(f"Starting application with log level: {log_level}")
logger.info(f"CORS origins: {os.environ.get('ALLOWED_ORIGINS', '*')}")

app = Flask(__name__)
# Production CORS configuration
CORS(app, resources={
    r"/*": {
        "origins": os.environ.get("ALLOWED_ORIGINS", "*").split(","),
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-Secret-Code"],
        "supports_credentials": True
    }
})

# Production security settings
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    PERMANENT_SESSION_LIFETIME=7200,  # 2 hours session lifetime
    SESSION_COOKIE_SECURE=True,  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE='Lax'  # CSRF protection
)

# Load system prompt
try:
    with open('prompts/system_prompt.txt', 'r') as f:
        SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    logger.error("System prompt file not found")
    SYSTEM_PROMPT = "Please process the following and return YAML:"

def require_secret_code(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.endpoint == 'verify_auth':
            # For verification endpoint, check header
            secret_code = request.headers.get('X-Secret-Code')
        else:
            # For other endpoints, check session first, then header
            secret_code = session.get('secret_code') or request.headers.get('X-Secret-Code')
        
        expected_code = os.environ.get('APP_SECRET_CODE')
        
        if not secret_code or secret_code != expected_code:
            logger.warning("Invalid or missing secret code attempt")
            if request.is_json or request.endpoint == 'verify_auth':
                return jsonify({'error': 'Invalid or missing secret code'}), 401
            return redirect(url_for('login'))
            
        # Store valid secret code in session
        session['secret_code'] = secret_code
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/verify-auth')
@require_secret_code
def verify_auth():
    """Endpoint to verify authentication"""
    return jsonify({'status': 'authenticated', 'message': 'Secret code is valid'}), 200

@app.route('/login')
def login():
    """Login page for secret code authentication"""
    if session.get('secret_code') == os.environ.get('APP_SECRET_CODE'):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/')
@require_secret_code
def index():
    """Main page - requires authentication"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
@require_secret_code
def process():
    try:
        text_input = request.form.get('text', '')
        pdf_file = request.files.get('pdf')

        if not text_input and not pdf_file:
            return jsonify({
                'error': 'Please provide either text input or a PDF file'
            }), 400

        # Process the inputs with Claude
        result = process_with_claude(text_input, pdf_file, SYSTEM_PROMPT)

        def replace_index_with_uuid(parsed_yaml):
            for qanda in parsed_yaml:
                qanda['id'] = str(uuid.uuid4())
            return parsed_yaml

        # Validate that result is a valid YAML
        try:
            parsed_result = yaml.safe_load(result)
            if 'QandAs' in parsed_result:
                qandas = parsed_result['QandAs']
                qandas_with_uuids = replace_index_with_uuid(qandas)
                result = yaml.dump(qandas_with_uuids, sort_keys=False)
            else:
                logger.error("Missing 'QandAs' key in result")
                raise ValueError("Expected 'QandAs' key in the result")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML: {str(e)}")
            return jsonify({'error': 'Invalid YAML format'}), 400

        return jsonify({'result': result})

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # In production, we use Uvicorn to run the app
    # This is only used for development
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000, debug=False)
