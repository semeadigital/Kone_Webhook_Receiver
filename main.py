from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import logging

# Initialize Flask app
app = Flask(__name__)

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory storage for latest webhook data
# In production, you'd use a database
latest_webhook_data = {
    'last_event': None,
    'timestamp': None,
    'event_count': 0
}

# Store history of events (last 10)
event_history = []
MAX_HISTORY = 10


@app.route('/', methods=['GET'])
def home():
    """
    Home endpoint - shows API documentation
    Returns basic info about available endpoints
    """
    return jsonify({
        'service': 'Kone Webhook Receiver',
        'status': 'running',
        'endpoints': {
            '/': 'GET - API documentation (you are here)',
            '/webhook': 'POST - Receive Kone webhooks',
            '/status': 'GET - Get latest webhook data',
            '/history': 'GET - Get recent webhook history',
            '/health': 'GET - Health check'
        },
        'description': 'This service receives webhooks from Kone API for lift status monitoring'
    }), 200


@app.route('/webhook', methods=['POST'])
def kone_webhook():
    """
    Main webhook endpoint that receives data from Kone
    This is where Kone will POST lift events
    """
    try:
        # Get JSON data from the request
        data = request.json
        
        # Get headers (useful for verification)
        headers = dict(request.headers)
        
        # Current timestamp
        timestamp = datetime.now().isoformat()
        
        # Log the incoming webhook
        logger.info("="*60)
        logger.info(f"Webhook received at: {timestamp}")
        logger.info(f"Event Type: {data.get('type', 'Unknown')}")
        logger.info(f"Equipment ID: {data.get('equipmentId', 'Unknown')}")
        logger.info("="*60)
        
        # Pretty print the full data
        logger.info("Full Payload:")
        logger.info(json.dumps(data, indent=2))
        
        # Store in memory
        latest_webhook_data['last_event'] = data
        latest_webhook_data['timestamp'] = timestamp
        latest_webhook_data['event_count'] += 1
        
        # Add to history (keep only last 10 events)
        event_history.append({
            'timestamp': timestamp,
            'data': data
        })
        if len(event_history) > MAX_HISTORY:
            event_history.pop(0)  # Remove oldest
        
        # Log to file for persistence (optional)
        # Railway has ephemeral storage, so files are lost on restart
        # But useful for debugging during active session
        try:
            with open('webhook_events.log', 'a') as f:
                f.write(json.dumps({
                    'timestamp': timestamp,
                    'data': data
                }) + '\n')
        except Exception as e:
            logger.warning(f"Could not write to log file: {e}")
        
        # IMPORTANT: Return 200 OK to acknowledge receipt
        # If you don't return 200, Kone might retry sending
        return jsonify({
            'status': 'success',
            'message': 'Webhook received and processed',
            'timestamp': timestamp
        }), 200
        
    except Exception as e:
        # Log any errors
        logger.error(f"Error processing webhook: {str(e)}")
        
        # Return error response
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/status', methods=['GET'])
def get_status():
    """
    Get the latest webhook data received
    Useful for your local ANPR system to query
    """
    if latest_webhook_data['last_event'] is None:
        return jsonify({
            'message': 'No webhooks received yet',
            'event_count': latest_webhook_data['event_count']
        }), 200
    
    return jsonify({
        'latest_event': latest_webhook_data['last_event'],
        'timestamp': latest_webhook_data['timestamp'],
        'total_events_received': latest_webhook_data['event_count']
    }), 200


@app.route('/history', methods=['GET'])
def get_history():
    """
    Get recent webhook history (last 10 events)
    """
    return jsonify({
        'total_events': len(event_history),
        'events': event_history
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    Railway and monitoring tools use this to verify service is running
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'uptime_check': 'OK'
    }), 200


# Main entry point
if __name__ == '__main__':
    # Railway provides PORT environment variable
    # Default to 5000 for local testing
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting Kone Webhook Receiver on port {port}")
    
    # host='0.0.0.0' makes it accessible from outside
    # debug=False for production (Railway sets this automatically)
    app.run(host='0.0.0.0', port=port, debug=False)
