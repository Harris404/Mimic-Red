# RAG向量库构建方案

## 当前项目状态
项目已经完成了RAG数据准备的**前置工作**：
- ✅ 数据采集：笔记和评论已存储在 SQLite (`datas/notes.db`)
- ✅ 数据清洗：`rag_util.py` 提供字段精简和评论聚合
- ✅ 数据导出：`note_manager.py` 支持导出为 JSONL 格式（`export_to_jsonl`）

**缺失部分**：
- ❌ 向量化（Embedding）模块
- ❌ 向量数据库集成（如 Chroma/Faiss/Pinecone）
- ❌ 检索接口

---

## 完整RAG构建流程

### 步骤1：从数据库导出RAG数据
使用现有的 `run.py --export-rag` 命令：
```bash
python run.py --export-rag
```

这会生成：
- `datas/excel_datas/rag_documents/notes_rag_{timestamp}.jsonl` - 笔记数据
- `datas/excel_datas/rag_documents/comments_only_{timestamp}.jsonl` - 评论数据

每行格式示例：
```json
{
  "id": "note_12345",
  "text": "标题: 悉尼租房攻略\n\n内容: 分享我在悉尼租房的经验...\n\n标签: 悉尼, 租房, 留学",
  "metadata": {
    "title": "悉尼租房攻略",
    "author": "小红薯123",
    "keyword": "悉尼租房",
    "city": "sydney",
    "domain": "housing",
    "traffic_level": "level_4_5",
    "interaction": 2500,
    "upload_time": "2025-01-15"
  },
  "comments": "[用户A]很实用！ | [用户B]请问中介费多少？"
}
```

---

### 步骤2：选择向量化方案

#### 方案A：本地Embedding（推荐入门）
使用开源模型，无需API费用：
```python
# 安装依赖
pip install sentence-transformers chromadb

# 示例代码
from sentence_transformers import SentenceTransformer
import chromadb
import json

# 加载中文Embedding模型（推荐）
model = SentenceTransformer('shibing624/text2vec-base-chinese')

# 读取JSONL数据
docs = []
with open('datas/excel_datas/rag_documents/notes_rag_xxx.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        docs.append(json.loads(line))

# 提取文本和元数据
texts = [doc['text'] for doc in docs]
metadatas = [doc['metadata'] for doc in docs]
ids = [doc['id'] for doc in docs]

# 向量化并存入Chroma
client = chromadb.Client()
collection = client.create_collection(
    name="xhs_australia_notes",
    metadata={"description": "小红书澳洲笔记RAG数据库"}
)

# 批量插入（Chroma会自动调用embedding）
collection.add(
    documents=texts,
    metadatas=metadatas,
    ids=ids
)

# 检索测试
results = collection.query(
    query_texts=["悉尼租房价格"],
    n_results=5
)
print(results)
```

**推荐模型**：
- `shibing624/text2vec-base-chinese` - 通用中文（768维）
- `moka-ai/m3e-base` - 中英混合（768维）
- `BAAI/bge-large-zh-v1.5` - 高性能中文（1024维）

#### 方案B：云端API（推荐生产）
使用商业API，效果更好：
```python
# OpenAI Embedding
import openai
openai.api_key = "your-api-key"

def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"  # 或 text-embedding-3-large
    )
    return response.data[0].embedding

# 或使用国内服务（智谱AI、阿里通义等）
```

---

### 步骤3：选择向量数据库

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **ChromaDB** | 本地开发/小规模 | 零配置、轻量级、支持过滤 | 性能有限（\u003c100万条） |
| **Faiss** | 高性能检索 | Meta开源、超快速度 | 需手动管理元数据 |
| **Pinecone** | 生产环境 | 全托管、高可用 | 收费服务 |
| **Milvus** | 大规模部署 | 分布式、功能完整 | 部署复杂 |

**推荐起步方案**：ChromaDB（已在上面代码示例）

---

### 步骤4：构建检索接口

创建 `xhs_utils/vector_search.py`：
```python
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class XHSVectorSearch:
    def __init__(self, db_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection("xhs_australia_notes")
        self.model = SentenceTransformer('shibing624/text2vec-base-chinese')
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        city: str = None,
        domain: str = None,
        min_interaction: int = None
    ) -> List[Dict]:
        # 构建过滤条件
        where = {}
        if city:
            where['city'] = city
        if domain:
            where['domain'] = domain
        if min_interaction:
            where['interaction'] = {"$gte": min_interaction}
        
        # 检索
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where if where else None
        )
        
        return results

# 使用示例
searcher = XHSVectorSearch()
results = searcher.search(
    query="悉尼租房一个月多少钱",
    n_results=5,
    city="sydney",
    min_interaction=500
)
```

---

### 步骤5：集成到项目

修改 `run.py`，新增RAG构建命令：
```python
def build_vector_db():
    """构建向量数据库"""
    from xhs_utils.vector_builder import build_chroma_db
    
    logger.info("开始构建向量数据库...")
    
    # 先导出JSONL
    export_rag_data()
    
    # 构建向量库
    build_chroma_db(
        jsonl_path="datas/excel_datas/rag_documents/notes_rag_*.jsonl",
        db_path="./chroma_db",
        embedding_model="shibing624/text2vec-base-chinese"
    )
    
    logger.info("✅ 向量数据库构建完成!")
```

---

## 下一步行动建议

1. **立即可做**（无需等待）：
   ```bash
   python run.py --export-rag  # 导出现有数据
   ```

2. **安装向量化依赖**：
   ```bash
   pip install sentence-transformers chromadb
   ```

3. **选择方案**：
   - 如果只是实验/学习 → ChromaDB + 本地模型
   - 如果是生产应用 → Pinecone + OpenAI Embedding

4. **创建向量化脚本**：我可以帮您编写完整的 `vector_builder.py` 和 `vector_search.py`。

---

## 性能参考

以当前数据规模估算：
- **假设爬取1万条笔记**
- **每条平均500字** → 总文本约5MB
- **使用768维向量** → 向量库约30MB
- **ChromaDB检索速度** → \u003c100ms（本地）
- **Embedding耗时** → 约10分钟（本地GPU）或2分钟（OpenAI API）

---

## 总结

项目**已具备RAG数据准备能力**，只需补充向量化模块即可完成RAG系统。建议从ChromaDB起步，快速验证效果后再考虑升级到企业级方案。
