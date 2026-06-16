"""项目配置加载器 - 读取 loom.yaml 项目配置。

负责：
- 加载 loom.yaml 项目配置文件
- 提供合理的默认值
- 类型安全的配置访问

使用方式:
    config = LoomConfig.load(project_root)
    print(config.model)  # "gpt-4"
    print(config.token_budget)  # 8000
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
class LoomConfig:
    """L.O.O.M. 项目配置。

    Attributes:
        version: 项目版本号
        model: 默认 LLM 模型名称
        token_budget: Token 总预算
        output_reserve: 输出预留 Token 数
        extra: 其他自定义配置
    """

    version: str = DEFAULT_VERSION
    model: str = DEFAULT_MODEL
    token_budget: int = DEFAULT_TOKEN_BUDGET
    output_reserve: int = DEFAULT_OUTPUT_RESERVE
    extra: dict = field(default_factory=dict)

    @property
    def input_token_budget(self) -> int:
        """输入 Token 预算（总预算 - 输出预留）。"""
        return self.token_budget - self.output_reserve

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

        # 提取已知字段，其余放入 extra
        known_keys = {"version", "model", "token_budget", "output_reserve"}
        extra = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            version=str(data.get("version", DEFAULT_VERSION)),
            model=str(data.get("model", DEFAULT_MODEL)),
            token_budget=int(data.get("token_budget", DEFAULT_TOKEN_BUDGET)),
            output_reserve=int(data.get("output_reserve", DEFAULT_OUTPUT_RESERVE)),
            extra=extra,
        )

    def save(self, project_root: Path) -> None:
        """将配置保存到 loom.yaml。

        Args:
            project_root: 项目根目录路径
        """
        config_path = project_root / "loom.yaml"
        data = {
            "version": self.version,
            "model": self.model,
            "token_budget": self.token_budget,
            "output_reserve": self.output_reserve,
            **self.extra,
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            logger.info("配置已保存: %s", config_path)
        except Exception as e:
            logger.error("配置保存失败: %s", e)
