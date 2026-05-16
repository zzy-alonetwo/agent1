import os
import hashlib
import json , pymysql ,redis
from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.file_handler import get_file_md5_hex, listidr_with_allowed_type, get_file_loader
from utils.path_tool import get_abs_path1
from utils.logger_handler import logger

# ==============================================================================
# MySQL + Redis 配置和实现（当前启用）
# ==============================================================================
from utils.config_handler import chroma_conf
# 加载 MySQL + Redis 配置
try:
    import yaml
    with open(get_abs_path1("config/mysql_redis.yml"), "r", encoding="utf-8") as f:
        mysql_redis_conf = yaml.load(f, Loader=yaml.FullLoader)
    USE_MYSQL_REDIS = mysql_redis_conf.get("enabled", False)
except Exception as e:
    logger.warning(f"加载 MySQL + Redis 配置失败，使用 Chroma: {str(e)}")
    USE_MYSQL_REDIS = False

# MySQL 和 Redis 连接（延迟初始化）
mysql_conn = None
redis_conn = None

def init_mysql_connection():
    """初始化 MySQL 连接"""
    global mysql_conn
    if mysql_conn:
        return mysql_conn
    
    try:
        import pymysql
        conf = mysql_redis_conf["mysql"]
        mysql_conn = pymysql.connect(
            host=conf["host"],
            port=conf["port"],
            user=conf["username"],
            password=conf["password"],
            database=conf["database"],
            charset=conf["charset"],
            cursorclass=pymysql.cursors.DictCursor
        )
        # 创建必要的表
        create_tables()
        logger.info("✅ MySQL 连接初始化成功")
        return mysql_conn
    except ImportError:
        logger.error("❌ pymysql 未安装，请安装: pip install pymysql")
        raise
    except Exception as e:
        logger.error(f"❌ MySQL 连接失败: {str(e)}")
        raise

def init_redis_connection():
    """初始化 Redis 连接"""
    global redis_conn
    if redis_conn:
        return redis_conn
    
    try:
        import redis
        conf = mysql_redis_conf["redis"]
        redis_conn = redis.Redis(
            host=conf["host"],
            port=conf["port"],
            password=conf.get("password"),
            db=conf["db"],
            decode_responses=True
        )
        # 测试连接
        redis_conn.ping()
        logger.info("✅ Redis 连接初始化成功")
        return redis_conn
    except ImportError:
        logger.error("❌ redis 未安装，请安装: pip install redis")
        raise
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {str(e)}")
        raise

