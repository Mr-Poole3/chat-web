from math import inf

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import asyncio
import httpx
import json
from fastapi.middleware.cors import CORSMiddleware
import queue
from openai import AzureOpenAI  # Add this import at the top with other imports


# 模拟不同的模型（实际应用中，你需要调用真正的模型API）
MODEL_OPTIONS = {
    "model_1": "DeepSeek-V3",  # Example model name (key) and display name
    "model_2": "DeepSeek-R1",
    "model_3": "GPT-4o-mini",
}

"""
https://ds.yovole.com/api/chat/completions

api_key: sk-833480880d9d417fbcc7ce125ca7d78b

model_name: DeepSeek-V3  DeepSeek-R1


openai azure配置
pi_key="4d6f722a1a6f47ac822c0f3c9dbcc844",
api_version="2024-08-01-preview",
azure_endpoint="https://euinstance.openai.azure.com/"

model_name: gpt-4o-mini
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API configuration
DEEPSEEK_API_URL = "https://ds.yovole.com/api/chat/completions"
DEEPSEEK_API_KEY = "sk-833480880d9d417fbcc7ce125ca7d78b"

AZURE_API_KEY = "4d6f722a1a6f47ac822c0f3c9dbcc844"
AZURE_API_VERSION = "2024-08-01-preview"
AZURE_ENDPOINT = "https://euinstance.openai.azure.com/"


class ChatRequest(BaseModel):
    model: str  # Model name
    prompt: str  # User message
    max_tokens: int = 800000  # Maximum tokens to generate
    temperature: float = 0.7  # Temperature for generation
    stream: bool = True  # Stream the response


class ModelListResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    models: List[str] = ["DeepSeek-V3", "DeepSeek-R1", "gpt-4o-mini"]


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """列出可用的模型"""
    return ModelListResponse(
        code=200,
        msg="success",
        models=["DeepSeek-V3", "DeepSeek-R1", "gpt-4o-mini"]
    )


async def fetch_deepseek_response(
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    response_queue: queue.Queue
):
    """Fetch response from DeepSeek API and put into queue"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers, timeout=None) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    print(error_detail.decode("utf-8"))
                    response_queue.put(None)  # Signal end of stream
                    return

                async for line in response.aiter_lines():
                    print(line)
                    if line.strip():
                        if line.startswith("data: "):
                            try:
                                json_str = line[6:].strip()  # Skip "data: "

                                if not json_str or json_str == "[DONE]":
                                    continue

                                if not (json_str.startswith('{') or json_str.startswith('[')):
                                    print(f"Skipping invalid JSON line: {json_str}")
                                    continue

                                data = json.loads(json_str)

                                # Extract content from the delta
                                if data["choices"] and len(data["choices"]) > 0:
                                    delta = data["choices"][0]["delta"]
                                    if "content" in delta and delta["content"]:
                                        response_queue.put(delta["content"])
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {e}")
                            except Exception as e:
                                print(f"Error parsing SSE: {e}")

                # Signal end of stream
                response_queue.put(None)
    except Exception as e:
        response_queue.put({"error": f"Error fetching DeepSeek response: {str(e)}", "status_code": 500})
        response_queue.put(None)  # Signal end of stream


async def fetch_azure_response(model: str, prompt: str, max_tokens: int, temperature: float,
                               response_queue: queue.Queue):
    """Fetch response from Azure OpenAI API using the official client"""
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT
        )

        stream_resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )

        for chunk in stream_resp:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                response_queue.put(content)

        # Signal end of stream
        response_queue.put(None)
    except Exception as e:
        response_queue.put({"error": f"Error fetching Azure response: {str(e)}", "status_code": 500})
        response_queue.put(None)  # Signal end of stream


async def stream_from_queue(response_queue: queue.Queue):
    """Stream responses from the queue"""
    while True:
        try:
            item = response_queue.get_nowait()

            if item is None:  # End of stream
                break

            if isinstance(item, dict) and "error" in item:  # Error occurred
                raise HTTPException(status_code=item.get("status_code", 500), detail=item["error"])

            # 确保返回的是字符串类型，并且格式化为SSE格式
            yield f"data: {item}\n\n"

            response_queue.task_done()
        except queue.Empty:  # Add specific exception handling for empty queue
            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error in stream_from_queue: {e}")
            break


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Chat endpoint that streams responses from the selected model API"""
    try:
        response_queue = queue.Queue()

        if request.model in ["DeepSeek-V3", "DeepSeek-R1"]:
            # Start fetching in a background task
            t_openai = asyncio.create_task(fetch_deepseek_response(
                request.model, request.prompt, request.max_tokens, request.temperature, response_queue
            ))

            return StreamingResponse(
                stream_from_queue(response_queue),
                media_type="text/event-stream"
            )
        elif request.model in ["gpt-4o-mini"]:

            # Start fetching in a background task
            t_deepseek = asyncio.create_task(fetch_azure_response(
                request.model, request.prompt, request.max_tokens, request.temperature, response_queue
            ))

            return StreamingResponse(
                stream_from_queue(response_queue),
                media_type="text/event-stream"
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {request.model}")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during chat: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def main():
    # response = await chat(ChatRequest(model="gpt-4o-mini", prompt="你好"))
    response = await chat(ChatRequest(model="DeepSeek-R1", prompt="你好"))
    s = ""
    if response and hasattr(response, "body_iterator"):
        async for data in response.body_iterator:
            s += f"{data}"
            print(s)


if __name__ == "__main__":
    # asyncio.run(main())
    import uvicorn
    uvicorn.run(
        app,
        host="localhost",
        port=8000,
        timeout_keep_alive=0,
        limit_concurrency=None,
        limit_max_requests=None
    )
