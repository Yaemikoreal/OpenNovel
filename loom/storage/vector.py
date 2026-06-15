"""向量索引存储适配层。

基于 LlamaIndex + BGE-M3 实现本地向量索引管理：
- 索引的构建与持久化
- 增量更新
- 语义检索
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VectorStore:
    """向量索引存储，管理 LlamaIndex 向量索引的生命周期。

    使用 BGE-M3 本地模型进行文本向量化，防止数据泄漏。
    索引持久化到 .index/ 目录，支持增量更新。
    """

    def __init__(
        self,
        project_root: Path,
        index_dir: Optional[Path] = None,
        embedding_model: str = "BAAI/bge-m3",
    ) -> None:
        """初始化向量存储。

        Args:
            project_root: 项目根目录路径
            index_dir: 索引持久化目录，默认为 project_root / ".index"
            embedding_model: Embedding 模型名称，默认使用 BGE-M3
        """
        self.project_root = project_root
        self.index_dir = index_dir or project_root / ".index"
        self.embedding_model = embedding_model
        self._index = None

    def build_index(self, documents_dir: Path) -> None:
        """从文档目录构建向量索引。

        Args:
            documents_dir: 文档目录路径
        """
        if not documents_dir.exists():
            logger.warning("文档目录不存在: %s", documents_dir)
            return

        # TODO: 实现 LlamaIndex 索引构建
        # from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
        # from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        #
        # embed_model = HuggingFaceEmbedding(model_name=self.embedding_model)
        # documents = SimpleDirectoryReader(str(documents_dir)).load_data()
        # storage_context = StorageContext.from_defaults(persist_dir=str(self.index_dir))
        # self._index = VectorStoreIndex.from_documents(
        #     documents, embed_model=embed_model, storage_context=storage_context
        # )
        # self._index.storage_context.persist()
        logger.info("向量索引构建完成 (待实现): %s", documents_dir)

    def load_index(self) -> bool:
        """从持久化目录加载已有索引。

        Returns:
            是否成功加载索引
        """
        if not self.index_dir.exists():
            logger.warning("索引目录不存在: %s", self.index_dir)
            return False

        # TODO: 实现 LlamaIndex 索引加载
        # from llama_index.core import load_index_from_storage, StorageContext
        # storage_context = StorageContext.from_defaults(persist_dir=str(self.index_dir))
        # self._index = load_index_from_storage(storage_context)
        logger.info("向量索引加载完成 (待实现)")
        return True

    def query(self, query_text: str, top_k: int = 3) -> list[str]:
        """执行语义检索查询。

        Args:
            query_text: 查询文本
            top_k: 返回最相关的 top_k 条结果

        Returns:
            检索结果文本列表
        """
        if self._index is None:
            logger.warning("索引未加载，返回空结果")
            return []

        # TODO: 实现 LlamaIndex 查询
        # query_engine = self._index.as_query_engine(similarity_top_k=top_k)
        # response = query_engine.query(query_text)
        # return [str(node) for node in response.source_nodes]
        return []

    def add_document(self, text: str, metadata: Optional[dict] = None) -> None:
        """向索引中添加单个文档，触发增量更新。

        Args:
            text: 文档文本
            metadata: 文档元数据
        """
        if self._index is None:
            logger.warning("索引未初始化，无法添加文档")
            return

        # TODO: 实现 LlamaIndex 增量插入
        # from llama_index.core import Document
        # doc = Document(text=text, metadata=metadata or {})
        # self._index.insert(doc)
        logger.info("文档已添加到索引 (待实现)")

    def delete_document(self, doc_id: str) -> None:
        """从索引中删除指定文档。

        Args:
            doc_id: 文档 ID
        """
        if self._index is None:
            logger.warning("索引未初始化，无法删除文档")
            return

        # TODO: 实现 LlamaIndex 文档删除
        # self._index.delete_ref_doc(doc_id)
        logger.info("文档已从索引删除 (待实现)")
