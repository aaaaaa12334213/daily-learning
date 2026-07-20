"""
AI 内容生成模块
使用 OpenAI 兼容接口生成每日学习内容
"""

import json
import random
import logging
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)


class ContentGenerator:
    """AI 学习内容生成器"""

    def __init__(self, api_base: str, api_key: str, model: str):
        self.client = OpenAI(base_url=api_base, api_key=api_key)
        self.model = model

    def generate(
        self,
        topics: list[str],
        length: str = "中",
        date: str = None,
        book: str = None,
        chapter: str = None,
    ) -> dict:
        """
        生成今日学习内容

        Args:
            topics: 可选主题列表
            length: 内容长度（短/中/长）
            date: 日期字符串，默认今天
            book: 指定书名（可选）
            chapter: 指定章节（可选）

        Returns:
            dict: {"title": str, "content": str}
        """
        if not date:
            date = datetime.now().strftime("%Y年%m月%d日")

        length_map = {"短": "200字左右", "中": "500字左右", "长": "1000字左右"}
        length_desc = length_map.get(length, "500字左右")

        if book:
            # 书籍模式：围绕指定书籍和章节生成
            chapter_info = f"的第 {chapter} 章" if chapter else ""
            prompt = f"""你是一个中医学习助手。请围绕《{book}》{chapter_info}的内容，生成一篇适合碎片化阅读的学习笔记。

请严格按以下 JSON 格式输出（不要输出其他内容）：
{{
  "title": "本章标题",
  "image_keyword": "一个英文关键词，用于搜索配图，如 chinese-medicine, herbs, acupuncture",
  "sections": [
    {{"heading": "小标题", "body": "正文内容"}}
  ],
  "case": "一个临床案例或应用场景",
  "quote": "一句金句或思考题"
}}

要求：
- 内容长度：{length_desc}
- sections 包含 2-4 个知识点，每个知识点有 heading 和 body
- 语言通俗易懂，适合快速阅读
- 直接进入内容，不要套话"""
            system_prompt = "你是一个专业的中医知识讲解者，擅长将中医经典内容简化为易学易懂的学习笔记。输出必须是合法 JSON。"
        else:
            # 通用模式
            topic = random.choice(topics)
            prompt = f"""你是一个每日学习推送助手。今天是 {date}，请围绕「{topic}」这个主题，生成一篇适合碎片化阅读的学习内容。

请严格按以下 JSON 格式输出（不要输出其他内容）：
{{
  "title": "吸引人的标题",
  "image_keyword": "一个英文关键词，用于搜索配图",
  "sections": [
    {{"heading": "小标题", "body": "正文内容"}}
  ],
  "case": "一个实际案例或应用场景",
  "quote": "一句金句或思考题"
}}

要求：
- 内容长度：{length_desc}
- sections 包含 1-3 个知识点
- 语言通俗易懂，适合快速阅读
- 不要有套话开头，直接进入内容"""
            system_prompt = "你是一个优质的学习内容创作者，擅长将复杂知识简化为易读的内容。输出必须是合法 JSON。"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000,
            )

            raw = response.choices[0].message.content.strip()

            # 尝试解析 JSON，兼容 AI 可能输出 ```json ... ``` 包裹的情况
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            title = data.get("title", f"{date} 每日学习")
            image_keyword = data.get("image_keyword", "learning")

            logger.info(f"内容生成成功: {title}")
            return {
                "title": f"📚 {title}",
                "content": data,          # 结构化数据，由 pusher 渲染为 HTML
                "image_keyword": image_keyword,
            }

        except Exception as e:
            logger.error(f"内容生成失败: {e}")
            return {
                "title": f"📚 {date} 每日学习",
                "content": {"sections": [{"heading": "生成失败", "body": f"请检查 AI 配置。错误：{e}"}]},
                "image_keyword": "error",
            }

    def generate_series(
        self,
        book: str,
        chapter: str = None,
        length: str = "中",
    ) -> dict:
        """
        生成连载内容（一次性生成所有片段）

        Args:
            book: 书名
            chapter: 章节
            length: 每段长度

        Returns:
            dict: {"title": str, "parts": [{"content": dict, "image_keyword": str, "recap_next": str}, ...], "total": int}
        """
        length_map = {"短": "400字左右", "中": "600字左右", "长": "800-1000字"}
        length_desc = length_map.get(length, "600字左右")

        chapter_info = f"的第 {chapter} 章" if chapter else ""

        prompt = f"""你是一个中医学习助手。请围绕《{book}》{chapter_info}的内容，生成适合每天碎片化阅读的连载学习笔记。

要求：
1. 根据内容复杂度，智能决定分成几段（2-6段），重要的内容多分几段
2. 每段长度：{length_desc}
3. 每段包含 2-3 个知识点，讲透讲清楚，要有深度
4. 最后一段要有总结回顾

请严格按以下 JSON 格式输出（不要输出其他内容）：
{{
  "title": "连载总标题",
  "parts": [
    {{
      "sections": [{{"heading": "小标题", "body": "正文，重要术语用**加粗**标记"}}],
      "key_terms": ["本篇最重要的3-5个术语"],
      "case": "案例（可空）",
      "quote": "金句（可空）",
      "image_keyword": "精准的英文配图关键词，如 traditional-chinese-medicine-pulse-diagnosis",
      "recap_next": "为下一段写的前情提要（最后一段为空字符串）"
    }}
  ]
}}

注意：
- body 中的**重要术语**请用 **加粗** 标记，方便读者快速抓住重点
- key_terms 列出本篇最核心的术语，用于排版高亮
- image_keyword 要精准描述内容场景，用于搜索相关配图
- recap_next 是写给下一篇开头的「前情提要」，用一两句话概括本篇要点
- 第一篇的 recap_next 概括第一篇内容，第二篇开头会显示它
- 最后一段的 recap_next 为空字符串
- 直接输出 JSON，不要其他内容"""

        system_prompt = "你是一个专业的中医知识讲解者，擅长将内容拆分为适合每日阅读的连载片段。输出必须是合法 JSON。"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
            )

            raw = response.choices[0].message.content.strip()
            data = self._parse_json(raw)

            if data is None:
                raise ValueError("AI 返回内容无法解析为 JSON")

            parts = data.get("parts", [])
            title = data.get("title", f"《{book}》{chapter_info}")

            if not parts:
                raise ValueError("AI 返回的 parts 为空")

            logger.info(f"连载生成成功: {title}，共 {len(parts)} 篇")
            return {
                "title": title,
                "parts": parts,
                "total": len(parts),
            }

        except Exception as e:
            logger.error(f"连载生成失败: {e}")
            logger.info("尝试降级：逐篇生成...")
            return self._fallback_series(book, chapter, length)

    def _parse_json(self, raw: str) -> dict | None:
        """鲁棒 JSON 解析，尝试多种策略"""
        # 策略1: 直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 策略2: 提取代码块
        for marker in ["```json", "```"]:
            if marker in raw:
                try:
                    extracted = raw.split(marker, 1)[1].split("```", 1)[0].strip()
                    return json.loads(extracted)
                except (json.JSONDecodeError, IndexError):
                    pass

        # 策略3: 找最外层 { } 匹配
        start = raw.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(raw[start:i+1])
                        except json.JSONDecodeError:
                            pass
                        break

        # 策略4: 尝试修复常见 JSON 错误（尾随逗号）
        import re
        fixed = re.sub(r',\s*([}\]])', r'\1', raw)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        return None

    def _fallback_series(self, book: str, chapter: str, length: str) -> dict:
        """降级方案：逐篇生成，每篇单独调 AI"""
        chapter_info = f"的第 {chapter} 章" if chapter else ""
        length_map = {"短": "200字左右", "中": "400字左右", "长": "600字左右"}
        length_desc = length_map.get(length, "400字左右")

        parts = []
        num_parts = 3  # 降级时默认 3 篇

        for i in range(num_parts):
            part_prompt = f"""你是中医学习助手。请为《{book}》{chapter_info}生成第 {i+1}/{num_parts} 篇学习笔记。

请严格按以下 JSON 格式输出：
{{"sections": [{{"heading": "小标题", "body": "正文"}}], "case": "案例", "quote": "金句", "image_keyword": "英文关键词", "recap_next": "下篇前情提要"}}

要求：{length_desc}，1-2个知识点。直接输出JSON。"""

            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "输出合法JSON。"},
                        {"role": "user", "content": part_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500,
                )
                raw = resp.choices[0].message.content.strip()
                part_data = self._parse_json(raw)
                if part_data:
                    parts.append(part_data)
                else:
                    raise ValueError(f"第{i+1}篇JSON解析失败")
            except Exception as e:
                logger.error(f"第{i+1}篇生成失败: {e}")
                parts.append({
                    "sections": [{"heading": "内容生成失败", "body": "请稍后重试。"}],
                    "case": "", "quote": "", "image_keyword": "error", "recap_next": ""
                })

        return {
            "title": f"《{book}》{chapter_info}",
            "parts": parts,
            "total": len(parts),
        }
