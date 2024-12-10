import os
from app import app
import uvicorn
from uvicorn.middleware.wsgi import WSGIMiddleware

# Wrap Flask app with WSGI middleware for Uvicorn compatibility
asgi_app = WSGIMiddleware(app)

if __name__ == "__main__":
    # Production settings for Replit deployment
    port = int(os.environ.get('PORT', 5000))
    
    # Configure uvicorn with settings optimized for long-running requests
    uvicorn.run(
        "main:asgi_app",  # Use the WSGI-wrapped app
        host="0.0.0.0",
        port=port,
        workers=1,  # Single worker for Replit environment
        timeout_keep_alive=120,  # Keep-alive timeout
        timeout_graceful_shutdown=300,  # Graceful shutdown timeout
        log_level="info",
        proxy_headers=True,  # Trust proxy headers for proper IP handling
        forwarded_allow_ips="*"  # Allow forwarded IPs in proxy headers
    )
