"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {"name": "explorer",
         "description": "Delegate when requirements, shared code, or dirty input data need inspection before implementation.",
         "system_prompt": "Inspect the supplied files, README and docstrings. Identify requirements, root causes and edge cases. Do not modify files. Return evidence with file paths and actionable findings; distinguish observations from assumptions."},
        {"name": "implementer",
         "description": "Delegate when code must be repaired or data and logs must be transformed into required output files.",
         "system_prompt": "Implement only the delegated requirements. Read relevant specifications first, fix shared root causes, handle input edge cases and run available tests or validation. Report actual changed files, commands and outcomes. Never modify tests or skills."},
        {"name": "reviewer",
         "description": "Delegate after implementation to independently verify outputs, requirements and boundary cases.",
         "system_prompt": "Independently inspect the requested outputs against all supplied rules and docstrings. Run tests and verify formats and edge cases. Do not modify files. Return concrete discrepancies and validation evidence; do not claim success without checking."},
    ]
