"""
阅读进度追踪模块
本地记录连载阅读进度，支持续读、跳过、换主题等
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROGRESS_FILE = Path(__file__).parent / "progress.json"


class ProgressTracker:
    """连载阅读进度管理器"""

    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default()

    def _default(self) -> dict:
        return {
            "book": None,
            "chapter": None,
            "chapter_num": 0,       # 数字章节号，用于自动递增
            "total_parts": 0,
            "current_part": 0,
            "parts": [],          # 预生成的各片段内容
            "recap": "",          # 前情提要
            "status": "idle",     # idle / reading / summarizing
            "auto_continue": True, # 章节完成后自动推下一章
        }

    def save(self):
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def reset(self):
        """重置进度"""
        self.data = self._default()
        self.save()

    def start_series(self, book: str, chapter: str, parts: list[dict], total: int, chapter_num: int = None):
        """
        开始一个新的连载

        Args:
            book: 书名
            chapter: 章节
            parts: 各片段内容列表
            total: 总片段数
            chapter_num: 数字章节号（可选，用于自动递增）
        """
        self.data = {
            "book": book,
            "chapter": chapter,
            "chapter_num": chapter_num or self.data.get("chapter_num", 0),
            "total_parts": total,
            "current_part": 0,
            "parts": parts,
            "recap": "",
            "status": "reading",
            "auto_continue": self.data.get("auto_continue", True),
        }
        self.save()
        logger.info(f"开始连载: 《{book}》第{chapter}章，共 {total} 篇")

    def get_next_chapter_info(self) -> dict:
        """获取下一章信息（自动递增章节号）"""
        book = self.data.get("book")
        num = self.data.get("chapter_num", 0) + 1
        # 中文数字映射
        cn_nums = ["零","一","二","三","四","五","六","七","八","九","十",
                   "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十"]
        chapter_cn = cn_nums[num] if num < len(cn_nums) else str(num)
        return {
            "book": book,
            "chapter": chapter_cn,
            "chapter_num": num,
        }

    def get_next_part(self) -> dict | None:
        """
        获取下一个待推送的片段

        Returns:
            dict: {"part_num": int, "total": int, "content": str, "recap": str, "is_last": bool}
                  或 None（表示已全部读完）
        """
        if self.data["status"] != "reading":
            return None

        idx = self.data["current_part"]
        total = self.data["total_parts"]

        if idx >= total:
            self.data["status"] = "summarizing"
            self.save()
            return None

        part = self.data["parts"][idx]
        self.data["current_part"] = idx + 1

        # 更新前情提要（用本篇的 recap_next 作为下一篇的前情提要）
        next_recap = part.get("recap_next", "")
        if next_recap:
            self.data["recap"] = next_recap
        self.save()

        return {
            "part_num": idx + 1,
            "total": total,
            "content": part,  # 整个 part 就是内容 dict（含 sections, case, quote, image_keyword）
            "recap": self.data.get("recap", ""),
            "is_last": (idx + 1 >= total),
            "book": self.data["book"],
            "chapter": self.data["chapter"],
        }

    def update_recap(self, recap: str):
        """更新前情提要"""
        self.data["recap"] = recap
        self.save()

    def skip_to_next(self) -> dict | None:
        """跳过当前片段，直接到下一篇"""
        # 不增加 current_part，让 get_next_part 自然推进
        return self.get_next_part()

    def next_chapter(self):
        """跳到下一章（重置进度）"""
        self.reset()
        logger.info("已重置进度，等待新章节")

    def get_summary_flag(self) -> bool:
        """检查是否该发总结了"""
        if self.data["status"] == "summarizing":
            self.data["status"] = "idle"
            self.save()
            return True
        return False

    def peek_next_title(self) -> str:
        """预览下一篇的标题（不推进进度）"""
        idx = self.data["current_part"]
        total = self.data["total_parts"]
        if idx >= total:
            return ""
        next_part = self.data["parts"][idx]
        sections = next_part.get("sections", [])
        if sections:
            return sections[0].get("heading", "")
        return ""

    @property
    def current_book(self) -> str:
        return self.data.get("book")

    @property
    def current_chapter(self) -> str:
        return self.data.get("chapter")
