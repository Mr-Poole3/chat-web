import os
import sys
import time
import asyncio
from typing import Any, Dict, List, Union, Optional
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from fast_graphrag import GraphRAG, QueryParam
from fast_graphrag._llm import OpenAILLMService, OpenAIEmbeddingService

_cur_dir = Path(os.path.split(os.path.abspath(__file__))[0])
_prj_dir = Path(os.path.split(_cur_dir)[0])
_root_dir = Path(os.path.split(_prj_dir)[0])
sys.path.append(str(_root_dir))

_cur_dir = Path(os.path.split(os.path.abspath(__file__))[0])
_prompt_dir = _prj_dir / "prompts"

from lib import log
from knowledge_base.config.conf import DOMAIN

with open(_prompt_dir / "domain_v0.txt", "rb") as f:
    P_DOMAIN = f.read().decode("utf-8")

ENTITY_TYPES = ["node"]
AZURE_CONFIG = {
    "client": "azure",
    "api_version": "2024-08-01-preview",
    "base_url": "https://euinstance.openai.azure.com/",
    "api_key": "4d6f722a1a6f47ac822c0f3c9dbcc844",
}


@log.record(show_return=False)
def load(
    dir_path: str,
    domain: str,
    entity_types: List[str],
    example_queries: List[str],
    log_id=None,
):
    s_time = time.time()
    if not dir_path and not os.path.isdir(dir_path):
        log.error(log_id, f"Error: invalid dir: {dir_path}")
        return

    if not example_queries or not isinstance(example_queries, list):
        log.error(log_id, f"Error: invalid exampl queries: {example_queries}")
        return

    try:
        grag = GraphRAG(
            working_dir=dir_path,
            domain=domain,
            example_queries="\n".join(example_queries),
            entity_types=entity_types,
            config=GraphRAG.Config(
                llm_service=OpenAILLMService(
                    model="gpt-4o-mini", **AZURE_CONFIG  # type: ignore
                ),
                embedding_service=OpenAIEmbeddingService(
                    **AZURE_CONFIG  # type: ignore
                ),
            ),
        )
        log.log_time(log_id, f"Load kb successfully", s_time)
        return grag

    except Exception as ex:
        print(log.get_trace_back())
        log.error(
            log_id, f"Error occurs during loading or creating graph in {dir_path}: {ex}"
        )
        return


@log.record(show_args_ids=[1, 2])
def insert(
    graph: GraphRAG,
    content: Union[str, List[str]],
    metadata: Union[List[Optional[Dict[str, Any]]], Optional[Dict[str, Any]]] = None,
    log_id=None,
):
    """
    同步往graph中插入数据
    @param graph:
    @param content:
    @param metadata:
    @param log_id:
    @return:
    """
    if not isinstance(content, str) and not isinstance(content, list):
        log.error(log_id, f"Error: invalid content type: {content}")
        return

    try:
        return graph.insert(content, metadata)
    except Exception as ex:
        print(log.get_trace_back())
        log.error(log_id, f"Error occurs during inserting graph: {ex}")
        return


@log.record(show_args_ids=[1, 2, 3, 4, 5, 6])
def query(
    graph: GraphRAG,
    q: str,
    with_references: bool = False,
    only_context: bool = True,
    entities_max_tokens: int = 2000,
    relationships_max_tokens: int = 2000,
    chunks_max_tokens: int = 3200,
    log_id=None,
):
    try:
        params = QueryParam(
            with_references=with_references,
            only_context=only_context,
            entities_max_tokens=entities_max_tokens,
            relations_max_tokens=relationships_max_tokens,
            chunks_max_tokens=chunks_max_tokens,
        )
        return graph.query(q, params)

    except Exception as ex:
        print(log.get_trace_back())
        log.error(log_id, f"Error occurs during graph query: {query} : {ex}")
        return


async def insert_async(
    graph: GraphRAG,
    content: Union[str, List[str]],
    metadata: Union[List[Optional[Dict[str, Any]]], Optional[Dict[str, Any]]] = None,
    log_id=None,
):
    """
    异步往graph中插入数据
    @param graph:
    @param content:
    @param metadata:
    @param log_id:
    @return:
    """
    s_time = time.time()
    if not isinstance(content, str) and not isinstance(content, list):
        log.error(log_id, f"Error: invalid content type: {content}")
        return

    try:
        ret = await graph.async_insert(content, metadata)
        log.log_time(log_id, f"finish inserting content: {ret}", s_time)
        return ret
    except Exception as ex:
        print(log.get_trace_back())
        log.error(log_id, f"Error occurs during inserting graph: {ex}")
        return


async def query_async(
    graph: GraphRAG,
    q: str,
    with_references: bool = False,
    only_context: bool = True,
    entities_max_tokens: int = 2000,
    relationships_max_tokens: int = 2000,
    chunks_max_tokens: int = 3200,
    log_id=None,
):
    """
    异步查询graph
    @param graph:
    @param q:
    @param with_references:
    @param only_context:
    @param entities_max_tokens:
    @param relationships_max_tokens:
    @param chunks_max_tokens:
    @param log_id:
    @return:
    """
    s_time = time.time()

    try:
        await graph.state_manager.query_start()

        params = QueryParam(
            with_references=with_references,
            only_context=only_context,
            entities_max_tokens=entities_max_tokens,
            relations_max_tokens=relationships_max_tokens,
            chunks_max_tokens=chunks_max_tokens,
        )

        answer = await graph.async_query(q, params)

        log.log_time(log_id, f"Finish querying graphRAG", s_time)
        return answer

    except Exception as ex:
        print(log.get_trace_back())
        log.error(log_id, f"Error occurs during graph query: {q} : {ex}")
        return
    finally:
        await graph.state_manager.query_done()


if __name__ == "__main__":
    log.PRINT = True
    log.PROJECT = "Test_Graph"

    _prj_dir = os.path.split(_cur_dir)[0]
    _root_dir = Path(os.path.split(_prj_dir)[0])
    _cache_dir = _root_dir / "cache_graph" / "1"

    test_example_queries = [
        "How to upload CSV?",
    ]
    test_graph = load(
        str(_cache_dir),
        example_queries=test_example_queries,
        domain=DOMAIN,
        entity_types=ENTITY_TYPES,
    )
    print("graph load success")
    kb_contents = ["I am a helpful assistant"]
    asyncio.run(insert_async(test_graph, kb_contents, log_id=log.uid()))
    print("insert content into graph successfully")
    test_query = "who am i"
    test_answer = query(test_graph, q=test_query, only_context=True)
