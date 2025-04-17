import os
import sys
import time
from pathlib import Path
from multiprocessing import Lock

_cur_dir = Path(os.path.split(os.path.abspath(__file__))[0])
_prj_dir = Path(os.path.split(_cur_dir)[0])
_root_dir = Path(os.path.split(_prj_dir)[0])
sys.path.append(str(_root_dir))

from lib import log
from lib.redis_kv import RedisKVStore
from knowledge_base.core.grag import load
from knowledge_base.config.conf import DOMAIN, ENTITY_TYPES, EXAMPLE_QUERIES

REDIS_PREFIX = "kb-manager"
_graph_cache_dir = _root_dir / "cache_graph"
if not os.path.exists(_graph_cache_dir):
    _graph_cache_dir.mkdir(exist_ok=True)


class GraphManager:
    # 类级别的缓存字典，用于存储所有图实例
    _graph_instances = {}
    _graph_lock = Lock()  # 用于确保线程安全

    def __init__(
        self,
        kb_id,
        max_cache_size=5,
        expiration_time=300,
        log_id=None,
    ):
        self.kb_id = kb_id
        self.max_cache_size = max_cache_size
        self.expiration_time = expiration_time
        self.log_id = log_id
        self.redis_key = f"{REDIS_PREFIX}:::{self.kb_id}"
        self.example_queries = EXAMPLE_QUERIES

    def load_graph(self):
        """
        加载图，优先从缓存获取，否则从磁盘加载
        """
        with self._graph_lock:
            current_time = time.time()

            # 检查缓存中是否存在且未过期
            if self.kb_id in self._graph_instances:
                last_access_time = RedisKVStore().get(self.redis_key)

                if (
                    last_access_time
                    and current_time - float(last_access_time) <= self.expiration_time
                ):
                    # 更新访问时间
                    RedisKVStore().set(
                        key=self.redis_key, value=current_time, log_id=self.log_id
                    )
                    log.log_time(self.log_id, f"从缓存加载图: {self.kb_id}", current_time)
                    return self._graph_instances[self.kb_id]
                else:
                    # 已过期，从缓存中移除
                    log.log(self.log_id, f"图 {self.kb_id} 已过期，重新加载")
                    del self._graph_instances[self.kb_id]

            # 缓存容量检查
            if len(self._graph_instances) >= self.max_cache_size:
                # 移除最旧的图
                oldest_kb = next(iter(self._graph_instances.keys()))
                del self._graph_instances[oldest_kb]
                log.log(self.log_id, f"缓存已满，移除最旧的图: {oldest_kb}")

            # 从磁盘加载新图
            log.log(self.log_id, f"重新从磁盘加载图: {self.kb_id}")
            graph = self._load_from_disk()

            # 存入缓存
            self._graph_instances[self.kb_id] = graph
            RedisKVStore().set(self.redis_key, current_time, log_id=self.log_id)

            return graph

    def _load_from_disk(self):
        """从磁盘加载图"""
        kb_dir = str(_graph_cache_dir / self.kb_id)
        graph = load(
            dir_path=str(kb_dir),
            domain=DOMAIN,
            entity_types=ENTITY_TYPES,
            example_queries=self.example_queries,
        )
        return graph

    def release_graph(self):
        """释放图资源"""
        with self._graph_lock:
            if self.kb_id in self._graph_instances:
                del self._graph_instances[self.kb_id]
                log.log(self.log_id, f"释放图: {self.kb_id}")

    @classmethod
    def cleanup(cls, cleanup_interval: int = 300, log_id: int | str | None = None):
        """清理所有过期的图"""
        current_time = time.time()
        with cls._graph_lock:
            for kb_id in list(cls._graph_instances.keys()):
                redis_key = f"{REDIS_PREFIX}:::{kb_id}"
                last_access_time = RedisKVStore().get(key=redis_key)
                if (
                    not last_access_time
                    or current_time - float(last_access_time) > cleanup_interval
                ):
                    del cls._graph_instances[kb_id]
                    log.log(log_id, f"清理过期图: {kb_id}")


def main():
    test_log_id_1 = "11111111111111111111111"
    test_log_id_2 = "22222222222222222222222"
    test_kb_id = "1"
    test_cache_time = 100

    # 创建两个管理器实例，使用相同的 kb_id
    manager1 = GraphManager(
        kb_id=test_kb_id,
        expiration_time=test_cache_time,
        log_id=test_log_id_1,
    )

    manager2 = GraphManager(
        kb_id=test_kb_id,
        expiration_time=test_cache_time,
        log_id=test_log_id_2,
    )

    # 加载图实例
    graph1 = manager1.load_graph()
    graph2 = manager2.load_graph()

    # 验证是否是同一个实例
    print(f"graph2和graph1是否为同一实例: {graph1 is graph2}")  # 应该输出 True

    # 等待过期时间后再次加载
    time.sleep(5)  # 超过过期时间
    graph3 = manager1.load_graph()  # 将创建新实例
    print(f"graph3和graph1是否为同一实例: {graph3 is graph1}")

    # 清理
    GraphManager.cleanup(log_id=log.uid())


if __name__ == "__main__":
    main()
