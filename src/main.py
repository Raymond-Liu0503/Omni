from kafka import KafkaConsumer
import geocoder
import requests
import json
import pandas as pd
import uuid
import os
from dotenv import load_dotenv
from threading import Thread
from shared_state import shared_state

# Constants
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "req_data"

class UserQueryProcessor:
    def __init__(self, kafka_broker=KAFKA_BROKER, kafka_topic=KAFKA_TOPIC, api_key_env="keys.env"):
        load_dotenv(api_key_env)
        self.api_key = os.getenv("API_KEY")
        self.or_key = os.getenv("OR_KEY")  # OpenRouter API key
        self.MAPBOX_ACCESS_TOKEN = self.api_key
        self.SESSION_TOKEN = str(uuid.uuid4())
        self.KAFKA_BROKER = kafka_broker
        self.KAFKA_TOPIC = kafka_topic
        self.consumer = KafkaConsumer(
            self.KAFKA_TOPIC,
            bootstrap_servers=self.KAFKA_BROKER,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            group_id='req-group'
        )
        self.latest_results = None 

    def query_openrouter(self, prompt, model="deepseek/deepseek-r1:free", temperature=0.3, max_tokens=1024):
        """
        Query the OpenRouter API for a response.
        """
        headers = {
            "Authorization": f"Bearer {self.or_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,  
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,  
            "max_tokens": max_tokens,  
        }
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()  
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API error: {e}")
            return {"error": str(e)}

    def get_search_suggestions(self, query, proximity=None):
        """
        Fetch search suggestions from Mapbox API.
        """
        url = "https://api.mapbox.com/search/searchbox/v1/suggest"
        params = {
            "q": query,
            "access_token": self.MAPBOX_ACCESS_TOKEN,
            "session_token": self.SESSION_TOKEN,
            "limit": 5,
            "types": "poi",
            "language": "en"
        }
        if proximity:
            params["proximity"] = proximity 

        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()["suggestions"]
        else:
            print("Error fetching suggestions:", response.status_code, response.text)
            return None

    def process_result_data(self, results):
        """
        Extract relevant restaurant information into a DataFrame.
        """
        processed_data = []
        for result in results:
            processed_data.append({
                "name": result.get("name", "Unknown"),
                "category": result.get("poi_category", "Unknown"),
                "distance": result.get("distance", "Unknown"),
                "address": result.get("full_address", "Unknown")
            })
        return pd.DataFrame(processed_data)
    
    def extract_last_line(self, text):
        """
        Extract the last line from a multi-line string (LLM API's usually return thinking process).
        """
        lines = text.strip().split('\n')  
        return lines[-1] if lines else ""  

    def process_message(self, message):
        """
        Process a Kafka message using OpenRouter API.
        """
        print(f"Received: {message.value.decode('utf-8')}")
        shared_state.update_latest_results("Processing user query...")
        data = json.loads(message.value)
        coordinates = data.get("coordinates")
        query = data.get("query")

        if coordinates:
            latitude, longitude = coordinates
            print(f"Your current GPS coordinates:\nLatitude: {latitude}\nLongitude: {longitude}\n")

            # Generate a search phrase using OpenRouter
            user_reqs = f"Here's the user's query: {query}, think of a single phrase or word to feed an API to find places nearby related to the query. Your response must be limited to exactly one phrase or word and nothing else."
            response = self.query_openrouter(user_reqs, model="deepseek/deepseek-r1-distill-llama-70b:free", temperature=0.3, max_tokens=1024)
            
            if "choices" in response:
                search_phrase = response["choices"][0]["message"]["content"]
                print(f"Generated search phrase: {search_phrase}")

                # Extract the last line from the response
                search_phrase = self.extract_last_line(search_phrase)
                print(f"Extracted search phrase: {search_phrase}")
            else:
                print("Error generating search phrase.")
                shared_state.update_latest_results("Error generating search phrase.")
                return

            # Fetch search suggestions using Mapbox API
            results = self.get_search_suggestions(search_phrase, proximity=f"{longitude},{latitude}")
            if results:
                print(results)
                df = self.process_result_data(results)
                print(df.head())

                # Generate a summary of the results using OpenRouter
                user_reqs = f"Based on this data, list the best options based on the user's request: {query}. Don't include your thinking process, just your final answer."
                response = self.query_openrouter(
                    prompt=user_reqs + "\n" + json.dumps(df.to_dict()),
                    # model="deepseek/deepseek-r1:free",
                    # temperature=0.7,
                    model="mistralai/mistral-small-24b-instruct-2501:free",
                    max_tokens=2048
                )

                print(response)
                
                if "choices" in response:
                    result_summary = response["choices"][0]["message"]["content"]
                    print(f"Generated summary: {result_summary}")
                    shared_state.update_latest_results(result_summary)
                else:
                    print("Error generating summary.")
                    shared_state.update_latest_results("Error generating summary.")
                    shared_state.clear_cache()
            else:
                print("No Results found.")
                shared_state.update_latest_results("No Results found.")
                shared_state.clear_cache()
        else:
            print("Unable to retrieve GPS coordinates.")
            shared_state.update_latest_results("Unable to retrieve GPS coordinates.")
            shared_state.clear_cache()

    def start_consuming(self):
        """
        Start consuming messages from Kafka in a separate thread.
        """
        for message in self.consumer:
            self.process_message(message)