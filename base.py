from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1:8000", "http://localhost:8000", "http://localhost:8080", "http://127.0.0.1:8080"],  # 允许Vue开发服务器和生产环境
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
