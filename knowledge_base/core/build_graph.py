import os
import sys
import time
import asyncio
from typing import Any
from pathlib import Path
import docx

from fast_graphrag import GraphRAG

_cur_dir = Path(os.path.split(os.path.abspath(__file__))[0])
_prj_dir = Path(os.path.split(_cur_dir)[0])
_root_dir = Path(os.path.split(_prj_dir)[0])
sys.path.append(str(_root_dir))

from lib import log
from lib.pdf_parser import parse_pdf
from lib.count_tokens import get_gpt_token_count
from lib.json_processor import json_dump
from knowledge_base.core.grag import query_async, insert_async

temp_kg_original_file_dir = _root_dir / "temp_kb_files"
if not os.path.exists(temp_kg_original_file_dir):
    temp_kg_original_file_dir.mkdir(exist_ok=True)

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def _read_single_file(file_path: str, log_id=None) -> tuple[str, Any]:
    try:
        file_lower = file_path.lower()
        if not any(
            file_lower.endswith(ext)
            for ext in [".txt", ".pdf", ".doc", ".docx", ".md"]
        ):
            log.error(log_id, f"Unsupported file type: {file_path}")
            return "", 0

        content = ""
        if file_lower.endswith(".pdf"):
            content = parse_pdf(file_path, log_id=log_id)
        elif file_lower.endswith(".docx"):
            try:
                doc = docx.Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
            except Exception as docx_err:
                log.error(log_id, f"Error reading docx file {file_path}: {docx_err}")
                return "", 0
        elif file_lower.endswith((".txt", ".md")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError) as text_err:
                log.error(log_id, f"Error reading text file {file_path}: {text_err}")
                return "", 0
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError) as other_err:
                log.error(log_id, f"Error reading file {file_path}: {other_err}")
                return "", 0

        token = get_gpt_token_count(content)
        return content, token
    except Exception as e:
        print(log.get_trace_back())
        log.error(log_id, f"Error processing file: {file_path}: {e}")
        return "", 0


def _read_files_from_dir(dir_path: str) -> list[str]:
    """
    从指定目录读取文件内容
    :param dir_path: 文件目录路径
    :return: 文件内容列表

    根据不同的文件类型采用不同的策略
    """
    contents = []
    try:
        for file_name in os.listdir(dir_path):
            if not any(
                file_name.lower().endswith(ext)
                for ext in [".txt", ".pdf", ".doc", ".docx", "md"]
            ):
                continue
            file_path = os.path.join(dir_path, file_name)
            try:
                with open(file_path, "rb") as f:
                    content = f.read().decode("utf-8")
                    contents.append(content)
            except (IOError, UnicodeDecodeError) as e:
                print(f"Error reading file {file_path}: {str(e)}")
                continue
    except OSError as e:
        print(f"Error accessing directory {dir_path}: {str(e)}")
    return contents


@log.record(show_args_ids=[1, 2])
async def insert_data_2_graph(
    graph: GraphRAG,
    file_path: str | None = None,
    log_id: str | int | None = None,
):
    """
    构建图谱
    @param graph:
    @param file_path: 文件路径
    @param log_id:
    @return graph:
    """
    s_time = time.time()
    try:
        # 批量读取文件内所有内容
        content, token = _read_single_file(file_path, log_id=log_id)
        # 异步向graph中插入数据
        await insert_async(graph, content, log_id=log_id)
        log.log_time(log_id, f"Build graph rag successfully", s_time)
        return graph, token
    except Exception as e:
        log.error(log_id, f"Error building graph: {str(e)}")
        return None, 0
    finally:
        # 删除文件
        if file_path is not None:
            os.remove(file_path)


async def main(q, graph: GraphRAG, log_id=None):
    result = await query_async(graph, q, log_id=log_id)
    log.log(log_id, f"query: {test_q}\nresult: {json_dump(result, indent=2)}")


if __name__ == "__main__":
    from knowledge_base.core.manager import GraphManager

    test_kb_id = "1"
    test_q = "transformer的主要架构特点"
    graph = GraphManager(test_kb_id, log_id=log.uid()).load_graph()
    test_file_path = f"{temp_kg_original_file_dir}/{test_kb_id}/test.pdf"
    test_rag, token = asyncio.run(
        insert_data_2_graph(graph, test_file_path, log_id=log.uid())
    )
    test_resp = asyncio.run(main(test_q, test_rag, log_id=log.uid()))
