"""
GitHub Pages 网页生成模块
每次推送时生成独立的 HTML 页面，保存到 pages/ 目录
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

PAGES_DIR = Path(__file__).parent / "pages"


def generate_page(
    data: dict,
    part_num: int = None,
    total: int = None,
    recap: str = None,
    is_last: bool = False,
    series_title: str = None,
    next_title: str = None,
    next_url: str = None,
    prev_url: str = None,
) -> str:
    """生成一个完整的 HTML 页面"""
    title = data.get("title", "")
    sections = data.get("sections", [])
    key_terms = data.get("key_terms", [])
    case = data.get("case", "")
    quote = data.get("quote", "")

    def bold_text(text: str) -> str:
        return re.sub(r'\*\*(.+?)\*\*', r'<b style="color:#c0392b;font-weight:700;">\1</b>', text)

    # 进度条
    progress_html = ""
    if part_num is not None and total:
        filled = int(part_num / total * 10)
        bar = "█" * filled + "░" * (10 - filled)
        pct = int(part_num / total * 100)
        progress_html = f'''
  <div style="margin-bottom:16px;">
    <span style="font-size:13px;color:#999;letter-spacing:1px;">{bar} 第 {part_num}/{total} 篇（{pct}%）</span>
  </div>'''

    # 前情提要
    recap_html = ""
    if recap:
        recap_html = f'''
  <div style="background:#fff8e1;border-left:4px solid #ffb300;padding:12px 16px;margin-bottom:20px;border-radius:0 8px 8px 0;">
    <div style="font-size:13px;font-weight:600;color:#f57c00;margin-bottom:4px;">📖 前情提要</div>
    <div style="font-size:14px;color:#666;line-height:1.7;">{recap}</div>
  </div>'''

    # 关键词标签
    tags_html = ""
    if key_terms:
        tags = "".join(f'<span style="display:inline-block;background:#fce4ec;color:#e94560;font-size:12px;padding:3px 10px;border-radius:12px;margin:3px 4px 3px 0;font-weight:500;">{t}</span>' for t in key_terms)
        tags_html = f'''
  <div style="margin-bottom:20px;">
    {tags}
  </div>'''

    # 系列标题
    series_html = ""
    if series_title:
        series_html = f'<div style="font-size:13px;color:#999;margin-bottom:6px;letter-spacing:0.5px;">{series_title}</div>'

    # 知识点段落
    sections_html = ""
    for i, s in enumerate(sections):
        heading = s.get("heading", "")
        body = bold_text(s.get("body", ""))
        separator = '<div style="border-top:1px dashed #e0e0e0;margin:20px 0;"></div>' if i > 0 else ""
        sections_html += f'''
  {separator}
  <div style="margin-bottom:8px;">
    <div style="font-size:17px;font-weight:700;color:#e94560;margin-bottom:10px;">
      ▎{heading}
    </div>
    <div style="font-size:15px;color:#555;line-height:1.9;padding-left:4px;">
      {body}
    </div>
  </div>'''

    # 底部导航
    nav_html = ""
    if prev_url:
        nav_html += f'<a href="{prev_url}" style="display:inline-block;padding:8px 20px;background:#e94560;color:#fff;text-decoration:none;border-radius:20px;font-size:14px;margin:4px;">← 上一篇</a> '
    if next_url and next_title:
        nav_html += f'<a href="{next_url}" style="display:inline-block;padding:8px 20px;background:#e94560;color:#fff;text-decoration:none;border-radius:20px;font-size:14px;margin:4px;">下一篇：{next_title} →</a>'
    elif is_last:
        nav_html += '<span style="font-size:14px;color:#888;">本章已完结</span>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 每日学习推送</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #f0f0f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; }}
  .container {{ max-width: 600px; margin: 0 auto; background: #fff; min-height: 100vh; padding: 20px; }}
</style>
</head>
<body>
<div class="container">
<div style="max-width:100%;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;color:#333;line-height:1.8;padding:16px;border-radius:12px;">

  {series_html}
  {progress_html}
  {recap_html}

  <h2 style="font-size:21px;font-weight:700;color:#1a1a2e;margin:0 0 8px 0;padding-bottom:14px;border-bottom:2.5px solid #e94560;">
    {title}
  </h2>

  {tags_html}
  {sections_html}

  {f'''
  <div style="border-top:1px dashed #e0e0e0;margin:24px 0 20px 0;"></div>
  <div style="background:#fafafa;border-left:4px solid #e94560;padding:14px 18px;margin-bottom:20px;border-radius:0 8px 8px 0;">
    <div style="font-size:14px;font-weight:600;color:#e94560;margin-bottom:8px;">📋 临床案例</div>
    <div style="font-size:15px;color:#555;line-height:1.8;">{case}</div>
  </div>''' if case else ""}

  {f'''
  <div style="text-align:center;margin:28px 0 12px 0;">
    <div style="font-size:17px;font-style:italic;color:#1a1a2e;font-weight:500;line-height:1.6;">
      "{quote}"
    </div>
  </div>''' if quote else ""}

  <!-- 底部导航 -->
  <div style="text-align:center;margin-top:28px;padding:16px;background:#f5f5f5;border-radius:8px;">
    {nav_html}
  </div>

  <div style="text-align:center;margin-top:14px;">
    <span style="font-size:12px;color:#bbb;">每日学习推送 · {datetime.now().strftime('%Y-%m-%d')}</span>
  </div>

</div>
</div>
</body>
</html>"""
    return html


def save_page(
    filename: str,
    data: dict,
    part_num: int = None,
    total: int = None,
    recap: str = None,
    is_last: bool = False,
    series_title: str = None,
    next_title: str = None,
    next_url: str = None,
    prev_url: str = None,
) -> str:
    """
    生成并保存 HTML 页面

    Args:
        filename: 文件名（不含路径），如 "ch1-part1.html"

    Returns:
        str: 生成的文件路径
    """
    PAGES_DIR.mkdir(exist_ok=True)
    filepath = PAGES_DIR / filename

    html = generate_page(
        data=data,
        part_num=part_num,
        total=total,
        recap=recap,
        is_last=is_last,
        series_title=series_title,
        next_title=next_title,
        next_url=next_url,
        prev_url=prev_url,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"网页已生成: {filepath}")
    return str(filepath)
