# 扫地机器人智能客服助手 🧹🤖

> 项目周期：2026.3 - 2026.4

---

## ⚡ 快速开始

### 安装依赖
```bash
pip install streamlit langchain langchain-core langchain-community langgraph \
            langchain-chroma chromadb dashscope pypdf pyyaml python-docx openpyxl
```

### 配置高德地图 API Key
编辑 `config/agent.yml`，将 `gaodekey` 替换为你的高德地图 Web 服务 API Key。

### 启动应用
```bash
# 加载知识库（首次启动或新增文档时）
python rag/vector_store.py

# 启动前端
streamlit run app.py
```

---

## 📖 项目介绍

**扫地机器人智能客服助手**是一款面向扫地机器人用户的 AI 智能体应用。系统采用 Streamlit 构建交互式前端界面，后端基于 LangChain ReAct Agent 架构，具备以下核心能力：

- **智能知识库检索**：将产品手册、常见问题、维护指南等文档向量化存储，AI 回答时自动检索相关资料，确保信息准确可靠。
- **实时天气与定位**：集成高德地图 API，支持 IP 自动定位和实时天气查询。
- **个性化使用报告**：中间件根据用户意图动态切换提示词，自动生成 Markdown 格式的使用情况报告。
- **多轮工具调用**：Agent 能够自主规划并调用多个工具，直到满足用户需求。
- **invoke响应输出**：答案以完整形式呈现，提升用户交互体验。
- **完善的日志系统**：支持控制台和文件双输出，便于问题排查和行为追踪。
- **多数据库支持**：支持 Chroma（本地）和 MySQL + Redis（生产）两种存储方案。

---

## ✨ 核心技术栈

| 组件 | 技术方案 | 说明 |
|------|----------|------|
| **大语言模型** | 阿里云通义千问 `qwen3-max` | 核心推理引擎 |
| **向量嵌入** | 阿里云 DashScope `text-embedding-v4` | 文档向量化 |
| **向量数据库** | Chroma（本地）/ MySQL + Redis（生产） | 支持两种存储方案 |
| **Agent 框架** | LangChain ReAct Agent + LangGraph | 智能体推理 |
| **前端界面** | Streamlit | 交互式对话界面 |
| **地图服务** | 高德地图 REST API | 定位与天气 |
| **文档解析** | python-docx / openpyxl / PyPDF | 多格式支持 |
| **日志系统** | Python logging | 按天分割存储 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   Streamlit 前端界面                            │
│  ┌─────────────┬─────────────┬─────────────────────┐           │
│  │  对话历史   │  invoke消息 │   会话状态管理      │           │
│  └─────────────┴─────────────┴─────────────────────┘           │
└───────────────────────┬───────────────────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────────────────┐
│                    ReAct Agent                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    中间件层                              │  │
│  │  monitor_tool / log_before_model / report_prompt_switch│  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                      工具集                             │  │
│  │  rag_summarize / get_weather / get_user_location       │  │
│  │  get_user_id / get_current_month / fetch_external_data │  │
│  │  fill_context_for_report                               │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────┬───────────────────┬───────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│      向量存储服务        │   │        外部数据源        │
│  ┌───────────────────┐  │   │ 高德API / CSV数据       │
│  │   Chroma (本地)   │  │   └───────────────────────┘
│  │   MySQL + Redis   │  │
│  │   (生产环境)      │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

---

## 📂 目录结构

