import json
import geocoder
import time
from kafka import KafkaProducer

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "restaurant_data"
USER_QUERY = "I need some groceries" 

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")  # Serialize messages to JSON
)

def get_current_gps_coordinates():
    """Retrieves the user's GPS coordinates based on IP."""
    g = geocoder.ip('me')
    return g.latlng if g.latlng is not None else None

def send_to_kafka(data):
    if data:
        try:
            producer.send(KAFKA_TOPIC, value=data)
            producer.flush()
            print(f"Sent to Kafka: {data}")
        except Exception as e:
            print(f"Error sending data to Kafka: {e}")

def main():
    while True:
        data = {"coordinates":get_current_gps_coordinates(), "query":USER_QUERY}
        if data:
            send_to_kafka(data)
        time.sleep(600)

if __name__ == "__main__":
    main()