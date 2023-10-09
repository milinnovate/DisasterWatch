from flask import Flask, request, jsonify, render_template
from langchain.llms import OpenAI
from langchain.agents import load_tools, initialize_agent, Tool
from langchain.utilities import SerpAPIWrapper
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
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
        "domain": [ "ndtv.com", "bbc.in", "thehindu.com"], # not sure if this is working
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

    response_schemas = [
        ResponseSchema(name="commentary", description="news about the disaster"),
        ResponseSchema(name="date", description="date of the disaster"),
        ResponseSchema(name="source", description="source used to answer the user's question, should be a website.")
    ]
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()

    question = f"The user is interested in finding disaster commentary for the location {location}. Find the latest news about the disasters along with the date and the location of the disaster, along with the source (link) of the news"
    prompt = ChatPromptTemplate(
    messages=[
        HumanMessagePromptTemplate.from_template("Answer the user's question as best as possible.\n{format_instructions}\n{question}")  
    ],
    input_variables=["question"],
    partial_variables={"format_instructions": format_instructions}
    )

    input = prompt.format_prompt(question=question)

    # date, location, event, source

    # Generate commentary for each location one by one
    commentary = []
    dates = []
    sources = []
    for location_data in locations_data:
        location = location_data['location']
        prompt = f"The user is interested in finding disaster commentary for the location {location}. Find the latest news about the disasters along with the date and the location of the disaster, along with the source of the news"
        response = agent.run(input)
        commentary.append(response['answer'])
        dates.append(response['date'])
        sources.append(response['source'])
        

    # return location and commentary
    return jsonify({'dates': dates, 'locations': locations, 'commentary': commentary, 'sources': sources})

if __name__ == '__main__':
    app.run(debug=True, port= 3001)