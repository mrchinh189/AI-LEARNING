"""Nguyên tắc 4: bot tự chấm bài theo rubric trước khi nộp.

Người chấm là một lời gọi model riêng, không thấy quá trình làm bài — chỉ thấy
đề, rubric và bài nộp — nên khó "tự khen" như khi bot tự đánh giá trong cùng
cuộc hội thoại.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .llm import LLM

GRADER_SYSTEM = (
    "Bạn là người chấm bài nghiêm khắc và công bằng. Chấm bài nộp theo đúng từng "
    "tiêu chí trong rubric, không thêm tiêu chí mới. Chỉ cho 'passed' khi MỌI tiêu "
    "chí bắt buộc đều đạt. Phản hồi phải cụ thể, chỉ ra chỗ cần sửa."
)


class CriterionResult(BaseModel):
    criterion: str
    met: bool
    note: str


class Grade(BaseModel):
    passed: bool
    score: int = Field(description="Điểm tổng 0-10")
    criteria: list[CriterionResult]
    feedback: str = Field(description="Những gì cần sửa để đạt, rỗng nếu đã đạt")


def grade(llm: LLM, *, task: str, rubric: str, answer: str) -> Grade:
    prompt = (
        f"<task>\n{task}\n</task>\n\n<rubric>\n{rubric}\n</rubric>\n\n"
        f"<submission>\n{answer}\n</submission>"
    )
    return llm.parse(purpose="grade", system=GRADER_SYSTEM, prompt=prompt, schema=Grade)
