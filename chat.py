from typing import List
import asyncio
import queue
from fastapi.responses import StreamingResponse
from openai import AzureOpenAI
from pydantic import BaseModel, Field

from backend import AZURE_API_KEY, AZURE_API_VERSION, AZURE_ENDPOINT
from base import app


class ChatRequest(BaseModel):
    model_name: str = Field(default="gpt-4o-mini", description="model nam")  # Model name
    messages: List[dict] = Field([], description="chat history")  # User message
    max_tokens: int = 3000  # Maximum tokens to generate


class ToolsChatRequest(BaseModel):
    model: str = "gpt-4o-mini"  # Model name
    prompt: str  # User message
    max_tokens: int = 8000  # Maximum tokens to generate
    temperature: float = 0.7  # Temperature for generation
    stream: bool = True  # Stream the response
    feature: str = "chat"  # Feature type


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


async def fetch_azure_stream(prompt: str, response_queue: queue.Queue):
    """获取Azure OpenAI流式响应"""
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT
        )
        
        stream_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.7,
            stream=True
        )
        
        for chunk in stream_resp:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                response_queue.put(content)
        
        # 信号流结束
        response_queue.put(None)
    except Exception as e:
        print(f"Error fetching Azure stream: {e}")
        response_queue.put(None)


async def stream_from_queue(response_queue: queue.Queue):
    """从队列中流式传输响应"""
    while True:
        try:
            item = response_queue.get_nowait()
            
            if item is None:  # 流结束
                break
            
            # 确保返回的是字符串类型，并格式化为SSE格式
            yield f"data: {item}\n\n"
            
            response_queue.task_done()
        except queue.Empty:
            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error in stream_from_queue: {e}")
            break


@app.post("/api/v1/tools/chat")
async def tools_chat(request: ToolsChatRequest):
    """提供流式聊天响应的API端点"""
    try:
        print(f"收到聊天请求: {request}")
        # 创建响应队列
        response_queue = queue.Queue()
        
        # 启动后台任务获取流式响应
        asyncio.create_task(fetch_azure_stream(request.prompt, response_queue))
        
        # 返回流式响应
        return StreamingResponse(
            stream_from_queue(response_queue),
            media_type="text/event-stream"
        )
    except Exception as e:
        print(f"Error in tools_chat: {e}")
        return ResponseModel(code=500, msg=f"Error: {str(e)}")


if __name__ == '__main__':
    import asyncio

    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hello, how can I help you today?"},
        {"role": "user", "content": "I need help with my computer"},
    ]
    resp = asyncio.run(chat(ChatRequest(messages=history)))
    print(resp)
