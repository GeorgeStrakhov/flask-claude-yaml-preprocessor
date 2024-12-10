import os
from flask import Flask, render_template, request, jsonify
from utils.claude_client import process_with_claude
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load system prompt
try:
    with open('prompts/system_prompt.txt', 'r') as f:
        SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    logger.error("System prompt file not found")
    SYSTEM_PROMPT = "Please process the following and return YAML:"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        text_input = request.form.get('text', '')
        pdf_file = request.files.get('pdf')
        
        if not text_input and not pdf_file:
            return jsonify({'error': 'Please provide either text input or a PDF file'}), 400

        # Process the inputs with Claude
        result = process_with_claude(text_input, pdf_file, SYSTEM_PROMPT)
        
        return jsonify({'result': result})
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
