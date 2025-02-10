from kafka import KafkaConsumer
import geocoder
import requests
import json
import pandas as pd
from llama_cpp import Llama
from functools import lru_cache
import uuid
import os
from dotenv import load_dotenv

load_dotenv("keys.env")

api_key = os.getenv("API_KEY")

# Mapbox API Key (Replace with your own key)
MAPBOX_ACCESS_TOKEN = api_key
SESSION_TOKEN = str(uuid.uuid4())

@lru_cache(maxsize=1)
def load_llm_model():
    """Loads the LLM model once and caches it for faster inference."""

    return Llama(model_path="/mnt/c/Users/raymo/Documents/Coding-Programs/KafkaProject/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf", 
                 n_gpu_layers=-1, n_ctx=2048)

def get_search_suggestions(query, proximity=None):
    url = "https://api.mapbox.com/search/searchbox/v1/suggest"
    params = {
        "q": query,
        "access_token": MAPBOX_ACCESS_TOKEN,
        "session_token": SESSION_TOKEN,
        "limit": 5, 
        "types": "poi",
        "language": "en"
    }
    if proximity:
        params["proximity"] = proximity  # Bias results to a location

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()["suggestions"]
    else:
        print("Error fetching suggestions:", response.status_code, response.text)
        return None

def process_result_data(results):
    """Extracts relevant restaurant information into a DataFrame."""
    processed_data = []
    for result in results:
        processed_data.append({
            "name": result.get("name", "Unknown"),
            "category": result.get("poi_category", "Unknown"),
            "distance": result.get("distance", "Unknown"),
            "address": result.get("full_address", "Unknown")
        })
    return pd.DataFrame(processed_data)

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "restaurant_data"

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='latest',
    group_id='restaurant-group'
)

for message in consumer:
    print(f"Received: {message.value.decode('utf-8')}")
    data = json.loads(message.value)
    coordinates = data.get("coordinates")
    query = data.get("query")
    llm = load_llm_model()  

    if coordinates:
        latitude, longitude = coordinates
        print(f"Your current GPS coordinates:\nLatitude: {latitude}\nLongitude: {longitude}\n")

        user_reqs = f"Here's the user's query: {query}, think of a single phrase or word to feed an API to find places nearby related to the query. Your response must limited to exactly one phrase or word and nothing else."
        messages = [
            {"role": "system", "content": "You are a concise and helpful AI assistant."},
            {"role": "user", "content": f"{user_reqs}"}
        ]

        response = llm.create_chat_completion(messages=messages, max_tokens=2048, temperature=0.3, stop=[])
        print(response['choices'][0]['message']['content'])
        text = response['choices'][0]['message']['content']

        start_index = text.find("</think>")

        # Extract everything after </think>
        if start_index != -1:
            result = text[start_index + len("</think>"):].strip()
        else:
            result = "No </think> tag found."

        results = get_search_suggestions(result, proximity=f"{longitude},{latitude}")
        if results:
            print(results)
            df = process_result_data(results)
            print(df.head())

            user_reqs = f"Based on this data, list the best options based on the user's request: {query}."
            messages = [
                {"role": "system", "content": "You are a concise and helpful AI assistant."},
                {"role": "user", "content": f"{user_reqs} \n {df.to_dict()}"}
            ]

            response = llm.create_chat_completion(messages=messages, max_tokens=2048, stop=[])
            print(response['choices'][0]['message']['content'])
        else:
            print("No Results found.")
    else:
        print("Unable to retrieve GPS coordinates.")