def create_tables():
    """创建 MySQL 表"""
    try:
        cursor = mysql_conn.cursor()
        
        # 创建文档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                file_md5 VARCHAR(32) UNIQUE NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_file_md5 (file_md5)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        # 创建文档片段表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                doc_id INT NOT NULL,
                chunk_index INT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_doc_id (doc_id),
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        mysql_conn.commit()
        cursor.close()
        logger.info("✅ MySQL 表创建成功")
    except Exception as e:
        logger.error(f"❌ 创建 MySQL 表失败: {str(e)}")

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度，公式没问题，但数据类型有点问题
    """
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = (sum(a * a for a in vec1)) ** 0.5
    norm2 = (sum(b * b for b in vec2)) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

# ==============================================================================
# VectorStoreService（MySQL + Redis 版本）
# ==============================================================================
class VectorStoreService:
    def __init__(self):
        # 初始化文本分割器
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )
        
        # 初始化模型
        from model.factory import embed_model
        self.embed_model = embed_model
        
        # 初始化数据库连接
        if USE_MYSQL_REDIS:
            self.mysql_conn = init_mysql_connection()
            self.redis_conn = init_redis_connection()
            self.vector_prefix = mysql_redis_conf["redis"].get("vector_prefix", "vector:")
            self.doc_prefix = mysql_redis_conf["redis"].get("doc_prefix", "doc:")
            logger.info("🔄 使用 MySQL + Redis 作为向量存储后端")
        else:
            # 回退到 Chroma
            self._init_chroma()
            logger.info("🔄 使用 Chroma 作为向量存储后端")
    
    def _init_chroma(self):
        """初始化 Chroma（备用方案）"""
        from langchain_chroma import Chroma
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=self.embed_model,
            persist_directory=get_abs_path1(chroma_conf["persist_directory"]),
        )
    
    def get_retriever(self):
        if USE_MYSQL_REDIS:
            return MySQLRedisRetriever(self)
        else:
            return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})
    
    def check_md5_exists(self, md5_hex: str) -> bool:
        """检查 MD5 是否已存在"""
        if USE_MYSQL_REDIS:
            try:
                cursor = self.mysql_conn.cursor()
                cursor.execute("SELECT id FROM documents WHERE file_md5 = %s", (md5_hex,))
                result = cursor.fetchone()
                cursor.close()
                return result is not None
            except Exception as e:
                logger.error(f"❌ 检查 MD5 失败: {str(e)}")
                return False
        else:
            # Chroma 版本（文件存储）
            md5_store_path = get_abs_path1(chroma_conf["md5_hex_store"])
            if not os.path.exists(md5_store_path):
                return False
            with open(md5_store_path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.strip() == md5_hex:
                        return True
            return False
    
    def save_md5(self, md5_hex: str):
        """保存 MD5"""
        if USE_MYSQL_REDIS:
            # MySQL 版本不需要额外保存 MD5，已在 documents 表中
            pass
        else:
            # Chroma 版本（文件存储）
            md5_store_path = get_abs_path1(chroma_conf["md5_hex_store"])
            with open(md5_store_path, "a", encoding="utf-8") as f:
                f.write(md5_hex + '\n')
    
    def add_documents(self, documents: List[Document], file_md5: str, file_name: str, file_path: str):
        """添加文档到向量存储"""
        if USE_MYSQL_REDIS:
            try:
                logger.info(f"[add_documents] 开始处理文档: {file_name}")
                cursor = self.mysql_conn.cursor()
                
                # 插入文档记录
                logger.info(f"[add_documents] 插入文档记录到 MySQL...")
                cursor.execute(
                    "INSERT INTO documents (file_md5, file_name, file_path) VALUES (%s, %s, %s)",
                    (file_md5, file_name, file_path)
                )
                doc_id = cursor.lastrowid
                logger.info(f"[add_documents] 文档ID: {doc_id}")
                
                # 分割文档
                logger.info(f"[add_documents] 分割文档...")
                split_docs = self.spliter.split_documents(documents)
                logger.info(f"[add_documents] 分割成 {len(split_docs)} 个片段")
                
                # 插入文档片段
                logger.info(f"[add_documents] 插入文档片段...")
                for idx, chunk in enumerate(split_docs):
                    # 生成向量
                    logger.info(f"[add_documents] 生成向量 {idx+1}/{len(split_docs)}...")
                    embedding = self.embed_model.embed_query(chunk.page_content)
                    embedding_bytes = json.dumps(embedding).encode('utf-8')
                    
                    logger.info(f"[add_documents] 插入到 MySQL...")
                    cursor.execute(
                        "INSERT INTO document_chunks (doc_id, chunk_index, content, embedding) VALUES (%s, %s, %s, %s)",
                        (doc_id, idx, chunk.page_content, embedding_bytes)
                    )
                    
                    # 同时存入 Redis 缓存
                    logger.info(f"[add_documents] 存入 Redis...")
                    vector_key = f"{self.vector_prefix}{doc_id}:{idx}"
                    doc_key = f"{self.doc_prefix}{doc_id}:{idx}"
                    self.redis_conn.set(vector_key, json.dumps(embedding))
                    self.redis_conn.set(doc_key, chunk.page_content)
                
                logger.info(f"[add_documents] 提交事务...")
                self.mysql_conn.commit()
                cursor.close()
                logger.info(f"✅ 文档 {file_name} 已存入 MySQL + Redis")
                return True
            except Exception as e:
                logger.error(f"❌ 添加文档失败: {str(e)}")
                self.mysql_conn.rollback()
                return False
        else:
            # Chroma 版本
            split_docs = self.spliter.split_documents(documents)
            self.vector_store.add_documents(split_docs)
            self.save_md5(file_md5)
            return True
    
    def load_document(self):
        """
        从数据文件夹内读取数据文件，并转入向量数据库
        支持格式: txt, pdf, csv
        """
        logger.info("[load_document] 开始加载知识库...")
        
        config = mysql_redis_conf if USE_MYSQL_REDIS else chroma_conf
        
        logger.info(f"[load_document] 数据路径: {config['data_path']}")
        logger.info(f"[load_document] 允许的文件类型: {config['allow_knowledge_file_type']}")
        
        allow_files_path = listidr_with_allowed_type(
            get_abs_path1(config["data_path"]),
            allowed_type=config["allow_knowledge_file_type"],
        )
        
        logger.info(f"[load_document] 找到 {len(allow_files_path)} 个文件")
        
        for idx, path in enumerate(allow_files_path):
            logger.info(f"[load_document] 处理文件 {idx+1}/{len(allow_files_path)}: {path}")
            
            # 计算 MD5
            logger.info(f"[load_document] 计算 MD5...")
            md5_hex = get_file_md5_hex(path)
            
            if not md5_hex:
                logger.error(f"[加载知识库]{path}无法计算MD5，跳过")
                continue
            
            # 检查是否已存在
            logger.info(f"[load_document] 检查 MD5 是否已存在...")
            if self.check_md5_exists(md5_hex):
                logger.info(f"[加载知识库]{path}已经存入知识库中，跳过")
                continue
            
            try:
                # 获取文件加载器
                logger.info(f"[load_document] 获取文件加载器...")
                loader = get_file_loader(path)
                if loader is None:
                    logger.warning(f"[加载知识库]{path}不支持的文件格式，跳过")
                    continue
                
                # 加载文件
                logger.info(f"[load_document] 加载文件内容...")
                documents = loader(path)
                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue
                
                # 添加到数据库
                logger.info(f"[load_document] 添加到数据库...")
                file_name = os.path.basename(path)
                self.add_documents(documents, md5_hex, file_name, path)
                logger.info(f"[加载知识库]{path}内容加载成功")
                
            except Exception as e:
                logger.error(f"[加载知识库]{path},加载失败,{str(e)}", exc_info=True)
        
        logger.info("[load_document] 加载知识库完成！")

# ==============================================================================
# MySQL + Redis 检索器
# ==============================================================================
class MySQLRedisRetriever:
    def __init__(self, service: VectorStoreService):
        self.service = service
        self.k = chroma_conf["k"]
    
    def invoke(self, query: str) -> List[Document]:
        """检索相似文档"""
        try:
            # 生成查询向量
            query_embedding = self.service.embed_model.embed_query(query)
            
            # 先尝试从 Redis 获取所有向量
            redis_conn = self.service.redis_conn
            vector_keys = redis_conn.keys(f"{self.service.vector_prefix}*")
            
            results = []
            
            if vector_keys:
                # 从 Redis 检索
                for key in vector_keys:
                    embedding_str = redis_conn.get(key)
                    if embedding_str:
                        embedding = json.loads(embedding_str)
                        similarity = cosine_similarity(query_embedding, embedding)
                        doc_key = key.replace(self.service.vector_prefix, self.service.doc_prefix)
                        content = redis_conn.get(doc_key)
                        if content:
                            results.append({
                                "similarity": similarity,
                                "content": content,
                                "key": key
                            })
            else:
                # 从 MySQL 检索
                cursor = self.service.mysql_conn.cursor()
                cursor.execute("SELECT id, chunk_index, content, embedding FROM document_chunks")
                rows = cursor.fetchall()
                cursor.close()
                
                for row in rows:
                    embedding = json.loads(row["embedding"].decode('utf-8'))
                    similarity = cosine_similarity(query_embedding, embedding)
                    results.append({
                        "similarity": similarity,
                        "content": row["content"],
                        "key": f"{row['id']}:{row['chunk_index']}"
                    })
            
            # 按相似度排序并取前 k 个
            results.sort(key=lambda x: x["similarity"], reverse=True)
            top_results = results[:self.k]
            
            # 转换为 Document 对象
            documents = []
            for res in top_results:
                documents.append(Document(
                    page_content=res["content"],
                    metadata={"source": res["key"], "similarity": res["similarity"]}
                ))
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ 检索失败: {str(e)}")
            return []

# ==============================================================================
# 以下是原始的 Chroma 实现（已注释）
# ==============================================================================
"""
# ===== 原始 Chroma 实现（已注释）=====
import os
from langchain_chroma import Chroma
from langchain_core.documents import Document

from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.file_handler import get_file_md5_hex, listidr_with_allowed_type, get_file_loader
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
        # 从数据文件夹内读取数据文件，并转入向量数据库
        # 要计算文件的md5去重
        # 支持格式: txt, pdf, docx, doc, xlsx, csv, md, html, json
        #:return: None
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
            loader = get_file_loader(read_path)
            if loader is None:
                logger.warning(f"[get_file_documents]不支持的文件格式: {read_path}")
                return []
            return loader(read_path)

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
"""

if __name__ == '__main__':
    vs = VectorStoreService()
    vs.load_document()
    retriever = vs.get_retriever()
    res = retriever.invoke("迷路")
    for chunk in res:
        print(chunk.page_content)
        print("-" * 20)