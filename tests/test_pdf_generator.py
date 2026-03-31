import os
import pytest
from pathlib import Path
from orchestrator.pdf_generator import generate_pdf


def test_generate_pdf_creates_file(tmp_path):
    """generate_pdf creates a PDF file from markdown content."""
    content = "# 測試懶人包\n\n## 核心概念\n這是一個測試。\n\n## 重點整理\n1. 第一點\n2. 第二點"
    title = "測試懶人包"
    output_path = tmp_path / "test.pdf"

    generate_pdf(content, title, str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    # PDF starts with %PDF
    with open(output_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_generate_pdf_handles_chinese(tmp_path):
    """generate_pdf correctly renders Chinese characters."""
    content = "# AI Agent 完整攻略\n\n短影音不是靠量取勝，是靠懂「你是誰」。"
    output_path = tmp_path / "chinese.pdf"

    generate_pdf(content, "AI Agent 完整攻略", str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 100  # non-trivial size
