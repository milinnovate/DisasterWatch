from flask import Flask, request, jsonify, render_template
from langchain.llms import OpenAI
from langchain.agents import load_tools, initialize_agent, Tool
from langchain.utilities import SerpAPIWrapper
import json
from geopy.geocoders import Nominatim
import os 
from dotenv import load_dotenv  

app = Flask(__name__)

load_dotenv()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/getdisasterDataFromIdea', methods=['POST'])
def get_disaster_data_from_idea():
    # Get the disaster idea from the request body
    data = request.get_json()
    disasterIdea = data.get('idea')

    llm = OpenAI(temperature=0.9, openai_api_key=os.environ.get('OPEN_AI_KEY'))
    params = {
        "engine": "google",
        "gl": "us",
        "hl": "en",
        "domain": [ "ndtv.com", "bbc.in"], # not sure if this is working
    }
    search = SerpAPIWrapper(params=params)
    tool = Tool(
        name="search_tool",
        description="To search for relevant information about the disaster",
        func=search.run,
    )
    agent = initialize_agent([tool], llm, agent="zero-shot-react-description", verbose=True)

    prompt = f"The user is interested in finding locations affected by disasters. Given the prompt {disasterIdea}, find the relevant affected areas of disaster (like specific landmarks, attractions, or sites) separated by commas."
    response = agent.run(prompt)

    locations = [place.strip() for place in response.split(',')]
    print(locations)

    geolocator = Nominatim(user_agent="your_app_name")
    locations_data = []
    for location in locations:
        try:
            geo_location = geolocator.geocode(location)
            locations_data.append({
                'location': location,
                'latitude': geo_location.latitude,
                'longitude': geo_location.longitude,
            })
        except Exception as e:
            app.logger.info(f" Location not found or geocoding error: {location}")
            app.logger.info(f" Error: {e}")

     # Generate commentary for each location one by one
    for location_data in locations_data:
        location = location_data['location']
        prompt = f"The user is interested in finding disaster commentary for the location {location}. Find the latest news about the disasters along with the date and the location of the disaster, along with the source (link) of the news"
        response = agent.run(prompt)
        location_data['commentary'] = response

    return jsonify(locations_data)

if __name__ == '__main__':
    app.run(debug=True, port= 3001)