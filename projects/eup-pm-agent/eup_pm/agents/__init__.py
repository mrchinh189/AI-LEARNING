"""Đội AI agent: ① Điều phối, ② Lập kế hoạch, ③ Thu thập tiến độ, ⑤ Rủi ro.

④ Đối chiếu chứng từ, ⑥ Báo cáo và ⑦ Giao tiếp nằm ở evidence.py, jobs.py, llm.py
vì phần lớn là việc tất định, không cần vòng lặp agent.
"""

from .router import Team

__all__ = ["Team"]
