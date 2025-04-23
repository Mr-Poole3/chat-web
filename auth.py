from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
import mysql.connector
import jwt
import datetime
from datetime import timedelta
from base import app
from jose import JWTError
import bcrypt
from mysql.connector import Error
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取环境模式
ENV = os.getenv("ENV", "development")

# JWT配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "1234567890")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 默认24小时

# 根据环境选择数据库配置
if ENV == "production":
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "ai"),
        "port": int(os.getenv("DB_PORT", "3306"))
    }
else:
    # 开发环境配置
    db_config = {
        "host": os.getenv("DEV_DB_HOST", "localhost"),
        "user": os.getenv("DEV_DB_USER", "root"),
        "password": os.getenv("DEV_DB_PASSWORD", ""),
        "database": os.getenv("DEV_DB_NAME", "ai"),
        "port": int(os.getenv("DEV_DB_PORT", "3306"))
    }

# 安全配置
security = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


# Pydantic模型
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str


class TokenData(BaseModel):
    username: Optional[str] = None

class ChangePasswordData(BaseModel):
    current_password: str
    new_password: str


# 数据库连接函数
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# 密码验证函数
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# 获取密码哈希
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# 创建访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# 获取当前用户
async def get_current_user(token: str = Depends(security)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (token_data.username,))
        user = cursor.fetchone()
        if user is None:
            raise credentials_exception
        return user
    finally:
        cursor.close()
        conn.close()


@app.post("/api/v1/auth/change-password", response_model=dict)
async def change_password(change_password_data: ChangePasswordData, user: dict = Depends(get_current_user)):
    # 验证当前密码
    if not verify_password(change_password_data.current_password, user['password']):
        raise HTTPException(status_code=400, detail="当前密码错误")

    # 验证新密码强度
    if len(change_password_data.new_password) < 8 or not any(c.isupper() for c in change_password_data.new_password) or \
       not any(c.islower() for c in change_password_data.new_password) or not any(c.isdigit() for c in change_password_data.new_password):
        raise HTTPException(
            status_code=400,
            detail="新密码必须至少包含8个字符，并包含大写字母、小写字母和数字"
        )

    # 更新密码
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_password = get_password_hash(change_password_data.new_password)
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, user['username']))
        conn.commit()
        return {"message": "密码修改成功"}
    finally:
        cursor.close()
        conn.close()


# 注册路由
@app.post("/api/v1/auth/register", response_model=dict)
async def register(user: UserCreate):
    # 验证密码强度
    if len(user.password) < 8 or not any(c.isupper() for c in user.password) or \
        not any(c.islower() for c in user.password) or not any(c.isdigit() for c in user.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and numbers"
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")

        # 检查邮箱是否已存在
        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # 密码加密
        hashed_password = get_password_hash(user.password)

        # 插入新用户
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (user.username, user.email, hashed_password)
        )
        conn.commit()
        
        # 获取新用户ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        user_record = cursor.fetchone()
        
        if user_record:
            user_id = user_record[0]
            
            # 赠送3天体验VIP
            start_date = datetime.datetime.now()
            end_date = start_date + datetime.timedelta(days=3)
            
            # 查找基础VIP套餐（周卡）
            cursor.execute("SELECT id FROM subscription_plans WHERE name = '周卡VIP' LIMIT 1")
            plan_record = cursor.fetchone()
            
            if plan_record:
                plan_id = plan_record[0]
                # 创建体验订阅
                cursor.execute(
                    """
                    INSERT INTO user_subscriptions 
                    (user_id, plan_id, start_date, end_date, status, payment_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, plan_id, start_date, end_date, 'active', '注册赠送体验卡')
                )
                conn.commit()

        return {"message": "User registered successfully with 3-day VIP trial"}
    finally:
        cursor.close()
        conn.close()


# 登录路由
@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 打印接收到的数据，用于调试
        print(f"Received login request for username: {form_data.username}")

        cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()

        if not user:
            print(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 打印密码验证结果，用于调试
        is_valid = verify_password(form_data.password, user["password"]) # type: ignore
        print(f"Password validation result: {is_valid}")

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires # type: ignore
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user["username"] # type: ignore
        }
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


# 获取当前用户信息
@app.get("/auth/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 检查用户是否是第一次登录（通过检查是否有聊天记录）
        cursor.execute("SELECT COUNT(*) as count FROM chat_sessions WHERE user_id = %s", (current_user["id"],))
        chat_count = cursor.fetchone()["count"]
        
        # 返回用户信息，但不包含密码
        user_info = {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "created_at": current_user["created_at"].isoformat() if isinstance(current_user["created_at"], datetime.datetime) else current_user["created_at"],
            "updated_at": current_user["updated_at"].isoformat() if isinstance(current_user["updated_at"], datetime.datetime) else current_user["updated_at"],
            "is_new_user": chat_count == 0  # 如果没有聊天记录，说明是新用户
        }
        return user_info
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
