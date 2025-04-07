from fastapi import Depends

from auth import User, get_current_user
from base import app


# 获取当前用户信息
@app.get("/api/v1/auth/me", response_model=User)
async def get_user_info(current_user: dict = Depends(get_current_user)):
    return current_user
