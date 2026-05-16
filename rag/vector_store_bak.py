import os
from langchain_chroma import Chroma
from langchain_core.documents import Document

from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.file_handler import get_file_md5_hex, listidr_with_allowed_type, pdf_loader, txt_loader
from utils.path_tool import get_abs_path1
from utils.logger_handler import logger


class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path1(chroma_conf["persist_directory"]),
        )
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def load_document(self):
        """
        从数据文件夹内读取数据文件，并转入向量数据库
        要计算文件的md5去重
        支持格式: txt, pdf
        :return: None
        """

        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path1(chroma_conf["md5_hex_store"])):
                open(get_abs_path1(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False
            with open(get_abs_path1(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True
                return False

        def save_md5_hex(md5_for_check: str):
            with open(get_abs_path1(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check + '\n')

        def get_file_documents(read_path: str):
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)
            elif read_path.endswith("txt"):
                return txt_loader(read_path)
            else:
                logger.warning(f"[get_file_documents]不支持的文件格式: {read_path}")
                return []

        allow_files_path = listidr_with_allowed_type(
            get_abs_path1(chroma_conf["data_path"]),
            allowed_type=chroma_conf["allow_knowledge_file_type"],
        )

        for path in allow_files_path:
            md5_hex = get_file_md5_hex(path)

            if not md5_hex:
                logger.error(f"[加载知识库]{path}无法计算MD5，跳过")
                continue

            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}已经存入知识库中，跳过")
                continue
            try:
                documents = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue
                split_documents = self.spliter.split_documents(documents)

                if not split_documents:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue
                self.vector_store.add_documents(split_documents)

                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库]{path}内容加载成功")
            except Exception as e:
                logger.error(f"[加载知识库]{path},加载失败,{str(e)}", exc_info=True)


if __name__ == '__main__':
    vs = VectorStoreService()
    vs.load_document()
    retriever = vs.get_retriever()
    res = retriever.invoke("迷路")
    for chunk in res:
        print(chunk.page_content)
        print("-" * 20)