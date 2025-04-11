from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://0.0.0.0:5173",
        "http://0.0.0.0:8000",
        "http://localhost:8000",
        "http://localhost:7863",
        "http://0.0.0.0:7863",
        "http://47.116.178.101",  # 允许服务器访问
        "http://47.116.178.101:7863",
        "http://47.116.178.101:5173",
        "http://47.116.178.101:8000",
    ],  # 允许Vue开发服务器和生产环境
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
