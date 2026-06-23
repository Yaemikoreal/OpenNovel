"""项目配置加载器 - 读取 loom.yaml 项目配置。

负责：
- 加载 loom.yaml 项目配置文件
- 提供合理的默认值
- 类型安全的配置访问
- per-agent LLM 配置覆盖

使用方式:
    config = LoomConfig.load(project_root)
    print(config.model)  # "gpt-4"
    print(config.token_budget)  # 8000

    # 获取 Agent 专用 LLM 配置
    writer_cfg = config.get_agent_llm_config("writer")
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# 默认配置值
DEFAULT_MODEL = "gpt-4"
DEFAULT_TOKEN_BUDGET = 8000
DEFAULT_OUTPUT_RESERVE = 2000
DEFAULT_VERSION = "1.0.1"


@dataclass
class AgentConfig:
    """单个 Agent 的 LLM 配置覆盖。

    未设置的字段继承 LoomConfig 的默认值。
    """

    model: str | None = None
    api_base: str | None = None
    api_key: str | None = None


@dataclass
class LoomConfig:
    """L.O.O.M. 项目配置。

    Attributes:
        version: 项目版本号
        model: 默认 LLM 模型名称
        token_budget: Token 总预算
        output_reserve: 输出预留 Token 数
        api_base: 自定义 API 端点（用于 OpenAI 兼容接口）
        api_key: API 密钥（优先级高于环境变量）
        creative_direction: 创作方向描述 (loom auto 用)
        target_chapters: 目标章节数 (loom auto 用)
        words_per_chapter: 每章目标字数 (loom auto 用)
        outline: 大纲文件路径 (loom auto 用)
        agent_writer: Writer Agent 的 LLM 配置覆盖
        agent_critic: Critic Agent 的 LLM 配置覆盖
        agent_manager: Manager Agent 的 LLM 配置覆盖
        extra: 其他自定义配置
    """

    version: str = DEFAULT_VERSION
    model: str = DEFAULT_MODEL
    token_budget: int = DEFAULT_TOKEN_BUDGET
    output_reserve: int = DEFAULT_OUTPUT_RESERVE
    api_base: str | None = None
    api_key: str | None = None

    # loom auto 创作配置
    creative_direction: str = ""
    target_chapters: int = 5
    words_per_chapter: int = 3000
    outline: str = "outlines/story.md"

    # per-agent LLM 配置覆盖
    agent_writer: AgentConfig = field(default_factory=AgentConfig)
    agent_critic: AgentConfig = field(default_factory=AgentConfig)
    agent_manager: AgentConfig = field(default_factory=AgentConfig)

    extra: dict = field(default_factory=dict)

    @property
    def input_token_budget(self) -> int:
        """输入 Token 预算（总预算 - 输出预留）。"""
        return self.token_budget - self.output_reserve

    def get_agent_llm_config(self, agent_name: str) -> dict[str, str | None]:
        """获取指定 Agent 的 LLM 配置，未设置的字段继承默认值。

        Args:
            agent_name: Agent 名称 ("writer", "critic", "manager")

        Returns:
            包含 model, api_base, api_key 的字典
        """
        agent_cfg_map = {
            "writer": self.agent_writer,
            "critic": self.agent_critic,
            "manager": self.agent_manager,
        }
        agent_cfg = agent_cfg_map.get(agent_name, AgentConfig())
        return {
            "model": agent_cfg.model or self.model,
            "api_base": agent_cfg.api_base or self.api_base,
            "api_key": agent_cfg.api_key or self.api_key,
        }

    @classmethod
    def load(cls, project_root: Path) -> "LoomConfig":
        """从项目根目录加载配置。

        如果 loom.yaml 不存在或读取失败，返回默认配置。

        Args:
            project_root: 项目根目录路径

        Returns:
            LoomConfig 实例
        """
        config_path = project_root / "loom.yaml"
        if not config_path.exists():
            logger.info("配置文件不存在，使用默认配置: %s", config_path)
            return cls()

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("配置文件读取失败，使用默认配置: %s", e)
            return cls()

        # 解析 per-agent 配置
        agents_data = data.get("agents", {})
        agent_writer = _parse_agent_config(agents_data.get("writer", {}))
        agent_critic = _parse_agent_config(agents_data.get("critic", {}))
        agent_manager = _parse_agent_config(agents_data.get("manager", {}))

        # 提取已知字段，其余放入 extra
        known_keys = {
            "version", "model", "token_budget", "output_reserve",
            "api_base", "api_key", "agents",
            "creative_direction", "target_chapters", "words_per_chapter", "outline",
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            version=str(data.get("version", DEFAULT_VERSION)),
            model=str(data.get("model", DEFAULT_MODEL)),
            token_budget=int(data.get("token_budget", DEFAULT_TOKEN_BUDGET)),
            output_reserve=int(data.get("output_reserve", DEFAULT_OUTPUT_RESERVE)),
            api_base=data.get("api_base"),
            api_key=data.get("api_key"),
            creative_direction=str(data.get("creative_direction", "")),
            target_chapters=int(data.get("target_chapters", 5)),
            words_per_chapter=int(data.get("words_per_chapter", 3000)),
            outline=str(data.get("outline", "outlines/story.md")),
            agent_writer=agent_writer,
            agent_critic=agent_critic,
            agent_manager=agent_manager,
            extra=extra,
        )

    def save(self, project_root: Path) -> None:
        """将配置保存到 loom.yaml。

        Args:
            project_root: 项目根目录路径
        """
        config_path = project_root / "loom.yaml"
        data: dict = {
            "version": self.version,
            "model": self.model,
            "token_budget": self.token_budget,
            "output_reserve": self.output_reserve,
        }
        if self.api_base:
            data["api_base"] = self.api_base
        if self.api_key:
            data["api_key"] = self.api_key

        # 创作配置
        if self.creative_direction:
            data["creative_direction"] = self.creative_direction
        data["target_chapters"] = self.target_chapters
        data["words_per_chapter"] = self.words_per_chapter
        data["outline"] = self.outline

        # per-agent 配置
        agents: dict = {}
        for name, cfg in [("writer", self.agent_writer), ("critic", self.agent_critic), ("manager", self.agent_manager)]:
            agent_data: dict = {}
            if cfg.model:
                agent_data["model"] = cfg.model
            if cfg.api_base:
                agent_data["api_base"] = cfg.api_base
            if cfg.api_key:
                agent_data["api_key"] = cfg.api_key
            if agent_data:
                agents[name] = agent_data
        if agents:
            data["agents"] = agents

        data.update(self.extra)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            logger.info("配置已保存: %s", config_path)
        except Exception as e:
            logger.error("配置保存失败: %s", e)


def _parse_agent_config(data: dict) -> AgentConfig:
    """从 YAML 数据解析 AgentConfig。

    Args:
        data: YAML 中 agents.writer / agents.critic / agents.manager 的值

    Returns:
        AgentConfig 实例
    """
    if not data:
        return AgentConfig()
    return AgentConfig(
        model=data.get("model"),
        api_base=data.get("api_base"),
        api_key=data.get("api_key"),
    )
