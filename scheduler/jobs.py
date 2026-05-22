"""定时任务 — APScheduler 周期性执行灵感生成和论文推荐"""

from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.logger import logger

_scheduler: BackgroundScheduler | None = None


def init_scheduler():
    """初始化并启动定时任务调度器"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.start()
    logger.info("定时任务调度器已启动")
    return _scheduler


def schedule_weekly_jobs():
    """注册每周定时任务"""
    sched = init_scheduler()

    # 每周一上午 9:07 生成灵感（避开整点高峰）
    sched.add_job(
        _weekly_idea_generation,
        CronTrigger(day_of_week="mon", hour=9, minute=7),
        id="weekly_ideas",
        name="每周灵感生成",
        replace_existing=True,
    )

    # 每周一上午 9:17 推荐论文
    sched.add_job(
        _weekly_recommendation,
        CronTrigger(day_of_week="mon", hour=9, minute=17),
        id="weekly_recommend",
        name="每周论文推荐",
        replace_existing=True,
    )

    logger.info("已注册每周定时任务: 周一 9:07 灵感, 9:17 推荐")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时任务调度器已停止")


def _weekly_idea_generation():
    logger.info("=== 执行每周灵感生成 ===")
    try:
        from idea_generator.brainstormer import generate_ideas
        ideas = generate_ideas(save=True)
        logger.info(f"已生成 {len(ideas)} 个灵感")
    except Exception as e:
        logger.error(f"每周灵感生成失败: {e}")


def _weekly_recommendation():
    logger.info("=== 执行每周论文推荐 ===")
    try:
        from recommender.arxiv_fetcher import search_by_keywords, search_top_venues
        from recommender.ranker import rank_by_interest, generate_recommendation_reason
        from database.repository import PaperRepository

        all_papers = search_by_keywords()
        all_papers += search_top_venues()

        ranked = rank_by_interest(all_papers, top_k=15)

        with PaperRepository() as repo:
            for p in ranked:
                reason = generate_recommendation_reason(p)
                repo.add_recommendation(
                    arxiv_id=p.get("arxiv_id", ""),
                    title=p.get("title", ""),
                    authors=", ".join(p.get("authors", [])[:5]),
                    year=p.get("year"),
                    abstract=p.get("abstract", "")[:500],
                    venue=p.get("venue", ""),
                    reason=reason,
                )
            repo.commit()

        logger.info(f"已推荐 {len(ranked)} 篇论文")
    except Exception as e:
        logger.error(f"每周论文推荐失败: {e}")
