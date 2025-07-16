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

#extract_email_andconsent
import re

def extract_email_and_consent(message: str):
    # Check for valid email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', message)
    email = email_match.group(0) if email_match else None

    # Check for affirmative consent
    consent_phrases = ["sí", "claro", "está bien", "acepto", "de acuerdo"]
    consent = any(phrase in message.lower() for phrase in consent_phrases)

    return email, consent

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
from typing import Optional
class MessageRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
  # Extract email and opt-in consent from user message


# Geolocate user by IP
try:
    ip = requests.get("https://api.ipify.org").text
    geo = requests.get(f"https://ipapi.co/{ip}/json/").json()
    city = geo.get("city", "Unknown")
    country = geo.get("country_name", "Unknown")
except:
    city = "Unknown"
    country = "Unknown"

  

#Create a new user if none exists/Update last_seen if the user already exists    
def upsert_user(api, base_id, user_table_name, user_id, email=None, city=None, country=None, source=None, consent=False):
    user_table = api.table(base_id, user_table_name)

    # Search for existing user by ID
    existing = user_table.first(formula=f"{{user_id}} = '{user_id}'")

    if existing:
        # Update last_seen and any new info
        update_data = {
            "last_seen": datetime.utcnow().isoformat()
        }
        if city: update_data["city"] = city
        if country: update_data["country"] = country
        if source: update_data["source"] = source
        if email and consent:  # Only store if both are valid
            update_data["email"] = email
            update_data["consent"] = "yes"

        user_table.update(existing["id"], update_data)

    else:
        # Create new user
        create_data = {
            "user_id": user_id,
            "first_seen": datetime.utcnow().isoformat(),
            "plan_type": "free",
            "city": city or "",
            "country": country or "",
            "source": source or "",
        }
        if email and consent:
            create_data["email"] = email
            create_data["consent"] = "yes"

        user_table.create(create_data)

# Default source value (for marketing or A/B tracking)
SOURCE = "SOURCE"

# Define the /chat route
@app.post("/chat")
async def chat(data: MessageRequest):
    user_message = data.message
    # Generate a unique user ID
    user_id = data.user_id or str(uuid.uuid4())
    email, consent = extract_email_and_consent(user_message)

    # Get city and country from IP
    try:
        ip = requests.get("https://api.ipify.org").text  # Gets public IP of the server
        geo = requests.get(f"https://ipapi.co/{ip}/json/".format(ip)).json()
        city = geo.get("city", "Unknown")
        country = geo.get("country_name", "Unknown")
    except:
        city = "Unknown"
        country = "Unknown"

    
    intent = detect_intent(user_message)
    #print/debug logs
    print(f"[DEBUG] Email: {email}")
    print(f"[DEBUG] Consent: {consent}")
    print(f"[DEBUG] City: {city}, Country: {country}")
    print(f"[DEBUG] User ID: {user_id}")
    
    #try block
    try: 
        chat_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
        {
        "role": "system",
        "content": (
            "Hola, soy Clara, tu asistente médica en línea. Estoy aquí para ayudarte con cualquier duda relacionada con tu salud. "
            "Después de responder a tu pregunta, a veces puedo ofrecerte consejos de salud, contenido exclusivo o promociones especiales. "
            "Si en algún momento te gustaría recibirlos, puedes dejarme tu correo electrónico. Solo lo guardaré si me das tu consentimiento claro. "
        )
        },
    
        {
        "role": "user",
        "content": user_message
        }
        ],
        temperature=0.7 
     ) 
        reply = chat_response.choices[0].message.content
    
        
        #Log to Airtable
        api = Api(os.getenv("AIRTABLE_TOKEN"))
        base_id = os.getenv("AIRTABLE_BASE_ID")
        table_name = os.getenv("AIRTABLE_TABLE_NAME")
        table = api.table(base_id, table_name)
        
         # Log or update user in "Users" table
        user_table_name = "Users"
        user_table = api.table(base_id, user_table_name)
        upsert_user(api, base_id, "Users", user_id, email=email, city=city, country=country, source="SOURCE", consent=consent)


        # Inside your /chat route, after Clara replies:
        table.create({
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent,
            "message_count": 1,
            "plan_type": "free",
            "source": "SOURCE",
            "city": city,
            "country": country,
        })
        
        return {
        "user_id": user_id,
        "response": reply
        }
    except Exception as e:
        return {"error" : str (e)}       

  
    

