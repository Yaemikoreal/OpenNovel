"""LlamaIndex 检索路由 - 语义检索与向量索引管理。

基于 LlamaIndex + BGE-M3 实现：
- 设定文档的语义检索 (CANON 层)
- 潜意识池的灵感召回 (SUBCONSCIOUS 层)
- 增量索引构建与更新
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Retriever:
    """语义检索路由器，管理 LlamaIndex 索引与查询。

    支持两种索引类型：
    - canon: 设定文档索引，用于 CANON 层的权威设定检索
    - subconscious: 潜意识池索引，用于灵感碎片的语义召回
    """

    def __init__(self, project_root: Path, persist_dir: Optional[Path] = None) -> None:
        """初始化检索路由器。

        Args:
            project_root: 项目根目录路径
            persist_dir: 索引持久化目录，默认为 project_root / ".index"
        """
        self.project_root = project_root
        self.persist_dir = persist_dir or project_root / ".index"
        self._canon_index = None
        self._subconscious_index = None

    def build_canon_index(self) -> None:
        """构建设定文档的语义索引。

        扫描 canon/ 目录下的所有 Markdown 文件，构建 LlamaIndex 向量索引。
        """
        canon_dir = self.project_root / "canon"
        if not canon_dir.exists():
            logger.warning("设定目录不存在: %s", canon_dir)
            return

        # TODO: 实现 LlamaIndex 索引构建
        # from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
        # documents = SimpleDirectoryReader(str(canon_dir)).load_data()
        # self._canon_index = VectorStoreIndex.from_documents(documents)
        logger.info("设定索引构建完成 (待实现)")

    def build_subconscious_index(self) -> None:
        """构建潜意识池的语义索引。

        扫描 subconscious/ 目录下的所有文件，构建增量向量索引。
        """
        sub_dir = self.project_root / "subconscious"
        if not sub_dir.exists():
            logger.warning("潜意识目录不存在: %s", sub_dir)
            return

        # TODO: 实现 LlamaIndex 索引构建
        logger.info("潜意识索引构建完成 (待实现)")

    def query_canon(self, query_text: str, top_k: int = 3) -> str:
        """从设定索引中检索相关世界观规则。

        Args:
            query_text: 查询文本，通常基于当前场景描述
            top_k: 返回最相关的 top_k 条结果

        Returns:
            检索到的设定文本，多条结果以换行分隔
        """
        if self._canon_index is None:
            logger.warning("设定索引未构建，返回空结果")
            return ""

        # TODO: 实现 LlamaIndex 查询
        # query_engine = self._canon_index.as_query_engine(similarity_top_k=top_k)
        # response = query_engine.query(query_text)
        # return str(response)
        return ""

    def query_subconscious(self, query_text: str, top_k: int = 2) -> str:
        """从潜意识池中检索相似的灵感碎片。

        Args:
            query_text: 查询文本，通常基于当前正文
            top_k: 返回最相似的 top_k 条结果

        Returns:
            检索到的灵感文本，多条结果以换行分隔
        """
        if self._subconscious_index is None:
            logger.warning("潜意识索引未构建，返回空结果")
            return ""

        # TODO: 实现 LlamaIndex 查询
        return ""

    def add_to_subconscious(self, text: str, tags: Optional[list[str]] = None) -> None:
        """向潜意识池添加新的灵感碎片，并触发增量索引更新。

        Args:
            text: 灵感文本
            tags: 标签列表，用于分类和过滤
        """
        sub_dir = self.project_root / "subconscious"
        sub_dir.mkdir(parents=True, exist_ok=True)

        lines_file = sub_dir / "lines.md"
        tag_str = " ".join(f"#{t}" for t in (tags or []))
        entry = f"- {text} {tag_str}\n"

        with open(lines_file, "a", encoding="utf-8") as f:
            f.write(entry)

        # 触发增量索引更新
        self.build_subconscious_index()
        logger.info("灵感已存入潜意识池: %s", text[:50])
