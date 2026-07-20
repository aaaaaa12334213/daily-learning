"""
每日学习推送 - 主程序
用法:
    python main.py                          # 连载模式：继续上次的进度推送下一篇
    python main.py --book "书名"             # 开始新书的连载
    python main.py --book "书名" --chapter "一"  # 开始指定章节
    python main.py --test                   # 测试 PushPlus 连接
    python main.py --daemon                 # 定时模式（每天定时推送）
    python main.py --reset                  # 重置进度
"""

import sys
import time
import logging
import subprocess
from pathlib import Path

import yaml

from pusher import PushPlus
from content_generator import ContentGenerator
from progress import ProgressTracker
from pages_generator import save_page

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = Path(__file__).parent

# GitHub Pages 配置
GITHUB_USER = "aaaaaa12334213"
GITHUB_REPO = "daily-learning"
PAGES_BASE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}"


def load_config() -> dict:
    """加载配置文件"""
    config_path = BASE_DIR / "config.yaml"
    if not config_path.exists():
        logger.error("配置文件不存在，请复制 config.yaml 并填写你的 token")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def push_series(config: dict, book: str = None, chapter: str = None):
    """
    连载推送逻辑：
    1. 如果有进行中的连载 → 继续推下一篇
    2. 如果指定了新书 → 生成新连载并推第一篇
    3. 如果都没 → 提示用户指定书籍
    """
    pusher = PushPlus(token=config["pushplus"]["token"])
    ai_cfg = config["ai"]
    generator = ContentGenerator(
        api_base=ai_cfg["api_base"],
        api_key=ai_cfg["api_key"],
        model=ai_cfg["model"]
    )
    content_cfg = config["content"]
    length = content_cfg.get("length", "中")

    tracker = ProgressTracker()

    # 情况1：指定了新书 → 生成新连载
    if book:
        logger.info(f"开始新连载: 《{book}》{'第' + chapter + '章' if chapter else ''}")
        series = generator.generate_series(book=book, chapter=chapter, length=length)

        if series["total"] == 0:
            logger.error("连载生成失败")
            return

        # 保存连载到进度
        # 解析章节号为数字
        chapter_num = 0
        cn_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
        if chapter and chapter in cn_map:
            chapter_num = cn_map[chapter]
        tracker.start_series(
            book=book,
            chapter=chapter or "全",
            parts=series["parts"],
            total=series["total"],
            chapter_num=chapter_num,
        )

        # 推第一篇
        part = tracker.get_next_part()
        if part:
            next_title = tracker.peek_next_title()
            _send_part(pusher, part, series["title"], next_title=next_title, tracker=tracker)

    # 情况2：有进行中的连载 → 继续
    elif tracker.data["status"] == "reading":
        logger.info(f"继续连载: 《{tracker.current_book}》")
        part = tracker.get_next_part()
        if part:
            next_title = tracker.peek_next_title()
            _send_part(pusher, part, next_title=next_title, tracker=tracker)
        else:
            # 全部读完，发总结
            _send_summary(pusher, tracker, generator, config)

    # 情况3：该发总结了
    elif tracker.get_summary_flag():
        logger.info("发送章节总结...")
        _send_summary(pusher, tracker, generator, config)

    # 情况4：没有进行中的连载，也没指定新书
    else:
        logger.info("当前没有进行中的连载，请用 --book 指定一本书开始学习")
        logger.info("例如: python main.py --book \"中医内科学评讲\" --chapter \"一\"")


def _git_push(message: str):
    """提交并推送到 GitHub"""
    try:
        subprocess.run(["git", "add", "pages/"], cwd=str(BASE_DIR), check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=str(BASE_DIR), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), check=True)
        logger.info("✅ 已推送到 GitHub")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git 推送失败: {e}")


def _send_part(pusher: PushPlus, part: dict, series_title: str = None, next_title: str = None, tracker: ProgressTracker = None):
    """推送一个片段"""
    title = f"📚 {part['book']} · 第{part['chapter']}章"
    if series_title:
        title = f"📚 {series_title}"

    content_data = part["content"]
    image_keyword = content_data.get("image_keyword", "learning")
    part_num = part["part_num"]
    total = part["total"]
    is_last = part.get("is_last", False)

    # 生成当前篇的网页
    cn = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
    ch_num = cn.get(part["chapter"], part_num)
    current_filename = f"ch{ch_num}-part{part_num}.html"
    current_url = f"{PAGES_BASE_URL}/pages/{current_filename}"

    # 下一篇网页 URL
    next_url = None
    if not is_last:
        next_filename = f"ch{ch_num}-part{part_num + 1}.html"
        next_url = f"{PAGES_BASE_URL}/pages/{next_filename}"

    # 上一篇网页 URL
    prev_url = None
    if part_num > 1:
        prev_filename = f"ch{ch_num}-part{part_num - 1}.html"
        prev_url = f"{PAGES_BASE_URL}/pages/{prev_filename}"

    # 保存网页
    save_page(
        filename=current_filename,
        data=content_data,
        part_num=part_num,
        total=total,
        recap=part.get("recap"),
        is_last=is_last,
        series_title=series_title,
        next_title=next_title,
        next_url=next_url,
        prev_url=prev_url,
    )

    # 推送到 GitHub
    _git_push(f"推送: {part['book']} 第{part['chapter']}章 第{part_num}/{total}篇")

    pusher.send(
        title=title,
        content=content_data,
        image_keyword=image_keyword,
        part_num=part_num,
        total=total,
        recap=part.get("recap"),
        is_last=is_last,
        series_title=series_title,
        next_title=next_title,
        page_url=current_url,
    )

    if is_last:
        logger.info("📖 本章已推送完毕，下次将发送总结回顾")
    else:
        logger.info(f"✅ 推送完成：第 {part_num}/{total} 篇")
        logger.info(f"🌐 网页: {current_url}")


