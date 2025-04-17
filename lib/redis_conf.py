import os

import redis
from dotenv import load_dotenv

load_dotenv()
_REDIS_CONF = {
    "host": os.getenv("REDIS_HOST", "127.0.0.1"),
    "port": os.getenv("REDIS_PORT", "6379"),
    "db": 0,
}
CLIENT = redis.StrictRedis(**_REDIS_CONF, decode_responses=True)
