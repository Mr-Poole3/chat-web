from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import asyncio
import httpx
import json
import queue
from openai import AzureOpenAI  # Add this import at the top with other imports
import os

from base import app

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

# API configuration
DEEPSEEK_API_URL = "https://ds.yovole.com/api/chat/completions"
DEEPSEEK_API_KEY = "sk-833480880d9d417fbcc7ce125ca7d78b"

AZURE_API_KEY = "4d6f722a1a6f47ac822c0f3c9dbcc844"
AZURE_API_VERSION = "2024-08-01-preview"
AZURE_ENDPOINT = "https://euinstance.openai.azure.com/"

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置静态文件服务
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")


# 添加根路由，返回index.html
@app.get("/")
async def read_root():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail=f"index.html not found at {index_path}")


# 添加/index路由，也返回index.html
@app.get("/index")
async def read_index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail=f"index.html not found at {index_path}")


# 添加/index.html路由，也返回index.html
@app.get("/index.html")
async def read_index_html():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail=f"index.html not found at {index_path}")


class ChatRequest(BaseModel):
    model: str  # Model name
    prompt: str  # User message
    max_tokens: int = 4096 # Maximum tokens to generate
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
    
    # 简化系统提示，不再要求特定的Markdown格式
    system_message = "你是一个AI助手，请根据用户的问题给出回答。"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max(max_tokens, 4096),
        "temperature": temperature,
        "stream": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers, timeout=None) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    print(f"DeepSeek API 错误: {error_detail.decode('utf-8')}")
                    response_queue.put({"error": f"DeepSeek API 错误: {error_detail.decode('utf-8')}", "status_code": response.status_code})
                    response_queue.put(None)  # Signal end of stream
                    return
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                        
                    if line.startswith("data: "):
                        try:
                            json_str = line[6:].strip()  # 去掉 "data: " 前缀
                            
                            if not json_str or json_str == "[DONE]":
                                continue
                            
                            if not (json_str.startswith('{') or json_str.startswith('[')):
                                print(f"跳过无效的JSON行: {json_str}")
                                continue
                            
                            data = json.loads(json_str)
                            
                            # 处理增量响应
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    # 直接将原始响应发送给前端，保持JSON格式
                                    # 这样前端可以自行解析内容
                                    response_queue.put(line)
                        
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}")
                        except Exception as e:
                            print(f"处理SSE时出错: {e}")
                
                # 标记流结束
                response_queue.put("data: [DONE]\n\n")
                response_queue.put(None)  # Signal end of stream
    except Exception as e:
        error_msg = f"获取DeepSeek响应时出错: {str(e)}"
        print(error_msg)
        response_queue.put({"error": error_msg, "status_code": 500})
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
        
        # 简化系统提示，不再要求特定的Markdown格式
        system_message = "你是一个AI助手，请根据用户的问题给出回答。"
        
        stream_resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max(max_tokens, 4096),
            temperature=temperature,
            stream=True
        )
        
        for chunk in stream_resp:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                # 构造与DeepSeek相同格式的响应
                response_data = {
                    "choices": [{
                        "delta": {
                            "content": content
                        }
                    }]
                }
                # 转换为SSE格式
                sse_message = f"data: {json.dumps(response_data)}\n\n"
                response_queue.put(sse_message)
        
        # 发送结束标记
        response_queue.put("data: [DONE]\n\n")
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
            
            # 直接发送item，不额外添加data:前缀（如果是DeepSeek原始响应，已经包含data:前缀）
            if isinstance(item, str) and item.startswith("data: "):
                yield item + "\n\n"
            else:
                yield f"data: {item}\n\n"
            
            response_queue.task_done()
        except queue.Empty:  # Add specific exception handling for empty queue
            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"stream_from_queue中出错: {e}")
            break


@app.post("/api/v1/tools/chat")
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
        elif request.model in ["gpt-4o-mini", "gpt-4o"]:
            
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
    asyncio.run(main())
