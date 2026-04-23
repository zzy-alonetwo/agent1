# 扫地机器人智能客服助手 🧹🤖

> 基于 LangChain ReAct Agent + RAG + Streamlit 构建的智能客服系统

---

## ⚡ 快速开始

### 安装依赖
```bash
pip install streamlit langchain langchain-core langchain-community langgraph \
            langchain-chroma chromadb dashscope pypdf pyyaml
```

### 配置高德地图 API Key
编辑 `config/agent.yml`，将 `gaodekey` 替换为你的高德地图 Web 服务 API Key。

### 启动应用
```bash
streamlit run app.py
```

---

## 📖 项目介绍

**扫地机器人智能客服助手**是一款面向扫地机器人用户的 AI 智能体应用。系统采用 Streamlit 构建交互式前端界面，后端基于 LangChain ReAct Agent 架构，具备以下核心能力：

- **智能知识库检索**：将产品手册、常见问题、维护指南等文档向量化存储，AI 回答时自动检索相关资料，确保信息准确可靠。
- **实时天气与定位**：集成高德地图 API，支持 IP 自动定位和实时天气查询。
- **个性化使用报告**：中间件根据用户意图动态切换提示词，自动生成 Markdown 格式的使用情况报告。
- **多轮工具调用**：Agent 能够自主规划并调用多个工具，直到满足用户需求。
- **流式响应输出**：答案以逐字流式方式呈现，提升用户交互体验。
- **完善的日志系统**：支持控制台和文件双输出，便于问题排查和行为追踪。

---

## ✨ 核心技术栈

| 组件 | 技术方案 |
|------|----------|
| **大语言模型** | 阿里云通义千问 `qwen3-max` |
| **向量嵌入** | 阿里云 DashScope `text-embedding-v4` |
| **向量数据库** | Chroma（本地持久化存储） |
| **Agent 框架** | LangChain ReAct Agent + LangGraph |
| **前端界面** | Streamlit（支持对话历史） |
| **地图服务** | 高德地图 REST API |
| **日志系统** | Python logging（按天分割） |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              Streamlit 前端界面                          │
│  ┌─────────────┬─────────────┬─────────────────────┐   │
│  │  对话历史   │  流式消息    │   会话状态管理      │   │
│  └─────────────┴─────────────┴─────────────────────┘   │
└───────────────────────┬───────────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────────┐
│                  ReAct Agent                          │
│  ┌─────────────────────────────────────────────────┐  │
│  │               中间件层                           │  │
│  │  ├─ monitor_tool        工具调用监控与记录       │  │
│  │  ├─ log_before_model    模型调用前日志记录       │  │
│  │  └─ report_prompt_switch 动态提示词切换         │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │                   工具集                        │  │
│  │  rag_summarize / get_weather / get_user_location │  │
│  │  get_user_id / get_current_month / fetch_external_data│  │
│  │  fill_context_for_report                        │  │
│  └─────────────────────────────────────────────────┘  │
└───────────┬───────────────────┬───────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────┐   ┌─────────────────────────┐
│   RAG 检索服务   │   │     外部数据源          │
│   (Chroma DB)   │   │ 高德API / CSV数据      │
└─────────────────┘   └─────────────────────────┘
```

---

## 📂 目录结构

```
Agent_Project/
├── app.py                    # Streamlit 应用入口
├── agent/
│   ├── react_agent.py        # ReAct Agent 核心逻辑
│   └── tools/
│       ├── agent_tools.py    # 工具函数定义
│       └── middleware.py     # Agent 中间件
├── rag/
│   ├── rag_service.py        # RAG 检索摘要服务
│   └── vector_store.py       # Chroma 向量库管理
├── model/
│   └── factory.py            # 模型工厂（LLM + Embedding）
├── utils/
│   ├── config_handler.py     # YAML 配置加载器
│   ├── logger_handler.py     # 日志工具
│   ├── prompt_loader.py      # 提示词加载器
│   ├── file_handler.py       # 文档加载（PDF/TXT）
│   └── path_tool.py          # 路径工具
├── config/
│   ├── agent.yml             # Agent 配置（高德 API Key 等）
│   ├── rag.yml               # 模型名称配置
│   ├── chroma.yml            # 向量库配置
│   └── prompts.yml           # 提示词文件路径
├── prompts/
│   ├── main_prompt.txt       # 主 ReAct 提示词
│   ├── rag_summarize.txt     # RAG 摘要提示词
│   └── report_prompt.txt     # 报告生成提示词
├── data/
│   ├── 扫地机器人100问.pdf
│   ├── 扫地机器人100问2.txt
│   ├── 扫拖一体机器人100问.txt
│   ├── 故障排除.txt
│   ├── 维护保养.txt
│   ├── 选购指南.txt
│   └── external/
│       └── records.csv       # 用户使用记录
├── chroma_db/                # Chroma 向量数据库
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

编辑 `config/chroma.yml`：
```yaml
collection_name: agent
persist_directory: chroma_db
k: 3
data_path: data
chunk_size: 200
chunk_overlap: 20
```

---

## 🚀 启动指南

### 开发环境

```bash
# 安装依赖
pip install streamlit langchain langchain-core langchain-community langgraph \
            langchain-chroma chromadb dashscope pypdf pyyaml

# 配置环境变量
export DASHSCOPE_API_KEY="your_key"

# 启动应用
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

## 🔄 中间件机制

系统包含三个核心中间件：

1. **monitor_tool**：监控工具调用，记录调用状态，检测报告生成意图
2. **log_before_model**：在模型调用前记录日志
3. **report_prompt_switch**：根据上下文动态切换提示词模板

---

## 📋 日志系统

日志文件按天存储在 `logs/` 目录：
```
logs/agent_20250101.log
```

日志级别：
- **控制台**：INFO 及以上
- **文件**：DEBUG 及以上

---

## 📚 知识库管理

知识库文档存放在 `data/` 目录，支持 `.txt` 和 `.pdf` 格式。系统首次启动时自动向量化文档，通过 MD5 哈希去重，避免重复入库。

---

## 🔮 未来计划

- 支持 Redis 向量数据库
- 完善高德 MCP 协议集成
- 添加用户认证系统
- 支持更多文档格式

---

## 📄 许可证

本项目仅供学习与参考使用。
感谢黑马程序员开源免费项目、阿里云和高德地图等开放平台。