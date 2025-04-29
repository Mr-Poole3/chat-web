import backend
import chat
import auth
import me
from base import app

if __name__ == '__main__':
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_keep_alive=0,
        limit_concurrency=None,
        limit_max_requests=None
    )
