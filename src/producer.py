import json
import geocoder
import time
from kafka import KafkaProducer

TOPIC = "req_data"
HOST = "localhost:9092"

class KafkaGPSProducer:
    def __init__(self, broker=HOST, topic=TOPIC):
        self.broker = broker
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=self.broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    
    def get_current_gps_coordinates(self):
        """Retrieves the user's GPS coordinates based on IP."""
        g = geocoder.ip('me')
        return g.latlng if g.latlng is not None else None
    
    def send_to_kafka(self, data):
        if data:
            try:
                self.producer.send(self.topic, value=data)
                self.producer.flush()
                print(f"Sent to Kafka: {data}")
            except Exception as e:
                print(f"Error sending data to Kafka: {e}")
    
    def start(self, user_query):
        """Sends data to Kafka when called."""
        data = {"coordinates": self.get_current_gps_coordinates(), "query": user_query}
        if data:
            self.send_to_kafka(data)

if __name__ == "__main__":
    producer = KafkaGPSProducer()
    producer.start("I want almonds")