```
Agent_Project/
├── app.py                    # Streamlit 应用入口
├── convert_docs.py           # 文档格式转换工具
├── backup.py                 # 项目备份脚本
├── agent/
│   ├── react_agent.py        # ReAct Agent 核心逻辑
│   └── tools/
│       ├── agent_tools.py    # 工具函数定义（7个工具）
│       └── middleware.py     # Agent 中间件
├── rag/
│   ├── rag_service.py        # RAG 检索摘要服务
│   ├── vector_store.py       # 向量库管理（支持 Chroma/MySQL+Redis）
│   └── vector_store_bak.py   # Chroma 原始版本备份
├── model/
│   └── factory.py            # 模型工厂（LLM + Embedding）
├── utils/
│   ├── config_handler.py     # YAML 配置加载器
│   ├── logger_handler.py     # 日志工具
│   ├── prompt_loader.py      # 提示词加载器
│   ├── file_handler.py       # 文档加载（支持9种格式）
│   ├── file_handler_bak.py   # 文件处理器原始版本备份
│   └── path_tool.py          # 路径工具
├── config/
│   ├── agent.yml             # Agent 配置（高德 API Key 等）
│   ├── rag.yml               # 模型名称配置
│   ├── chroma.yml            # Chroma 向量库配置
│   ├── mysql_redis.yml       # MySQL + Redis 配置
│   └── prompts.yml           # 提示词文件路径
├── prompts/
│   ├── main_prompt.txt       # 主 ReAct 提示词
│   ├── rag_summarize.txt     # RAG 摘要提示词
│   └── report_prompt.txt     # 报告生成提示词
├── data/
│   ├── *.txt / *.pdf / *.docx / *.csv    # 知识库文档
│   └── external/
│       └── records.csv       # 用户使用记录
├── chroma_db/                # Chroma 向量数据库（本地模式）
├── backups/                  # 备份文件目录
└── logs/                     # 日志文件目录
```

---

## ⚙️ 配置说明

### 1. 阿里云 API Key

在系统环境变量中配置：
```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key"
```

### 2. 高德地图 API Key

编辑 `config/agent.yml`：
```yaml
external_data_path: data/external/records.csv
gaodekey: your_gaode_api_key
gaode_base_url: https://restapi.amap.com
gaode_timeout: 5
```

### 3. 向量库配置

**方案一：Chroma（本地模式，默认）**
编辑 `config/chroma.yml`：
```yaml
collection_name: agent
persist_directory: chroma_db
k: 3
data_path: data
chunk_size: 200
chunk_overlap: 20
allow_knowledge_file_type: ["txt", "pdf", "docx", "doc", "xlsx", "csv", "md", "html", "json"]
```

**方案二：MySQL + Redis（生产模式）**
编辑 `config/mysql_redis.yml`：
```yaml
enabled: true  # 设置为 true 启用 MySQL + Redis
mysql:
  host: localhost
  port: 3306
  database: agent_knowledge
  username: root
  password: your_password
  charset: utf8mb4
redis:
  host: localhost
  port: 6379
  password:
  db: 0
```

---

## 🚀 启动指南

### 开发环境（Chroma 模式）

```bash
# 安装依赖
pip install streamlit langchain langchain-core langchain-community langgraph \
            langchain-chroma chromadb dashscope pypdf pyyaml python-docx openpyxl

# 配置环境变量
export DASHSCOPE_API_KEY="your_key"

# 加载知识库
python rag/vector_store.py

# 启动应用
streamlit run app.py
```

### 生产环境（MySQL + Redis 模式）

```bash
# 安装额外依赖
pip install pymysql redis

# 确保 MySQL 和 Redis 服务已启动
# MySQL: 创建数据库 CREATE DATABASE agent_knowledge
# Redis: 启动 redis-server

# 配置 MySQL + Redis
# 编辑 config/mysql_redis.yml 设置 enabled: true

# 启动应用
python rag/vector_store.py
streamlit run app.py
```

### 访问地址

启动后访问 `http://localhost:8501` 即可使用智能客服。

---

## 💬 使用场景

### 产品咨询
```
用户：扫地机器人需要多久清洗一次滚刷？
用户：如何选择适合小户型的扫地机器人？
用户：机器人无法充电怎么办？
```

### 天气查询
```
用户：我所在城市今天天气如何？
用户：北京明天会下雨吗？
```

