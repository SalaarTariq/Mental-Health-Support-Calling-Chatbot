#uv add fastapi unicorn pydantic requests

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn 

app = FastAPI()



class Query(BaseModel):
    message: str



@app.post("/ask")
async def ask(query: Query):
    #AI Agent

    return "This is the Response"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



