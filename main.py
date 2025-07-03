from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from rag_engine import process_hairgator_request

app = FastAPI()

class HairGatorInput(BaseModel):
    text: Optional[str] = None
    image_url: Optional[str] = None

@app.post("/hairgator")
async def handle_request(body: HairGatorInput):
    return process_hairgator_request(body.text, body.image_url)
