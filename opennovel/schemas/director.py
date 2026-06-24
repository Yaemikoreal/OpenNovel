"""Director Agent 输出模型。

Director 分析已完成章节的全局叙事状态，
输出策略指导用于调整后续章节的创作方向。
"""

from pydantic import BaseModel


class DirectorAnalysis(BaseModel):
    """Director Agent 的分析结果。

    用于注入下一章的创作策略，而非直接修改大纲。
    """

    pacing_assessment: str
    """节奏评估：如 "过快" / "过慢" / "适中" / "先慢后快"。"""

    tension_curve: str
    """张力曲线描述：如 "持续上升" / "起伏" / "下降" / "堆积过高"。"""

    character_arc_status: dict[str, str]
    """每个角色的弧线状态：如 {"char_001": "成长中，尚未达到转折点"}。"""

    strategic_guidance: str
    """对下一章的策略指导（将注入 chapter_hint）。"""

    creative_direction_adjustment: str = ""
    """创作方向调整（将合并到 Writer 的 creative_direction）。可选。"""

    warnings: list[str] = []
    """警告列表：如 ["连续3章评分下降", "因果压力堆积过高"]。"""
