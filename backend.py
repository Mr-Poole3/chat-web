from fastapi import FastAPI, HTTPException, Request, Depends, Body, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import httpx
import json
import queue
from openai import AzureOpenAI
import os
import pymysql
from pymysql.cursors import DictCursor
import datetime
import uuid
from dotenv import load_dotenv
import jwt
from auth import JWT_SECRET_KEY, JWT_ALGORITHM
from knowledge_base.core.manager import GraphManager
from knowledge_base.core.build_graph import insert_data_2_graph
from pathlib import Path
from knowledge_base.core.grag import query_async
import numpy as np
import time
import re
import base64
import sys

from base import app
from lib.redis_kv import RedisKVStore

# 加载环境变量
load_dotenv()

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

# 获取当前环境
ENV = os.getenv("ENV", "development")

# 根据环境配置数据库连接参数
if ENV == "development":
    DB_HOST = os.getenv("DEV_DB_HOST", "localhost")
    DB_USER = os.getenv("DEV_DB_USER", "root")
    DB_PASSWORD = os.getenv("DEV_DB_PASSWORD", "")
    DB_NAME = os.getenv("DEV_DB_NAME", "ai")
    DB_PORT = int(os.getenv("DEV_DB_PORT", "3306"))
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "ai")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))

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

# 数据库连接函数
def get_db_connection():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=True
        )
        return connection
    except Exception as e:
        print(f"数据库连接错误: {e}")
        raise HTTPException(status_code=500, detail=f"数据库连接错误: {str(e)}")

# 测试数据库连接
@app.get("/api/v1/test-db")
async def test_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
        conn.close()
        return {"status": "success", "result": result, "environment": ENV}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
    feature: Optional[str] = "chat"  # 功能标识
    session_id: Optional[str] = None  # 会话ID
    is_terminated: Optional[bool] = False  # 是否被终止


class ModelListResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    models: List[str] = ["DeepSeek-V3", "DeepSeek-R1", "gpt-4o-mini"]


class ChatSession(BaseModel):
    id: str
    title: str
    model: str
    messages: List[Dict[str, Any]] = []
    createdAt: str
    updatedAt: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: List[ChatSession] = []


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """列出可用的模型"""
    return ModelListResponse(
        code=200,
        msg="success",
        models=["DeepSeek-V3", "DeepSeek-R1", "gpt-4o-mini"]
    )


