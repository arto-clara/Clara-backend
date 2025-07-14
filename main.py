from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import uuid

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

# Define the /chat route
@app.post("/chat")
async def chat(data: MessageRequest):
    user_message = data.message
    user_id = str(uuid.uuid4())

    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Clara, una asistente médica que habla español."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )
        
        from pyairtable import Api
        from datetime import datetime

        api = Api(os.getenv("AIRTABLE_TOKEN"))
        base_id = os.getenv("AIRTABLE_BASE_ID")
        table_name = os.getenv("AIRTABLE_TABLE_NAME")
        table = api.table(base_id, table_name)

        # Inside your /chat route, after Clara replies:
        table.create({
            "user_id": "user_123",
            "timestamp": datetime.utcnow().isoformat(),
            "intent": "general_info",
            "message_count": 1,
            "plan_type": "free",
            "source": "framer_homepage"
})
        return {"response": chat_response.choices[0].message.content}

    except Exception as e:
        return {"error": str(e)}
    

