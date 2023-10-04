from flask import Flask, request, jsonify, render_template
import openai
import json
from geopy.geocoders import Nominatim
import os 
from dotenv import load_dotenv  

app = Flask(__name__)

openai.api_key = os.environ.get('OPEN_AI_KEY')


load_dotenv()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/getdisasterDataFromIdea', methods=['POST'])
def get_disaster_data_from_idea():
    # Get the disaster idea from the request body
    data = request.get_json()
    disasterIdea = data.get('idea')

    prompt = f"Given the Disaster '{disasterIdea}', list relevant affected areas of disaster (like specific landmarks, attractions, or sites) separated by semicolons."
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=100,
        temperature=0.2,
    )
    generated_text = response.choices[0].text.strip()
    locations = [place.strip() for place in generated_text.split(';')]

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
            app.logger.info(f"Location not found or geocoding error: {location}")
            app.logger.info(f"Error: {e}")

    # Generate commentary for all locations
    prompt = f"You've mentioned that you're interested in '{disasterIdea}'. The relevant points of interest are {json.dumps(locations_data, default=str)}. Here is the latest news about the disasters along with the date and the location of the disaster:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1000,
        temperature=0.2,
    )
    commentary = response.choices[0].text.strip()

    return jsonify({'locations_data': locations_data, 'commentary': commentary})

if __name__ == '__main__':
    app.run(debug=True, port= 3001)