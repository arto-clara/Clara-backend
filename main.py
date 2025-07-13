from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load API key from .env file
load_dotenv()
client.api_key = os.getenv("OPENAI_API_KEY")


# Initialize OpenAI client
client = OpenAI()

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

    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Clara, una asistente médica que habla español y ofrece consejos de salud."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )

        return {"response": chat_response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}
    if __name__ == "__main__":
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)

