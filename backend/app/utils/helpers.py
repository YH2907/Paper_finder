"""辅助工具函数"""
import uuid
from datetime import datetime
from typing import Any, Optional


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


def get_current_timestamp() -> datetime:
    """获取当前时间戳"""
    return datetime.utcnow()


def truncate_text(text: str, max_length: int = 500) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def extract_doi_from_url(url: str) -> Optional[str]:
    """从 URL 提取 DOI"""
    if "doi.org/" in url:
        return url.split("doi.org/")[-1]
    return None


def format_authors(authors: list[str], max_display: int = 3) -> str:
    """格式化作者列表"""
    if not authors:
        return "未知作者"
    if len(authors) <= max_display:
        return ", ".join(authors)
    return f"{', '.join(authors[:max_display])} 等 {len(authors)} 位作者"


def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ""
    # 移除多余空白
    text = " ".join(text.split())
    # 移除特殊字符
    text = text.strip()
    return text


def paginate_params(page: int = 1, per_page: int = 20) -> tuple[int, int]:
    """分页参数处理"""
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    offset = (page - 1) * per_page
    return offset, per_page
