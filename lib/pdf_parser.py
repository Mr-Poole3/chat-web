from typing import Union

import fitz

from lib import log


@log.record(show_return=False)
def parse_pdf(
    file_path: Union[str, bytes], batch_size: int = 5, log_id: str | int | None = None
):
    """
    解析PDF文件或字节流
    @param file_path: 本地文件路径或PDF字节流
    @param batch_size: 每批次处理的页数
    @param log_id:
    @return: 提取的文本内容
    """
    try:
        # 根据输入类型打开PDF文件
        if isinstance(file_path, str):
            # 打开本地文件
            pdf_document = fitz.open(file_path)
        else:
            # 打开字节流
            pdf_document = fitz.open(stream=file_path, filetype="pdf")

        # 获取PDF的总页数
        total_pages = pdf_document.page_count

        # 初始化一个空的列表，用于存储每一批次的文本内容
        batches = []

        # 按批次提取文本内容
        for start_page in range(0, total_pages, batch_size):
            # 初始化一个空的字符串变量，用于存储当前批次的文本
            batch_text = ""

            # 计算当前批次的结束页码
            end_page = min(start_page + batch_size, total_pages)

            # 遍历当前批次的每一页
            for page_num in range(start_page, end_page):
                # 获取每一页对象
                page = pdf_document.load_page(page_num)
                if not page or not page.get_textpage():
                    continue

                # 提取每一页的文本内容
                batch_text += page.get_textpage().extractText()

            # 将当前批次的文本内容添加到列表中
            batches.append(batch_text)

        # 关闭PDF文件
        pdf_document.close()

        return "\n".join(batches)

    except Exception as e:
        log.error(log_id, f"PDF解析失败: {str(e)}")
        print(log.get_trace_back())
        return ""


if __name__ == "__main__":
    log.PRINT = True
    test_path = "/Users/chentanyu/Downloads/Transformer.pdf"
    print(parse_pdf(test_path, log_id=log.uid()))
    log.stop()
