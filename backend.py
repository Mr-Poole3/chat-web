from fastapi import FastAPI, HTTPException, Request, Depends, Body, UploadFile, File, Form
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

# 订阅计划模型
class SubscriptionPlan(BaseModel):
    id: int
    name: str
    duration_days: int
    price: float
    description: Optional[str] = None
    features: Dict[str, Any]
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

# 用户订阅模型
class UserSubscription(BaseModel):
    id: Optional[int] = None
    user_id: int
    plan_id: int
    start_date: datetime.datetime
    end_date: datetime.datetime
    status: str = "active"
    payment_id: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

# 订阅创建请求模型
class SubscriptionCreateRequest(BaseModel):
    user_id: int
    plan_id: int
    payment_id: Optional[str] = None

# 订阅列表响应模型
class SubscriptionListResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: List[SubscriptionPlan]

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
async def list_models(request: Request):
    """列出可用的模型"""
    try:
        # 获取用户ID
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                username = payload.get("sub")
                
                if username:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        user_data = cursor.fetchone()
                        if user_data:
                            user_id = user_data['id']
                    conn.close()
            except Exception as e:
                print(f"解析JWT令牌出错: {e}")
        
        # 检查用户是否是VIP
        is_vip = await check_user_vip_status(user_id) if user_id else False
        
        # 根据用户权限返回可用模型
        if is_vip:
            # VIP用户可以访问所有模型
            available_models = ["DeepSeek-V3", "DeepSeek-R1", "gpt-4o-mini"]
        else:
            # 非VIP用户只能访问DeepSeek模型
            available_models = ["DeepSeek-V3", "DeepSeek-R1"]
        
        return ModelListResponse(
            code=200,
            msg="success",
            models=available_models
        )
    except Exception as e:
        print(f"获取模型列表出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


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
        # 获取用户ID
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                username = payload.get("sub")
                
                if username:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        user_data = cursor.fetchone()
                        if user_data:
                            user_id = user_data['id']
                    conn.close()
            except Exception as e:
                print(f"解析JWT令牌出错: {e}")
        
        # 检查用户是否有权限使用选择的模型
        has_permission = await check_model_permission(user_id, chat_request.model) if user_id else False
        if not has_permission:
            raise HTTPException(status_code=403, detail=f"您没有权限使用模型: {chat_request.model}，请升级到VIP")
            
        response_queue = queue.Queue()
        
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
async def process_document(request: Request, file: UploadFile = File(...), user_id: Optional[str] = Form(None)):
    """处理上传的文档并提取知识"""
    temp_dir = None
    try:
        # 获取用户ID，优先使用表单中提供的，其次从请求头获取
        if not user_id:
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
                        conn.close()
                except Exception as e:
                    print(f"解析JWT令牌出错: {e}")
        
        # 如果没有用户ID，返回错误
        if not user_id:
            print("未提供用户ID，无法处理文档")
            return {"results": [{"type": "错误", "confidence": 0, "text": "未提供用户ID，请重新登录后再试"}], "kb_id": None}
        
        # 检查用户是否是VIP
        is_vip = await check_user_vip_status(int(user_id))
        if not is_vip:
            return {"results": [{"type": "错误", "confidence": 0, "text": "文档处理功能仅对VIP用户开放，请升级会员"}], "kb_id": None}
            
        print(f"处理用户 {user_id} 上传的文档: {file.filename}")
        
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
                # 创建元数据文件，添加用户ID
                metadata = {
                    "file_name": original_filename,
                    "upload_time": time.time(),
                    "token_count": token_count,
                    "user_id": user_id  # 保存用户ID到元数据
                }
                meta_file = kb_path / "metadata.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                print(f"保存知识库元数据成功: {kb_id}, 用户ID: {user_id}")
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
async def list_knowledge_bases(request: Request, user_id: Optional[str] = None):
    """获取所有可用的知识库列表"""
    try:
        # 获取知识库目录下的所有文件夹
        kb_list = []
        kb_dir = Path(os.path.abspath("cache_graph"))
        
        # 从请求头获取用户ID
        if not user_id:
            user_id = request.headers.get("X-User-ID")
            print(f"从请求头获取用户ID: {user_id}")
        
        # 如果没有获取到用户ID，返回空列表
        if not user_id:
            print("未提供用户ID，返回空列表")
            return {"kb_list": []}
            
        print(f"获取用户ID: {user_id} 的知识库列表")
        
        if os.path.exists(kb_dir):
            for kb_id in os.listdir(kb_dir):
                kb_path = kb_dir / kb_id
                if os.path.isdir(kb_path):
                    # 获取文件夹创建时间
                    create_time = os.path.getctime(kb_path)
                    
                    # 尝试获取文件名和用户ID
                    file_name = None
                    kb_user_id = None
                    try:
                        # 从知识库元数据中获取文件名和用户ID
                        meta_file = kb_path / "metadata.json"
                        if os.path.exists(meta_file):
                            with open(meta_file, "r", encoding="utf-8") as f:
                                metadata = json.load(f)
                                if "file_name" in metadata:
                                    file_name = metadata["file_name"]
                                if "user_id" in metadata:
                                    kb_user_id = metadata["user_id"]
                    except Exception as e:
                        print(f"读取知识库元数据出错: {str(e)}")
                    
                    # 只添加属于当前用户的知识库
                    if kb_user_id == user_id:
                        print(f"找到用户 {user_id} 的知识库: {kb_id}")
                        kb_list.append(
                            KnowledgeBaseInfo(
                                kb_id=kb_id,
                                create_time=create_time,
                                file_name=file_name
                            )
                        )
                    else:
                        print(f"知识库 {kb_id} 不属于用户 {user_id}, 属于用户 {kb_user_id}")
        
        # 按创建时间降序排序
        kb_list.sort(key=lambda x: x.create_time, reverse=True)
        print(f"返回用户 {user_id} 的知识库列表，共 {len(kb_list)} 个")
        return {"kb_list": kb_list}
        
    except Exception as e:
        print(f"获取知识库列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.delete("/api/v1/knowledge/delete/{kb_id}")
async def delete_knowledge_base(request: Request, kb_id: str, user_id: Optional[str] = None):
    """删除指定的知识库"""
    try:
        # 从请求参数或请求头中获取用户ID
        if not user_id:
            user_id = request.headers.get("X-User-ID")
        
        if not user_id:
            print("未提供用户ID，无法删除知识库")
            raise HTTPException(status_code=401, detail="未提供用户ID，请重新登录后再试")
            
        # 验证知识库ID有效性
        if not kb_id or not re.match(r'^[a-zA-Z0-9\-]+$', kb_id):
            raise HTTPException(status_code=400, detail="无效的知识库ID")
        
        # 检查知识库是否存在
        kb_path = Path(os.path.abspath("cache_graph")) / kb_id
        if not os.path.exists(kb_path):
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 验证用户是否有权限删除此知识库
        kb_owner = None
        try:
            meta_file = kb_path / "metadata.json"
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    if "user_id" in metadata:
                        kb_owner = metadata["user_id"]
            
            # 如果知识库属于其他用户，拒绝删除
            if kb_owner and kb_owner != user_id:
                print(f"用户 {user_id} 尝试删除用户 {kb_owner} 的知识库 {kb_id}")
                raise HTTPException(status_code=403, detail="您没有权限删除此知识库")
        except HTTPException:
            raise
        except Exception as e:
            print(f"验证知识库所有者时出错: {str(e)}")
            # 如果无法验证所有者，默认允许删除（不阻塞功能）
        
        print(f"用户 {user_id} 删除知识库 {kb_id}")
        
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
        # 获取用户ID
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                username = payload.get("sub")
                
                if username:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        user_data = cursor.fetchone()
                        if user_data:
                            user_id = user_data['id']
                    conn.close()
            except Exception as e:
                print(f"解析JWT令牌出错: {e}")
        
        if not user_id:
            print("未提供用户ID，无法查询知识库")
            raise HTTPException(status_code=401, detail="未提供用户ID，请重新登录后再试")
        
        # 检查用户是否是VIP
        is_vip = await check_user_vip_status(user_id)
        if not is_vip:
            raise HTTPException(status_code=403, detail="知识库查询功能仅对VIP用户开放，请升级会员")
            
        # 获取知识库ID，如果未提供则尝试获取最近的一个
        kb_id = query_request.kb_id
        if not kb_id:
            # 可以从会话或配置中获取默认知识库ID
            kb_id = str(uuid.uuid4())  # 临时ID用于测试
        
        # 验证用户是否有权限查询此知识库
        kb_path = Path(os.path.abspath("cache_graph")) / kb_id
        if os.path.exists(kb_path):
            kb_owner = None
            try:
                meta_file = kb_path / "metadata.json"
                if os.path.exists(meta_file):
                    with open(meta_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        if "user_id" in metadata:
                            kb_owner = metadata["user_id"]
                
                # 如果知识库属于其他用户，拒绝查询
                if kb_owner and str(kb_owner) != str(user_id):
                    print(f"用户 {user_id} 尝试查询用户 {kb_owner} 的知识库 {kb_id}")
                    raise HTTPException(status_code=403, detail="您没有权限查询此知识库")
            except HTTPException:
                raise
            except Exception as e:
                print(f"验证知识库所有者时出错: {str(e)}")
                # 继续处理，因为这不是关键错误
        
        print(f"用户 {user_id} 查询知识库 {kb_id}: {query_request.query}")
        
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
                    
                    # 转换结果为字符串
                    try:
                        knowledge_context = convert_numpy_types(query_result)
                    except Exception as e:
                        print(f"转换查询结果时出错: {str(e)}")
                        # 如果转换失败，尝试简单字符串化
                        knowledge_context = str(query_result)
            except Exception as e:
                print(f"查询知识库时出错: {str(e)}")
                # 在这里可以选择是否向用户显示错误信息
        
        # 使用LLM回答问题
        prompt_template = """
作为一个智能助手，请基于以下信息回答问题。

如果信息中包含答案，请直接回答。
如果信息不足以回答问题，请礼貌地表示无法基于当前信息回答，并建议用户尝试不同的问题或上传更多相关文档。
不要编造信息，不要声明自己是AI助手，直接回答即可。

相关信息：
{context}

用户问题：{query}
"""
        
        # 如果有知识库结果，则使用知识库结果构建上下文
        if knowledge_context:
            prompt = prompt_template.format(
                context=knowledge_context,
                query=query_request.query
            )
        else:
            # 如果没有知识库结果，直接告知用户
            prompt = prompt_template.format(
                context="没有找到相关信息。",
                query=query_request.query
            )
        
        # 使用不同的模型API生成回答
        model = "DeepSeek-V3"  # 默认模型
        
        # 发送请求到LLM服务
        async def generate_response():
            try:
                # 根据模型类型选择不同的API
                if "gpt" in model.lower() or "azure" in model.lower():
                    await fetch_azure_response(
                        model=model,
                        prompt=prompt,
                        max_tokens=query_request.max_tokens,
                        temperature=query_request.temperature,
                        response_queue=response_queue,
                        request=request
                    )
                else:
                    await fetch_deepseek_response(
                        model=model,
                        prompt=prompt,
                        max_tokens=query_request.max_tokens,
                        temperature=query_request.temperature,
                        response_queue=response_queue,
                        request=request
                    )
            except Exception as e:
                print(f"生成回答时出错: {str(e)}")
                # 将错误消息放入队列
                response_queue.put({"error": str(e)})
            finally:
                # 标记生成完成
                response_queue.put(None)
        
        # 启动异步任务生成回答
        asyncio.create_task(generate_response())
        
        # 流式返回生成的内容
        return StreamingResponse(
            stream_from_queue(response_queue),
            media_type="text/event-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"查询知识库时出错: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"内部服务器错误: {str(e)}"}
        )


# 权限和订阅相关功能
# ----------------------

# 检查用户是否有VIP权限
async def check_user_vip_status(user_id: int):
    try:
        if not user_id:
            return False
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 检查用户是否有活跃的订阅
            sql = """
            SELECT us.*, sp.features
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id = %s AND us.status = 'active' AND us.end_date > NOW()
            ORDER BY us.end_date DESC
            LIMIT 1
            """
            cursor.execute(sql, (user_id,))
            subscription = cursor.fetchone()
            
            if subscription:
                # 用户有活跃订阅
                return True
            else:
                # 用户没有活跃订阅
                return False
    except Exception as e:
        print(f"检查用户VIP状态时出错: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# 检查用户是否有权限使用模型
async def check_model_permission(user_id: int, model: str):
    # 非VIP用户只能使用DeepSeek模型
    is_vip = await check_user_vip_status(user_id)
    
    if is_vip:
        # VIP用户可以使用所有模型
        return True
    else:
        # 非VIP用户只能使用DeepSeek模型
        return model in ["DeepSeek-V3", "DeepSeek-R1"]

# 获取用户当前订阅信息
@app.get("/api/v1/user/subscription")
async def get_user_subscription(request: Request):
    try:
        # 从请求头获取用户ID
        user_id = None
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
                    conn.close()
            except Exception as e:
                print(f"解析JWT令牌出错: {e}")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="未授权，请先登录")
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 获取用户当前的活跃订阅
            sql = """
            SELECT us.id, us.user_id, us.plan_id, sp.name AS plan_name, 
                   sp.duration_days, sp.price, sp.description, sp.features,
                   us.start_date, us.end_date, us.status, us.payment_id,
                   us.created_at, us.updated_at
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id = %s AND us.status = 'active' AND us.end_date > NOW()
            ORDER BY us.end_date DESC
            LIMIT 1
            """
            cursor.execute(sql, (user_id,))
            subscription = cursor.fetchone()
            
            # 获取所有可用的订阅计划
            sql_plans = """
            SELECT id, name, duration_days, price, description, features
            FROM subscription_plans
            """
            cursor.execute(sql_plans)
            all_plans = cursor.fetchall()
            
            # 处理features字段，将其转换为字典
            for plan in all_plans:
                if 'features' in plan and plan['features']:
                    try:
                        plan['features'] = json.loads(plan['features'])
                    except:
                        plan['features'] = {}
            
            # 准备响应数据
            response_data = {
                "is_vip": subscription is not None,
                "subscription": subscription,
                "available_plans": all_plans
            }
            
            # 如果有订阅，处理日期和features字段
            if subscription:
                if 'features' in subscription and subscription['features']:
                    try:
                        subscription['features'] = json.loads(subscription['features'])
                    except:
                        subscription['features'] = {}
                
                # 处理日期格式
                for date_field in ['start_date', 'end_date', 'created_at', 'updated_at']:
                    if date_field in subscription and subscription[date_field]:
                        subscription[date_field] = subscription[date_field].isoformat()
            
        conn.close()
        return {"code": 200, "msg": "success", "data": response_data}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"获取用户订阅信息时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# 获取所有订阅计划
@app.get("/api/v1/subscription/plans", response_model=SubscriptionListResponse)
async def get_subscription_plans():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            SELECT id, name, duration_days, price, description, features
            FROM subscription_plans
            """
            cursor.execute(sql)
            plans = cursor.fetchall()
            
            # 处理features字段，将其转换为字典
            for plan in plans:
                if 'features' in plan and plan['features']:
                    try:
                        plan['features'] = json.loads(plan['features'])
                    except:
                        plan['features'] = {}
        
        conn.close()
        return SubscriptionListResponse(code=200, msg="success", data=plans)
    except Exception as e:
        print(f"获取订阅计划时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# 创建用户订阅（实际支付功能未实现，仅模拟订阅创建）
@app.post("/api/v1/user/subscription")
async def create_user_subscription(request: Request, subscription_data: SubscriptionCreateRequest):
    try:
        # 从请求头获取用户ID
        authorized_user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                username = payload.get("sub")
                
                if username:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        user_data = cursor.fetchone()
                        if user_data:
                            authorized_user_id = user_data['id']
                    conn.close()
            except Exception as e:
                print(f"解析JWT令牌出错: {e}")
        
        # 验证用户身份
        if not authorized_user_id or authorized_user_id != subscription_data.user_id:
            raise HTTPException(status_code=403, detail="没有权限为此用户创建订阅")
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 获取订阅计划详情
            cursor.execute("SELECT duration_days FROM subscription_plans WHERE id = %s", (subscription_data.plan_id,))
            plan = cursor.fetchone()
            
            if not plan:
                raise HTTPException(status_code=404, detail="订阅计划不存在")
                
            # 计算订阅开始和结束日期
            start_date = datetime.datetime.now()
            end_date = start_date + datetime.timedelta(days=plan['duration_days'])
            
            # 检查用户是否已有活跃订阅
            cursor.execute(
                "SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active' AND end_date > NOW()",
                (subscription_data.user_id,)
            )
            existing_subscription = cursor.fetchone()
            
            if existing_subscription:
                # 如果有现有订阅，将其标记为取消
                cursor.execute(
                    "UPDATE user_subscriptions SET status = 'cancelled', updated_at = NOW() WHERE id = %s",
                    (existing_subscription['id'],)
                )
            
            # 创建新订阅
            cursor.execute(
                """
                INSERT INTO user_subscriptions 
                (user_id, plan_id, start_date, end_date, status, payment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (subscription_data.user_id, subscription_data.plan_id, start_date, end_date, 
                 'active', subscription_data.payment_id)
            )
            
            # 获取新创建的订阅ID
            subscription_id = cursor.lastrowid
            
        conn.close()
        return {
            "code": 200, 
            "msg": "订阅创建成功", 
            "data": {
                "id": subscription_id,
                "user_id": subscription_data.user_id,
                "plan_id": subscription_data.plan_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "status": "active"
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"创建用户订阅时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# 取消用户订阅
@app.put("/api/v1/user/subscription/cancel")
async def cancel_user_subscription(request: Request, user_id: int = Body(...)):
    try:
        # 从请求头获取用户ID
        authorized_user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                username = payload.get("sub")
                
                if username:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id, role FROM users WHERE username = %s", (username,))
                        user_data = cursor.fetchone()
                        if user_data:
                            authorized_user_id = user_data['id']
                            is_admin = user_data.get('role') == 'admin'
                    conn.close()
            except Exception as e:
                print(f"解析JWT令牌出错: {e}")
        
        # 验证用户身份
        if not authorized_user_id or (authorized_user_id != user_id and not is_admin):
            raise HTTPException(status_code=403, detail="没有权限取消此用户的订阅")
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 获取用户的活跃订阅
            cursor.execute(
                "SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active' AND end_date > NOW()",
                (user_id,)
            )
            subscription = cursor.fetchone()
            
            if not subscription:
                raise HTTPException(status_code=404, detail="未找到活跃的订阅")
            
            # 将订阅状态更新为取消
            cursor.execute(
                "UPDATE user_subscriptions SET status = 'cancelled', updated_at = NOW() WHERE id = %s",
                (subscription['id'],)
            )
            
        conn.close()
        return {"code": 200, "msg": "订阅已取消"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"取消用户订阅时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
