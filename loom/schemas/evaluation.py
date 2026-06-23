"""Critic 评分输出模型。

Critic 对 Writer 产出的章节进行五维百分制评分。
80 分以上为合格，90 分以上为优秀。
"""

from pydantic import BaseModel, field_validator


class DimensionScore(BaseModel):
    """单个维度的评分。"""

    dimension: str
    score: int
    comment: str

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 0 <= v <= 20:
            raise ValueError(f"维度分数必须在 0-20 之间，收到: {v}")
        return v


class ChapterEvaluation(BaseModel):
    """Critic 输出的章节评分结果。"""

    total_score: int
    dimensions: list[DimensionScore]
    summary: str
    issues: list[str]
    suggestions: list[str]

    @field_validator("total_score")
    @classmethod
    def validate_total_score(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError(f"总分必须在 0-100 之间，收到: {v}")
        return v

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions_count(cls, v: list[DimensionScore]) -> list[DimensionScore]:
        if len(v) != 5:
            raise ValueError(f"必须包含 5 个维度评分，收到: {len(v)}")
        return v

    @property
    def is_pass(self) -> bool:
        """是否合格 (>=80 分)。"""
        return self.total_score >= 80

    @property
    def is_excellent(self) -> bool:
        """是否优秀 (>=90 分)。"""
        return self.total_score >= 90
