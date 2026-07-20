"""
PushPlus 微信推送模块
文档: https://www.pushplus.plus/doc/
"""

import re
import requests
import logging

logger = logging.getLogger(__name__)


def render_html(
    data: dict,
    image_keyword: str = "learning",
    part_num: int = None,
    total: int = None,
    recap: str = None,
    is_last: bool = False,
    series_title: str = None,
    next_title: str = None,
    page_url: str = None,
) -> str:
    """
    将结构化内容渲染为精美的 HTML 卡片
    """
    title = data.get("title", "")
    sections = data.get("sections", [])
    key_terms = data.get("key_terms", [])
    case = data.get("case", "")
    quote = data.get("quote", "")

    # 使用 LoremFlickr 关键词配图（真实相关图片）
    img_url = f"https://loremflickr.com/600/350/{image_keyword.replace(' ', ',')}?lock={hash(image_keyword) % 9999}"

    def bold_text(text: str) -> str:
        """将 **text** 转换为 <b>text</b>"""
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

    # 底部提示
    if is_last:
        footer_text = "本章已完结，下次推送将发送总结回顾"
    elif next_title:
        footer_text = f"下一篇：{next_title}"
    else:
        footer_text = "📖 未完待续，明天继续..."

    # 网页链接
    page_link_html = ""
    if page_url:
        page_link_html = f'''
  <div style="text-align:center;margin-top:10px;">
    <a href="{page_url}" style="font-size:13px;color:#e94560;text-decoration:none;font-weight:500;">🌐 点击打开网页版，可连续阅读 →</a>
  </div>'''

    # 系列标题
    series_html = ""
    if series_title:
        series_html = f'<div style="font-size:13px;color:#999;margin-bottom:6px;letter-spacing:0.5px;">{series_title}</div>'

    # 知识点段落（加更多留白和分隔）
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

    html = f"""
<div style="max-width:100%;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;color:#333;line-height:1.8;padding:16px;border-radius:12px;">

  <!-- 头图 -->
  <div style="margin-bottom:20px;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <img src="{img_url}" style="width:100%;height:auto;display:block;" />
  </div>

  {series_html}

  <!-- 进度条 -->
  {progress_html}

  <!-- 前情提要 -->
  {recap_html}

  <!-- 标题 -->
  <h2 style="font-size:21px;font-weight:700;color:#1a1a2e;margin:0 0 8px 0;padding-bottom:14px;border-bottom:2.5px solid #e94560;">
    {title}
  </h2>

  <!-- 关键词标签 -->
  {tags_html}

  <!-- 知识点 -->
  {sections_html}

  <!-- 案例 -->
  {f'''
  <div style="border-top:1px dashed #e0e0e0;margin:24px 0 20px 0;"></div>
  <div style="background:#fafafa;border-left:4px solid #e94560;padding:14px 18px;margin-bottom:20px;border-radius:0 8px 8px 0;">
    <div style="font-size:14px;font-weight:600;color:#e94560;margin-bottom:8px;">📋 临床案例</div>
    <div style="font-size:15px;color:#555;line-height:1.8;">{case}</div>
  </div>''' if case else ""}

  <!-- 金句 -->
  {f'''
  <div style="text-align:center;margin:28px 0 12px 0;">
    <div style="font-size:17px;font-style:italic;color:#1a1a2e;font-weight:500;line-height:1.6;">
      "{quote}"
    </div>
  </div>''' if quote else ""}

  <!-- 底部提示 -->
  <div style="text-align:center;margin-top:28px;padding:14px;background:#f5f5f5;border-radius:8px;">
    <span style="font-size:14px;color:#888;">{footer_text}</span>
  </div>

  {page_link_html}

  <!-- 操作指引 -->
  <div style="text-align:center;margin-top:14px;padding:12px;background:#e8f5e9;border-radius:8px;">
    <div style="font-size:13px;color:#2e7d32;font-weight:600;margin-bottom:4px;">📱 如何继续阅读</div>
    <div style="font-size:12px;color:#555;line-height:1.6;">
      在电脑上运行：<code style="background:#fff;padding:2px 8px;border-radius:4px;font-size:12px;border:1px solid #c8e6c9;">python main.py</code><br/>
      即可自动推送下一篇
    </div>
  </div>

  <div style="text-align:center;margin-top:14px;">
    <span style="font-size:12px;color:#bbb;">每日学习推送</span>
  </div>

</div>"""
    return html


class PushPlus:
    """PushPlus 消息推送客户端"""

    API_URL = "http://www.pushplus.plus/send"

    def __init__(self, token: str, template: str = "html"):
        self.token = token
        self.template = template

    def send(self, title: str, content, topic: str = None, image_keyword: str = None,
             part_num: int = None, total: int = None, recap: str = None,
             is_last: bool = False, series_title: str = None, next_title: str = None,
             page_url: str = None) -> bool:
        """
        发送消息到微信

        Args:
            title: 消息标题
            content: 消息内容（可以是 str 或 dict 结构化数据）
            topic: 群组话题编码（可选）
            image_keyword: 配图关键词
            part_num: 当前片段序号（连载模式）
            total: 总片段数（连载模式）
            recap: 前情提要
            is_last: 是否最后一篇
            series_title: 连载总标题

        Returns:
            bool: 是否发送成功
        """
        # 如果 content 是 dict，渲染为 HTML
        if isinstance(content, dict):
            content = render_html(
                content, image_keyword or "learning",
                part_num=part_num, total=total, recap=recap,
                is_last=is_last, series_title=series_title,
                next_title=next_title, page_url=page_url,
            )
            template = "html"
        else:
            template = self.template

        payload = {
            "token": self.token,
            "title": title,
            "content": content,
            "template": template,
        }
        if topic:
            payload["topic"] = topic

        try:
            resp = requests.post(self.API_URL, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 200:
                logger.info(f"推送成功: {title}")
                return True
            else:
                logger.error(f"推送失败: {data.get('msg', '未知错误')}")
                return False

        except requests.RequestException as e:
            logger.error(f"请求异常: {e}")
            return False

    def test(self) -> bool:
        """发送测试消息"""
        return self.send(
            title="🎉 每日学习推送 - 测试",
            content={
                "title": "测试成功",
                "sections": [
                    {"heading": "PushPlus 连接", "body": "如果你看到这条消息，说明 PushPlus 配置正确。"}
                ],
                "case": "",
                "quote": "一切就绪，开始学习之旅！"
            },
            image_keyword="celebration"
        )
