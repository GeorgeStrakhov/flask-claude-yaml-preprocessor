import os
import yaml
import uuid
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from utils.claude_client import process_with_claude
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS - in production, update origins based on your requirements
CORS(app, resources={
    r"/*": {
        "origins": os.environ.get("ALLOWED_ORIGINS", "*"),
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-Secret-Code"]
    }
})

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
        secret_code = request.headers.get('X-Secret-Code')
        expected_code = os.environ.get('APP_SECRET_CODE')
        
        if not secret_code or secret_code != expected_code:
            logger.warning("Invalid or missing secret code attempt")
            return jsonify({'error': 'Invalid or missing secret code'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
@require_secret_code
def index():
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
    app.run(host='0.0.0.0', port=5000, debug=False)