# 获取用户的聊天历史
@app.get("/api/v1/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(request: Request, user_id: Optional[int] = None):
    try:
        if not user_id:
            # 尝试从请求头获取用户ID
            user_id = request.headers.get("X-User-ID")
            
        # 如果仍然没有找到用户ID，尝试从Authorization头部提取
        if not user_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                try:
                    # 解析JWT令牌获取用户信息
                    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                    username = payload.get("sub")
                    
                    if username:
                        # 从数据库获取用户ID
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                            user_data = cursor.fetchone()
                            if user_data:
                                user_id = user_data['id']
                                print(f"从JWT令牌获取的用户ID: {user_id}")
                        conn.close()
                except Exception as e:
                    print(f"解析JWT令牌出错: {e}")
            
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空，请确保已登录")
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 查询用户的所有聊天会话
            sql = """
            SELECT id, user_id, title, model, created_at, updated_at 
            FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY updated_at DESC
            LIMIT 15
            """
            cursor.execute(sql, (user_id,))
            sessions = cursor.fetchall()
            
            # 转换日期格式并准备结果
            result = []
            for session in sessions:
                # 查询每个会话的消息
                sql_messages = """
                SELECT role, content, timestamp
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY sequence ASC
                """
                cursor.execute(sql_messages, (session['id'],))
                messages = cursor.fetchall()
                
                # 转换消息格式
                formatted_messages = []
                for msg in messages:
                    formatted_messages.append({
                        "role": msg['role'],
                        "content": msg['content'],
                        "timestamp": msg['timestamp'].isoformat()
                    })
                
                result.append({
                    "id": session['id'],
                    "title": session['title'],
                    "model": session['model'],
                    "messages": formatted_messages,
                    "createdAt": session['created_at'].isoformat(),
                    "updatedAt": session['updated_at'].isoformat() if session['updated_at'] else None
                })
        
        conn.close()
        return ChatHistoryResponse(code=200, msg="success", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"获取聊天历史记录错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天历史记录错误: {str(e)}")


# 创建新的聊天会话
@app.post("/api/v1/chat/sessions")
async def create_chat_session(
    request: Request,
    data: dict = Body(...),
):
    try:
        print(f"收到请求数据: {data}")
        user_id = data.get("user_id")
        title = data.get("title", "新对话")
        model = data.get("model", "DeepSeek-R1")
        
        # 打印调试信息
        print(f"从请求体中获取的用户ID: {user_id}")
        
        if not user_id:
            # 尝试从请求头获取用户ID
            user_id = request.headers.get("X-User-ID")
            print(f"从请求头获取的用户ID: {user_id}")
            
        # 如果仍然没有找到用户ID，尝试从Authorization头部提取
        if not user_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                try:
                    # 解析JWT令牌获取用户信息
                    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                    username = payload.get("sub")
                    
                    if username:
                        # 从数据库获取用户ID
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                            user_data = cursor.fetchone()
                            if user_data:
                                user_id = user_data['id']
                                print(f"从JWT令牌获取的用户ID: {user_id}")
                        conn.close()
                except Exception as e:
                    print(f"解析JWT令牌出错: {e}")
            
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空，请确保已登录")
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            session_id = str(uuid.uuid4())
            now = datetime.datetime.now()
            
            sql = """
            INSERT INTO chat_sessions (id, user_id, title, model, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (session_id, user_id, title, model, now, now))
        
        conn.close()
        return {"code": 200, "msg": "success", "data": {"id": session_id}}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"创建聊天会话错误: {e}")
        raise HTTPException(status_code=500, detail=f"创建聊天会话错误: {str(e)}")


# 更新聊天会话标题
@app.put("/api/v1/chat/sessions/{session_id}/title")
async def update_chat_title(session_id: str, title: str = Body(..., embed=True)):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            now = datetime.datetime.now()
            
            sql = """
            UPDATE chat_sessions 
            SET title = %s, updated_at = %s
            WHERE id = %s
            """
            cursor.execute(sql, (title, now, session_id))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="会话不存在")
        
        conn.close()
        return {"code": 200, "msg": "success"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"更新聊天标题错误: {e}")
        raise HTTPException(status_code=500, detail=f"更新聊天标题错误: {str(e)}")


# 删除聊天会话
@app.delete("/api/v1/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 先删除会话的所有消息
            sql_delete_messages = """
            DELETE FROM chat_messages
            WHERE session_id = %s
            """
            cursor.execute(sql_delete_messages, (session_id,))
            
            # 再删除会话本身
            sql_delete_session = """
            DELETE FROM chat_sessions
            WHERE id = %s
            """
            cursor.execute(sql_delete_session, (session_id,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="会话不存在")
        
        conn.close()
        return {"code": 200, "msg": "success"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"删除聊天会话错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除聊天会话错误: {str(e)}")


# 保存聊天消息
@app.post("/api/v1/chat/messages")
async def save_chat_message(
    request: Request,
    data: dict = Body(...)
):
    try:
        session_id = data.get("session_id")
        role = data.get("role")
        content = data.get("content")
        sequence = data.get("sequence")
        is_terminated = data.get("is_terminated", False)
        
        if not all([session_id, role, content, sequence is not None]):
            raise HTTPException(status_code=400, detail="缺少必要参数")
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            now = datetime.datetime.now()
            
            # 检查会话是否存在
            check_sql = "SELECT id FROM chat_sessions WHERE id = %s"
            cursor.execute(check_sql, (session_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="会话不存在")
            
            try:
                # 保存消息
                sql = """
                INSERT INTO chat_messages (session_id, role, content, timestamp, sequence, is_terminated)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (session_id, role, content, now, sequence, is_terminated))
                
                # 更新会话的更新时间
                update_sql = """
                UPDATE chat_sessions
                SET updated_at = %s
                WHERE id = %s
                """
                cursor.execute(update_sql, (now, session_id))
            except Exception as e:
                print(f"SQL执行错误: {str(e)}")
                # 如果是字段不存在的错误，尝试不包含is_terminated字段的插入
                if "Unknown column 'is_terminated'" in str(e):
                    sql = """
                    INSERT INTO chat_messages (session_id, role, content, timestamp, sequence)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (session_id, role, content, now, sequence))
                    
                    # 更新会话的更新时间
                    update_sql = """
                    UPDATE chat_sessions
                    SET updated_at = %s
                    WHERE id = %s
                    """
                    cursor.execute(update_sql, (now, session_id))
                else:
                    raise e
        
        conn.close()
        return {"code": 200, "msg": "success"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"保存聊天消息错误: {e}")
        raise HTTPException(status_code=500, detail=f"保存聊天消息错误: {str(e)}")


async def fetch_deepseek_response(
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    response_queue: queue.Queue,
    request: Request
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
                    # 检查客户端是否已断开连接
                    if await request.is_disconnected():
                        print("客户端已断开连接")
                        break
                        
                    if not line.strip():
                        continue
                        
                    if line.startswith("data: "):
                        try:
                            json_str = line[6:].strip()
                            
                            if not json_str or json_str == "[DONE]":
                                continue
                            
                            if not (json_str.startswith('{') or json_str.startswith('[')):
                                print(f"跳过无效的JSON行: {json_str}")
                                continue
                            
                            data = json.loads(json_str)
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    response_queue.put(line)
                        
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}")
                        except Exception as e:
                            print(f"处理SSE时出错: {e}")
                
                # 标记流结束
                response_queue.put("data: [DONE]\n\n")
                response_queue.put(None)  # Signal end of stream
    except httpx.RequestError as e:
        if str(e).startswith("Client disconnect"):
            print("客户端主动断开连接")
            return
        error_msg = f"获取DeepSeek响应时出错: {str(e)}"
        print(error_msg)
        response_queue.put({"error": error_msg, "status_code": 500})
        response_queue.put(None)
    except Exception as e:
        error_msg = f"获取DeepSeek响应时出错: {str(e)}"
        print(error_msg)
        response_queue.put({"error": error_msg, "status_code": 500})
        response_queue.put(None)


async def fetch_azure_response(
    model: str, 
    prompt: str, 
    max_tokens: int, 
    temperature: float,
    response_queue: queue.Queue,
    request: Request
):
    """Fetch response from Azure OpenAI API using the official client"""
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT
        )
        
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
            # 检查客户端是否已断开连接
            if await request.is_disconnected():
                print("客户端已断开连接")
                break
                
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                response_data = {
                    "choices": [{
                        "delta": {
                            "content": content
                        }
                    }]
                }
                sse_message = f"data: {json.dumps(response_data)}\n\n"
                response_queue.put(sse_message)
                
        # 发送结束标记
        response_queue.put("data: [DONE]\n\n")
        response_queue.put(None)
    except Exception as e:
        if str(e).startswith("Client disconnect"):
            print("客户端主动断开连接")
            return
        response_queue.put({"error": f"Error fetching Azure response: {str(e)}", "status_code": 500})
        response_queue.put(None)


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
async def chat(request: Request, chat_request: ChatRequest):
    """Chat endpoint that streams responses from the selected model API"""
    try:
        response_queue = queue.Queue()
        user_id = request.headers.get("X-User-ID")  # 假设前端会传递用户ID
        
        # 如果提供了会话ID，检查会话是否存在
        if chat_request.session_id:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM chat_sessions WHERE id = %s", (chat_request.session_id,))
                session = cursor.fetchone()
                if not session:
                    # 如果会话不存在，创建一个新会话
                    session_id = str(uuid.uuid4())
                    now = datetime.datetime.now()
                    cursor.execute(
                        "INSERT INTO chat_sessions (id, user_id, title, model, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                        (session_id, user_id, chat_request.prompt[:30] + "...", chat_request.model, now, now)
                    )
                else:
                    session_id = session['id']
            conn.close()
        else:
            # 如果没有提供会话ID，不创建会话，仅返回响应
            session_id = None
            
        if chat_request.model in ["DeepSeek-V3", "DeepSeek-R1"]:
            t_openai = asyncio.create_task(fetch_deepseek_response(
                chat_request.model, 
                chat_request.prompt, 
                chat_request.max_tokens, 
                chat_request.temperature, 
                response_queue,
                request
            ))
            
            return StreamingResponse(
                stream_from_queue(response_queue),
                media_type="text/event-stream"
            )
        elif chat_request.model in ["gpt-4o-mini", "gpt-4o"]:
            t_deepseek = asyncio.create_task(fetch_azure_response(
                chat_request.model, 
                chat_request.prompt, 
                chat_request.max_tokens, 
                chat_request.temperature, 
                response_queue,
                request
            ))
            
            return StreamingResponse(
                stream_from_queue(response_queue),
                media_type="text/event-stream"
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {chat_request.model}")
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


def convert_numpy_types(obj):
    """将numpy类型转换为Python原生类型"""
    if obj is None:
        return None
    # 处理numpy的数值类型
    if isinstance(obj, (np.integer, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.complex64, np.complex128)):
        return complex(obj)
    # 处理集合类型
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    # 处理有转换方法的对象
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    if hasattr(obj, 'item'):
        return obj.item()
    # 尝试直接将对象转为JSON可序列化的格式
    try:
        import json
        json.dumps(obj)
        return obj  # 如果可以序列化，则直接返回
    except (TypeError, OverflowError):
        # 如果对象无法JSON序列化，转为字符串
        return str(obj)


@app.post("/api/v1/knowledge/process")
async def process_document(file: UploadFile = File(...)):
    """处理上传的文档并提取知识"""
    temp_dir = None
    try:
        # 生成唯一的知识库ID
        kb_id = str(uuid.uuid4())
        
        # 创建临时文件保存上传的文档
        temp_dir = Path(os.path.abspath("temp_kb_files")) / kb_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 记录文件名，用于后续保存元数据
        original_filename = file.filename
        
        # 初始化知识库管理器
        log_id = str(uuid.uuid4())
        manager = GraphManager(kb_id=kb_id, log_id=log_id)
        
        # 加载知识图谱
        graph = manager.load_graph()
        
        # 处理文档并插入到图谱中
        rag, token_count = await insert_data_2_graph(
            graph=graph,
            file_path=str(file_path),
            log_id=log_id
        )
        
        if not rag:
            return {"results": [{"type": "处理结果", "confidence": 60, "text": "文档处理失败，请检查文档格式是否支持。"}], "kb_id": kb_id}
        
        # 保存元数据
        try:
            # 确保知识库目录存在
            kb_path = Path(os.path.abspath("cache_graph")) / kb_id
            if os.path.exists(kb_path):
                # 创建元数据文件
                metadata = {
                    "file_name": original_filename,
                    "upload_time": time.time(),
                    "token_count": token_count
                }
                meta_file = kb_path / "metadata.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                print(f"保存知识库元数据成功: {kb_id}")
            else:
                print(f"知识库目录不存在，无法保存元数据: {kb_id}")
        except Exception as e:
            print(f"保存元数据时出错: {str(e)}")
        
        # 提取关键信息
        results = []
        
        try:
            # 提取实体
            entities = await query_async(
                graph=graph,
                q="提取文档中的主要实体和概念",
                with_references=True,
                log_id=log_id
            )
            
            if entities:
                try:
                    results.append({
                        "type": "实体",
                        "confidence": 85,
                        "text": convert_numpy_types(entities)
                    })
                except Exception as e:
                    print(f"转换实体数据时出错: {str(e)}")
                
            # 提取关系
            relationships = await query_async(
                graph=graph,
                q="提取文档中的主要关系和连接",
                with_references=True,
                log_id=log_id
            )
            
            if relationships:
                try:
                    results.append({
                        "type": "关系",
                        "confidence": 80,
                        "text": convert_numpy_types(relationships)
                    })
                except Exception as e:
                    print(f"转换关系数据时出错: {str(e)}")
            
            # 提取关键内容
            key_points = await query_async(
                graph=graph,
                q="提取文档的关键内容和要点",
                with_references=True,
                log_id=log_id
            )
            
            if key_points:
                try:
                    results.append({
                        "type": "要点",
                        "confidence": 90,
                        "text": convert_numpy_types(key_points)
                    })
                except Exception as e:
                    print(f"转换要点数据时出错: {str(e)}")
                
        except Exception as e:
            print(f"查询图谱时出错: {str(e)}")
            # 如果查询失败，至少返回一个基本结果
            results.append({
                "type": "处理结果",
                "confidence": 70,
                "text": f"文档已成功处理，共{token_count}个token，但无法提取详细信息。错误信息：{str(e)}"
            })
        
        # 如果没有提取到任何结果，返回一个基本消息
        if not results:
            results.append({
                "type": "处理结果",
                "confidence": 65,
                "text": f"文档已处理，但未能提取出有效信息。共{token_count}个token。"
            })
            
        # 确保整个结果数组都被转换
        try:
            converted_results = convert_numpy_types(results)
        except Exception as e:
            print(f"转换最终结果时出错: {str(e)}")
            # 如果转换失败，返回一个简单的文本结果
            return {"results": [{"type": "处理结果", "confidence": 60, "text": f"文档已处理，但在转换结果时出错。错误信息：{str(e)}"}], "kb_id": kb_id}
            
        # 返回结果中添加知识库ID
        return {"results": converted_results, "kb_id": kb_id}
        
    except Exception as e:
        print(f"处理文档时出错: {str(e)}")
        return {"results": [{"type": "错误", "confidence": 0, "text": f"处理文档时出错: {str(e)}"}], "kb_id": None}
    finally:
        # 确保临时文件夹被清理
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时文件时出错: {str(e)}")


class KnowledgeQueryRequest(BaseModel):
    """知识库查询请求"""
    query: str
    kb_id: Optional[str] = None  # 如果不提供，则使用最近的知识库或默认知识库
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = True


class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""
    kb_id: str
    create_time: float
    file_name: Optional[str] = None


@app.get("/api/v1/knowledge/list")
async def list_knowledge_bases():
    """获取所有可用的知识库列表"""
    try:
        # 获取知识库目录下的所有文件夹
        kb_list = []
        kb_dir = Path(os.path.abspath("cache_graph"))
        
        if os.path.exists(kb_dir):
            for kb_id in os.listdir(kb_dir):
                kb_path = kb_dir / kb_id
                if os.path.isdir(kb_path):
                    # 获取文件夹创建时间
                    create_time = os.path.getctime(kb_path)
                    
                    # 尝试获取文件名
                    file_name = None
                    try:
                        # 从知识库元数据中获取文件名
                        meta_file = kb_path / "metadata.json"
                        if os.path.exists(meta_file):
                            with open(meta_file, "r", encoding="utf-8") as f:
                                metadata = json.load(f)
                                if "file_name" in metadata:
                                    file_name = metadata["file_name"]
                    except Exception:
                        pass
                    
                    # 添加到列表
                    kb_list.append(
                        KnowledgeBaseInfo(
                            kb_id=kb_id,
                            create_time=create_time,
                            file_name=file_name
                        )
                    )
        
        # 按创建时间降序排序
        kb_list.sort(key=lambda x: x.create_time, reverse=True)
        return {"kb_list": kb_list}
        
    except Exception as e:
        print(f"获取知识库列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.delete("/api/v1/knowledge/delete/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """删除指定的知识库"""
    try:
        # 验证知识库ID有效性
        if not kb_id or not re.match(r'^[a-zA-Z0-9\-]+$', kb_id):
            raise HTTPException(status_code=400, detail="无效的知识库ID")
        
        # 检查知识库是否存在
        kb_path = Path(os.path.abspath("cache_graph")) / kb_id
        if not os.path.exists(kb_path):
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 释放图资源
        try:
            log_id = str(uuid.uuid4())
            manager = GraphManager(kb_id=kb_id, log_id=log_id)
            manager.release_graph()
        except Exception as e:
            print(f"释放图资源时出错: {str(e)}")
        
        # 删除知识库目录
        import shutil
        shutil.rmtree(kb_path)
        
        # 清除Redis缓存
        try:
            redis_key = f"kb-manager:::{kb_id}"
            RedisKVStore().delete(key=redis_key)
        except Exception as e:
            print(f"清除Redis缓存时出错: {str(e)}")
        
        return {"success": True, "message": "知识库已成功删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"删除知识库时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.post("/api/v1/knowledge/query")
async def query_knowledge(request: Request, query_request: KnowledgeQueryRequest):
    """基于知识库查询，如果知识库中没有相关信息，则使用LLM回答"""
    try:
        # 获取知识库ID，如果未提供则尝试获取最近的一个
        kb_id = query_request.kb_id
        if not kb_id:
            # 可以从会话或配置中获取默认知识库ID
            kb_id = str(uuid.uuid4())  # 临时ID用于测试
        
        log_id = str(uuid.uuid4())
        response_queue = queue.Queue()
        
        # 创建知识库管理器并加载图谱
        manager = GraphManager(kb_id=kb_id, log_id=log_id)
        graph = manager.load_graph()
        
        # 尝试从知识库查询答案
        knowledge_context = None
        
        if graph:
            try:
                # 查询知识库
                query_result = await query_async(
                    graph=graph,
                    q=query_request.query,
                    with_references=True,
                    log_id=log_id
                )
                
                # 正确处理TQueryResponse对象
                if query_result:
                    print(f"知识库查询结果类型: {type(query_result)}")
                    
                    # 提取实体信息
                    entities_info = ""
                    relations_info = ""
                    chunks_info = ""
                    
                    try:
                        # 如果有entities属性
                        if hasattr(query_result, 'entities') and query_result.entities:
                            entities = query_result.entities
                            for entity in entities:
                                if hasattr(entity, 'name') and hasattr(entity, 'description'):
                                    entities_info += f"- {entity.name}: {entity.description}\n"
                        
                        # 如果有relations属性
                        if hasattr(query_result, 'relations') and query_result.relations:
                            relations = query_result.relations
                            for relation in relations:
                                if hasattr(relation, 'source') and hasattr(relation, 'target') and hasattr(relation, 'description'):
                                    relations_info += f"- {relation.source} 和 {relation.target} 的关系: {relation.description}\n"
                        
                        # 如果有chunks属性
                        if hasattr(query_result, 'chunks') and query_result.chunks:
                            chunks = query_result.chunks
                            for chunk in chunks:
                                if hasattr(chunk, 'content'):
                                    chunks_info += f"{chunk.content}\n"
                        
                        # 从context属性中提取
                        if hasattr(query_result, 'context'):
                            context = query_result.context
                            if hasattr(context, 'entities'):
                                for entity_tuple in context.entities:
                                    entity = entity_tuple[0]  # 第一个元素是实体对象
                                    if hasattr(entity, 'name') and hasattr(entity, 'description'):
                                        entities_info += f"- {entity.name}: {entity.description}\n"
                            
                            if hasattr(context, 'relations'):
                                for relation_tuple in context.relations:
                                    relation = relation_tuple[0]  # 第一个元素是关系对象
                                    if hasattr(relation, 'source') and hasattr(relation, 'target') and hasattr(relation, 'description'):
                                        relations_info += f"- {relation.source} 和 {relation.target} 的关系: {relation.description}\n"
                            
                            if hasattr(context, 'chunks'):
                                for chunk_tuple in context.chunks:
                                    chunk = chunk_tuple[0]  # 第一个元素是块对象
                                    if hasattr(chunk, 'content'):
                                        chunks_info += f"{chunk.content}\n"
                        
                        # 组合所有信息
                        knowledge_context = ""
                        
                        if chunks_info.strip():
                            knowledge_context += "原文内容:\n" + chunks_info + "\n\n"
                        
                        if entities_info.strip():
                            knowledge_context += "提取的实体:\n" + entities_info + "\n\n"
                        
                        if relations_info.strip():
                            knowledge_context += "提取的关系:\n" + relations_info + "\n\n"
                        
                        # 如果没有提取到任何信息但query_result是字符串，直接使用
                        if not knowledge_context and isinstance(query_result, str):
                            knowledge_context = query_result
                        
                        # 如果query_result有response属性且为字符串，添加到context
                        if hasattr(query_result, 'response') and isinstance(query_result.response, str):
                            knowledge_context += "生成的回答:\n" + query_result.response
                        
                        print(f"从知识库提取的上下文: {knowledge_context[:300]}...")
                        
                    except Exception as e:
                        print(f"处理知识库返回结果时出错: {str(e)}")
                        # 尝试直接将查询结果转换为字符串作为后备方案
                        try:
                            knowledge_context = str(query_result)
                            print(f"转换为字符串的知识库结果: {knowledge_context[:300]}...")
                        except:
                            print("无法将查询结果转换为字符串")
                
            except Exception as e:
                print(f"知识库查询出错: {str(e)}")
        
        # 固定使用DeepSeek-V3模型
        model = "DeepSeek-V3"
        
        # 构建带有提示的查询内容，加入知识库上下文
        prompt = ""
        if knowledge_context:
            prompt = f"""用户问题: {query_request.query}
            
根据以下从文档中提取的信息回答：
-----
{knowledge_context}
-----

请直接回答用户问题，不要引用上述信息来源，不要提及你在使用文档信息，用自然的方式回答，就像这些知识是你已知的一样。请保持简洁明了，直接给出答案。如果文档中没有相关信息，请诚实地说明你无法回答。"""
        else:
            prompt = f"用户问题: {query_request.query}\n\n如果你知道答案，请直接回答。"
        
        print(f"发送到LLM的提示: {prompt[:500]}...")
        
        # 始终使用DeepSeek模型生成回答，即使有知识库结果
        t_openai = asyncio.create_task(fetch_deepseek_response(
            model, 
            prompt, 
            query_request.max_tokens, 
            query_request.temperature, 
            response_queue,
            request
        ))
        
        return StreamingResponse(
            stream_from_queue(response_queue),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        print(f"知识库查询处理出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