def _send_summary(pusher: PushPlus, tracker: ProgressTracker, generator: ContentGenerator, config: dict):
    """发送章节总结回顾"""
    logger.info("生成章节总结...")

    # 让 AI 生成总结
    prompt = f"""请为《{tracker.current_book}》第{tracker.current_chapter}章写一份精简的总结回顾。

要求：
1. 用 Markdown 格式
2. 包含：本章核心要点（3-5条）、关键概念回顾、一句总结金句
3. 语言简洁有力，适合快速复习

请严格按以下 JSON 格式输出：
{{
  "title": "章节总结标题",
  "sections": [{{"heading": "小标题", "body": "内容"}}],
  "case": "",
  "quote": "总结金句",
  "image_keyword": "英文关键词"
}}"""

    try:
        from openai import OpenAI
        ai_cfg = {
            "api_base": generator.client.base_url.__str__().rstrip("/chat/completions"),
            "api_key": generator.client.api_key,
        }
        client = OpenAI(base_url=ai_cfg["api_base"], api_key=ai_cfg["api_key"])
        resp = client.chat.completions.create(
            model=generator.model,
            messages=[
                {"role": "system", "content": "你是中医学习助手，输出合法JSON。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
        )
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        import json
        summary = json.loads(raw)

        pusher.send(
            title=f"📚 《{tracker.current_book}》第{tracker.current_chapter}章 · 总结",
            content=summary,
            image_keyword=summary.get("image_keyword", "summary"),
            series_title=f"《{tracker.current_book}》第{tracker.current_chapter}章",
        )

        # 自动进入下一章
        if tracker.data.get("auto_continue", True):
            next_info = tracker.get_next_chapter_info()
            logger.info(f"✅ 总结完成，自动进入下一章: 第{next_info['chapter']}章")

            content_cfg = config["content"]
            length = content_cfg.get("length", "长")
            series = generator.generate_series(
                book=next_info["book"],
                chapter=next_info["chapter"],
                length=length,
            )

            if series["total"] > 0:
                tracker.start_series(
                    book=next_info["book"],
                    chapter=next_info["chapter"],
                    parts=series["parts"],
                    total=series["total"],
                    chapter_num=next_info["chapter_num"],
                )
                part = tracker.get_next_part()
                if part:
                    _send_part(pusher, part, series["title"], tracker=tracker)
                logger.info(" 下一章第一篇已推送")
            else:
                logger.error("下一章生成失败")
        else:
            tracker.reset()
            logger.info("✅ 总结推送完成，进度已重置")

    except Exception as e:
        logger.error(f"总结生成失败: {e}")


def test_connection(config: dict):
    """测试 PushPlus 连接"""
    pusher = PushPlus(token=config["pushplus"]["token"])
    if pusher.test():
        logger.info("✅ 测试成功！请检查微信是否收到消息")
    else:
        logger.error("❌ 测试失败，请检查 token 是否正确")


def daemon_mode(config: dict):
    """定时推送模式"""
    schedule = config.get("schedule", {})
    times = schedule.get("times", schedule.get("time", "08:00"))
    if isinstance(times, str):
        times = [times]
    logger.info(f"🕐 定时模式启动，每天 {', '.join(times)} 推送")

    pushed_today = set()

    while True:
        now = time.strftime("%H:%M")
        today = time.strftime("%Y-%m-%d")

        if now in times and today + now not in pushed_today:
            logger.info(f"到达推送时间 {now}，开始推送...")
            push_series(config)
            pushed_today.add(today + now)
            time.sleep(61)
        else:
            # 跨天时清空记录
            if now == "00:01":
                pushed_today.clear()
            time.sleep(30)


def main():
    config = load_config()

    if "--test" in sys.argv:
        test_connection(config)
    elif "--daemon" in sys.argv:
        daemon_mode(config)
    elif "--reset" in sys.argv:
        tracker = ProgressTracker()
        tracker.reset()
        logger.info("✅ 进度已重置")
    else:
        # 解析 --book 和 --chapter 参数
        book = None
        chapter = None
        if "--book" in sys.argv:
            idx = sys.argv.index("--book")
            if idx + 1 < len(sys.argv):
                book = sys.argv[idx + 1]
        if "--chapter" in sys.argv:
            idx = sys.argv.index("--chapter")
            if idx + 1 < len(sys.argv):
                chapter = sys.argv[idx + 1]
        push_series(config, book=book, chapter=chapter)


if __name__ == "__main__":
    main()
