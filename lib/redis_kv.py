import os
import sys
import json
import time

_cur_dir = os.path.split(os.path.abspath(__file__))[0]
_root_dir = os.path.split(_cur_dir)[0]
if _root_dir not in sys.path:
    sys.path.append(_root_dir)

from lib import log
from lib.redis_conf import CLIENT
from lib.json_processor import json_dump


class RedisKVStore:
    def __init__(self, client=CLIENT):
        # 创建 Redis 连接
        self.client = client

    def set(self, key, value, expire_time=None, log_id=None):
        """设置键值"""
        try:
            value = json_dump(value)
            self.client.set(name=key, value=value, ex=expire_time)
            return True
        except Exception as e:
            log.error(log_id, f"Error setting key '{key}': {str(e)}")
            print(log.get_trace_back())
            return False

    def get(self, key):
        """获取键值"""
        try:
            value = self.client.get(key)
            return value if value is not None else None
        except Exception as e:
            log.error(None, f"Error getting key '{key}': {str(e)}")
            return ""

    def get_json(self, key):
        """获取键值"""
        try:
            value = self.client.get(key)
            if isinstance(value, str) or isinstance(value, bytes):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError as e:
                    value = value
            return value
        except Exception as e:
            log.error(None, f"Error getting key '{key}': {str(e)}")
            return ""

    def delete(self, key):
        """删除键"""
        try:
            result = self.client.delete(key)
            log.log(
                None,
                f"Key '{key}' deleted." if result else f"Key '{key}' does not exist.",
            )
        except Exception as e:
            log.error(None, f"Error deleting key '{key}': {str(e)}")
            return ""

    def exists(self, key):
        """检查键是否存在"""
        try:
            return self.client.exists(key) == 1
        except Exception as e:
            log.error(None, f"Error checking existence of key '{key}': {str(e)}")
            return False

    def increment(self, key, amount=1):
        """增加键的值"""
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            log.error(None, f"Error incrementing key '{key}': {str(e)}")
            return 0

    def set_expire(self, key, seconds):
        """设置键的过期时间"""
        try:
            self.client.expire(key, seconds)
            return f"Expiration for key '{key}' set to {seconds} seconds."
        except Exception as e:
            return f"Error setting expiration for key '{key}': {str(e)}"

    def hset(self, key, field, value, expire_time=None, log_id=None):
        """设置哈希表中的字段值"""
        try:
            self.client.hset(key, field, value)
            if expire_time:
                self.client.expire(key, expire_time)
            return True
        except Exception as e:
            log.error(
                log_id, f"Error setting field '{field}' in hash '{key}': {str(e)}"
            )
            return False

    def hget(self, key, field, log_id=None):
        """获取哈希表中的字段值"""
        try:
            value = self.client.hget(key, field)
            if value is not None:
                log.log(log_id, f"Successfully got field '{field}' from hash '{key}'")
                return value
            log.log(log_id, f"Field '{field}' not found in hash '{key}'")
            return None
        except Exception as e:
            log.error(
                log_id, f"Error getting field '{field}' from hash '{key}': {str(e)}"
            )
            return None

    def hgetall(self, key, log_id=None):
        """获取哈希表中的所有字段和值"""
        try:
            value = self.client.hgetall(key)
            if value:
                log.log(log_id, f"Successfully got all fields from hash '{key}'")
                return value
            log.log(log_id, f"No fields found in hash '{key}'")
            return None
        except Exception as e:
            log.error(log_id, f"Error getting all fields from hash '{key}': {str(e)}")
            return None

    def set_nx(self, key, value, log_id=None):
        """设置键值，如果键不存在"""
        try:
            return self.client.setnx(key, value)
        except Exception as e:
            log.error(log_id, f"Error setting key '{key}': {str(e)}")
            return False

    def fuzzy_search(self, key, log_id=None):
        """
        在 Redis 中执行模糊搜索，返回匹配的键和对应的值。

        :param key: 搜索的模式（如 'user:*'）
        :param log_id: 日志ID
        :return: 一个包含匹配键和值的字典
        """
        try:
            s_time = time.time()
            keys = self.client.keys(key)
            matching_data = {k: self.get_json(k) for k in keys}
            log.log_time(
                log_id,
                f"Found {len(matching_data)} matches for pattern '{key}'",
                s_time,
            )

            return matching_data

        except Exception as e:
            log.error(
                log_id, f"Error during fuzzy search for pattern '{key}': {str(e)}"
            )
            return {}


if __name__ == "__main__":
    kv = RedisKVStore()
    print(kv.set("test", 111))
    print(kv.get("test"))
