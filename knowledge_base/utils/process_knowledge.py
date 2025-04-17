def process_graph_context(context: dict, top_k: int = 10, max_tokens: int = 5000):
    """
    处理grag的返回值传入prompt
    @param context:
    @param top_k
    @param max_tokens
    @return:
    """

    def calculate_word_count(text_list):
        """计算文本列表的token数量"""
        return sum(len(text.split()) for text in text_list)

    # 使用集合去重
    seen_entities = set()
    seen_relations = set()
    seen_chunks = set()
    
    # 处理实体
    entity_texts = []
    for entity in context.get("entities", [])[: top_k * 2]:
        if (
            isinstance(entity, list)
            and entity
            and isinstance(entity[0], dict)
            and entity[0].get("type") == "NODE"
        ):
            name = entity[0].get("name", "")
            description = entity[0].get("description", "")
            if name and description:
                entity_text = f"[{name}] {description}"
                if entity_text not in seen_entities:
                    seen_entities.add(entity_text)
                    entity_texts.append(entity_text)

    # 处理关系
    relation_texts = []
    for relation_info in context.get("relationships", [])[:top_k]:
        if isinstance(relation_info, list) and relation_info:
            rel = relation_info[0]
            source = rel.get("source", "")
            target = rel.get("target", "")
            description = rel.get("description", "")
            if source and target and description:
                relation_text = f"[{source}]->[{target}]: {description}"
                if relation_text not in seen_relations:
                    seen_relations.add(relation_text)
                    relation_texts.append(relation_text)

    # 处理文本块
    chunk_texts = []
    for chunk in context.get("chunks", []):
        if isinstance(chunk, list) and chunk:
            content = chunk[0].get("content", "")
            if content and content not in seen_chunks:
                seen_chunks.add(content)
                chunk_texts.append(content)

    # 计算动态chunk数量
    current_tokens = calculate_word_count(entity_texts + relation_texts)
    remaining_tokens = max_tokens - current_tokens
    for chunk in chunk_texts:
        chunk_tokens = len(chunk.split())
        if remaining_tokens >= chunk_tokens:
            chunk_texts.append(chunk)
            remaining_tokens -= chunk_tokens
        else:
            break

    # 组装最终格式
    result = []
    if entity_texts:
        result.append("# Entities")
        result.extend([f"ENTITY: {text}" for text in entity_texts])
        result.append("")

    if relation_texts:
        result.append("# Relationships")
        result.extend([f"RELATION: {text}" for text in relation_texts])
        result.append("")

    if chunk_texts:
        result.append("# Context")
        result.extend([f"CONTEXT: {text}" for text in chunk_texts])
        result.append("")

    return "\n".join(result)