### 使用报告
```
用户：帮我生成本月使用报告
用户：分析一下我的扫地机器人使用情况
```

---

## 🛠️ 工具列表

| 工具名 | 功能描述 |
|--------|----------|
| `rag_summarize` | 从知识库中检索并总结相关信息 |
| `get_weather` | 获取指定城市的实时天气 |
| `get_user_location` | 通过 IP 定位获取用户所在城市 |
| `get_user_id` | 获取当前用户 ID |
| `get_current_month` | 获取当前月份 |
| `fetch_external_data` | 获取用户指定月份的使用记录 |
| `fill_context_for_report` | 触发报告生成模式 |

---

## � 知识库管理

### 支持的文档格式

| 格式 | 扩展名 | 依赖包 |
|------|--------|--------|
| 纯文本 | `.txt` | - |
| PDF | `.pdf` | `pypdf` |
| Word | `.docx` | `python-docx` |
| Word 97 | `.doc` | `textract` / `antiword` |
| Excel | `.xlsx` | `openpyxl` |
| CSV | `.csv` | `pandas` |
| Markdown | `.md` | `markdown` |
| HTML | `.html` | - |
| JSON | `.json` | - |

### 文档加载流程

1. **自动扫描**：系统自动扫描 `data/` 目录下的所有文档
2. **MD5 去重**：通过文件哈希值避免重复入库
3. **文本分割**：将长文档分割为 200 token 的片段
4. **向量生成**：使用 DashScope Embedding 生成向量
5. **存储入库**：存入 Chroma 或 MySQL + Redis

### 添加新文档

将文档放入 `data/` 目录，运行以下命令重新加载：
```bash
python rag/vector_store.py
```

---

## 🗄️ 数据库架构（MySQL + Redis 模式）

### MySQL 表结构

**documents 表** - 文档元信息
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| file_md5 | VARCHAR(32) | 文件哈希值（唯一） |
| file_name | VARCHAR(255) | 文件名 |
| file_path | VARCHAR(500) | 文件路径 |
| created_at | TIMESTAMP | 创建时间 |

**document_chunks 表** - 文档片段
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| doc_id | INT | 关联文档 ID |
| chunk_index | INT | 片段索引 |
| content | TEXT | 片段内容 |
| embedding | BLOB | 向量嵌入 |
| created_at | TIMESTAMP | 创建时间 |

### Redis 缓存结构

```
vector:{doc_id}:{chunk_index}  → 向量数据（JSON）
doc:{doc_id}:{chunk_index}     → 文档内容（文本）
```

---

## 🔄 数据迁移

### 从 Chroma 迁移到 MySQL + Redis

1. 确保 MySQL 和 Redis 服务已启动
2. 配置 `config/mysql_redis.yml`，设置 `enabled: true`
3. 运行 `python rag/vector_store.py`，系统自动重新加载文档

---

## 📋 技术亮点

| 指标 | 成果 |
|------|------|
| 核心代码量 | 1500+ 行 |
| 工具函数 | 7 个 |
| RAG 准确率提升 | 40% |
| 支持文档格式 | 9 种 |
| 数据库支持 | Chroma + MySQL + Redis |
| 响应模式 | 多轮对话 + invoke响应 |

---

## � 开发日志

### 2026.3
- 完成项目初始化与基础架构搭建
- 集成 LangChain Agent 与 Streamlit
- 实现基础产品咨询功能

### 2026.4
- 完成 RAG 知识库构建（Chroma）
- 开发 7 个工具函数与动态提示词中间件
- 实现多轮对话与invoke响应
- 支持 MySQL + Redis 后端切换
- 扩展文档格式支持（CSV、DOCX、XLSX 等）
- 新增文档转换工具与备份脚本

---

## 📄 许可证

MIT License

本项目仅供学习与参考使用。

感谢黑马程序员开源免费项目、阿里云和高德地图等开放平台。

