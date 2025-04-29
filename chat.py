from typing import List

from openai import AzureOpenAI
from pydantic import BaseModel, Field

from backend import AZURE_API_KEY, AZURE_API_VERSION, AZURE_ENDPOINT
from base import app


class ChatRequest(BaseModel):
    model_name: str = Field(default="gpt-4o-mini", description="model nam")  # Model name
    messages: List[dict] = Field([], description="chat history")  # User message
    max_tokens: int = 3000  # Maximum tokens to generate


class ResponseModel(BaseModel):
    code: int = 200
    msg: str = "success"
    data: str = Field("", description="response data")


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT
        )
        if not request.messages or not "role" in request.messages[0] or not "content" in request.messages[0]:
            return ResponseModel(data="", code=400, msg="Invalid request")

        history = "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in request.messages])
        p_sys = f"You are a helpful assistant, you need to response to the user based on the chat history {history}"

        resp = client.chat.completions.create(
            model=request.model_name,
            messages=[{"role": "assistant", "content": p_sys}],
            max_tokens=max(request.max_tokens, 4096)
        )
        return ResponseModel(data=resp.choices[0].message.content, code=200, msg="success") # type: ignore
    except Exception as e:
        print(f"Error during chat: {e}")
        return ResponseModel(data="", code=500, msg="llm generated failed")


if __name__ == '__main__':
    import asyncio

    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hello, how can I help you today?"},
        {"role": "user", "content": "I need help with my computer"},
    ]
    resp = asyncio.run(chat(ChatRequest(messages=history)))
    print(resp)
