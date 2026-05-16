import os
import json
import hashlib
from typing import Optional, List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
)
from utils.logger_handler import logger


def get_file_md5_hex(filepath: str):
    if not os.path.exists(filepath):
        logger.error(f"[md5计算]文件{filepath}不存在")
        return None
    if not os.path.isfile(filepath):
        logger.error(f"[md5计算]路径{filepath}不是文件")
        return None

    md5_object = hashlib.md5()
    chunk_size = 4096
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_object.update(chunk)
            return md5_object.hexdigest()
    except Exception as e:
        logger.error(f"计算文件{filepath}md5失败,{str(e)}")
        return None


def listidr_with_allowed_type(path: str, allowed_type):
    files = []
    if not os.path.isdir(path):
        logger.error(f"[listidr_with_allowed_type]{path}不是文件夹")
        return []

    if isinstance(allowed_type, list):
        allowed_type = tuple(allowed_type)

    for f in os.listdir(path):
        if f.endswith(allowed_type):
            files.append(os.path.join(path, f))
    return files


def pdf_loader(filepath: str, password=None) -> list[Document]:
    return PyPDFLoader(filepath, password=password).load()


def txt_loader(filepath: str, encoding="utf-8") -> list[Document]:
    return TextLoader(filepath, encoding=encoding).load()