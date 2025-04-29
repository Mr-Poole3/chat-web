import backend
import chat
import auth
import me
from base import app
import os

if __name__ == '__main__':
    import uvicorn
    
    # 检测是否为开发环境
    is_dev = os.environ.get("ENVIRONMENT", "development") == "development"
    
    # 配置参数
    uvicorn_config = {
        "app": "main:app",  # 使用字符串形式引用app以支持热重载
        "host": "0.0.0.0",
        "port": 8000,
        "timeout_keep_alive": 0,
        "limit_concurrency": None,
        "limit_max_requests": None
    }
    
    # 在开发环境添加热重载
    if is_dev:
        uvicorn_config.update({
            "reload": True,  # 启用热重载
            "reload_dirs": ["./"],  # 监视的目录
            "workers": 1  # 开发环境使用单个工作进程
        })
        print("开发模式已启用，热重载功能已开启")
    
    # 启动服务器
    uvicorn.run(**uvicorn_config)