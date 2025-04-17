import os
import sys
import time
from pathlib import Path

_cur_dir = Path(os.path.split(os.path.abspath(__file__))[0])
_prj_dir = Path(os.path.split(_cur_dir)[0])
_root_dir = Path(os.path.split(_prj_dir)[0])
sys.path.append(str(_root_dir))

from lib import log
from knowledge_base.core.manager import GraphManager


@log.record()
def cleanup_grag(cleanup_interval=600, log_id=None):
    """
    定期清理过期的图实例

    Args:
        cleanup_interval: 清理间隔时间（秒），默认60秒
    """
    while True:
        try:
            log.log(log_id, "开始执行图实例清理...")

            # 执行清理
            GraphManager.cleanup(cleanup_interval=cleanup_interval, log_id=log_id)

            log.log(log_id, f"清理完成，等待 {cleanup_interval} 秒后执行下一次清理")
            time.sleep(cleanup_interval)

        except KeyboardInterrupt:
            log.log(log_id, "收到终止信号，清理脚本退出")
            break
        except Exception as e:
            log.log(log_id, f"清理过程发生错误: {str(e)}")
            time.sleep(5)  # 发生错误时短暂等待后继续


if __name__ == "__main__":
    cleanup_grag()
