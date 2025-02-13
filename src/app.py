from flask import Flask, request, jsonify, render_template, Response
from threading import Thread
import time
import json
from producer import KafkaGPSProducer  
from main import UserQueryProcessor 
from shared_state import shared_state 

app = Flask(__name__)

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "req_data"

producer = KafkaGPSProducer(broker=KAFKA_BROKER, topic=KAFKA_TOPIC)

query_processor = UserQueryProcessor(kafka_broker=KAFKA_BROKER, kafka_topic=KAFKA_TOPIC)

# Start Kafka consumer in a separate thread
def start_consumer():
    for message in query_processor.consumer:
        query_processor.process_message(message)

consumer_thread = Thread(target=start_consumer, daemon=True)
consumer_thread.start()

# Flask Routes
@app.route('/')
def index():
    """Render the HTML page."""
    return render_template('index.html')

@app.route('/send_query', methods=['POST'])
def send_query():
    """
    Endpoint to send a user query to Kafka.
    """
    data = request.json
    query = data.get("query")

    if not query:
        return jsonify({"error": "The 'query' field is required"}), 400

    producer.start(query)

    return jsonify({"status": "Query sent to Kafka", "query": query}), 200

@app.route('/stream')
def stream():
    """
    SSE endpoint to stream real-time updates to the client.
    """
    def event_stream():
        while True:
            latest_results = shared_state.get_latest_results()  
            if latest_results:
                yield f"data: {json.dumps({'latest_results': latest_results})}\n\n"
            time.sleep(1)  

    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(debug=True)