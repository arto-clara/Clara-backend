from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import uuid
from pyairtable import Api
from datetime import datetime
from pyairtable import Api
from datetime import datetime

def detect_intent(message: str) -> str:
    try:
        intent_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an intent tagging engine. "
                        "Analyze the user's message and generate a concise intent tag (in lowercase, no spaces, use underscores). "
                        "Examples: greeting, symptom_check, prescription_refill, lab_results, mental_health, unknown. "
                        "Only return the tag."
                    ),
                },
                {"role": "user", "content": message},
            ],
            temperature=0.2
        )
        return intent_response.choices[0].message.content.strip().lower()
    except Exception as e:
        return "unknown"

import requests


# Load API key from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for all origins (for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define expected request body format
class MessageRequest(BaseModel):
    message: str
#Create a new user if none exists/Update last_seen if the user already exists    
def upsert_user(api, base_id, user_table_name, user_id):
    user_table = api.table(base_id, user_table_name)

    # Search for existing user by ID
    existing = user_table.first(formula=f"{{user_id}} = '{user_id}'")

    if existing:
        # Update last_seen timestamp
        user_table.update(existing["id"], {
            "last_seen": datetime.utcnow().isoformat()
        })
    else:
        # Create new user
        user_table.create({
            "user_id": user_id,
            "first_seen": datetime.utcnow().isoformat(),
            "plan_type": "free"
        })

# Define the /chat route
@app.post("/chat")
async def chat(data: MessageRequest):
    user_message = data.message
    # Get city and country from IP
    try:
        ip = requests.get("https://api.ipify.org").text  # Gets public IP of the server
        geo = requests.get(f"https://ipapi.co/{ip}/json/").json()
        city = geo.get("city", "Unknown")
        country = geo.get("country_name", "Unknown")
    except:
        city = "Unknown"
        country = "Unknown"

    user_id = str(uuid.uuid4())
    intent = detect_intent(user_message)

    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Clara, una asistente médica que habla español."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )
        
        
        #Log to Airtable
        api = Api(os.getenv("AIRTABLE_TOKEN"))
        base_id = os.getenv("AIRTABLE_BASE_ID")
        table_name = os.getenv("AIRTABLE_TABLE_NAME")
        table = api.table(base_id, table_name)
        
         # Log or update user in "Users" table
        user_table_name = "Users"
        user_table = api.table(base_id, user_table_name)
        upsert_user(api, base_id, user_table_name, user_id)
        

        # Inside your /chat route, after Clara replies:
        table.create({
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent,
            "message_count": 1,
            "plan_type": "free",
            "source": "framer_homepage",
            "city": city,
            "country": country,

})
        return {"response": chat_response.choices[0].message.content}

    except Exception as e:
        return {"error": str(e)}
    

