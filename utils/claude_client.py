import anthropic
import base64
import logging
from werkzeug.utils import secure_filename
import os

logger = logging.getLogger(__name__)

def process_with_claude(text_input, pdf_file, system_prompt):
    try:
        client = anthropic.Anthropic()
        
        # Prepare the content list for the API request
        content = []
        
        # Add PDF if provided
        if pdf_file:
            pdf_data = base64.b64encode(pdf_file.read()).decode('utf-8')
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                }
            })
        
        # Add text input and system prompt
        prompt_text = system_prompt
        if text_input:
            prompt_text += f"\n\nText Input:\n{text_input}"
            
        content.append({
            "type": "text",
            "text": prompt_text
        })
        
        # Make API request
        message = client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": content
            }],
            betas=["pdfs-2024-09-25"]
        )
        
        return message.content[0].text
        
    except Exception as e:
        logger.error(f"Error processing with Claude: {str(e)}")
        raise Exception(f"Failed to process with Claude: {str(e)}")
