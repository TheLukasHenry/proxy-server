"""Scheduled task manager using APScheduler."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and return the scheduler instance."""
    global scheduler
    scheduler = AsyncIOScheduler()
    logger.info("Scheduler initialized")
    return scheduler


def start_scheduler():
    """Start the scheduler."""
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """Shut down the scheduler."""
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


def add_cron_job(
    func: Callable,
    job_id: str,
    cron_expression: str,
    **kwargs: Any
):
    """
    Add a cron-based scheduled job.

    Args:
        func: Async function to call
        job_id: Unique job identifier
        cron_expression: Cron expression (e.g., '0 8 * * *' for 8 AM daily)
        **kwargs: Additional arguments passed to func
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return

    parts = cron_expression.split()
    if len(parts) == 5:
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
    else:
        logger.error(f"Invalid cron expression: {cron_expression}")
        return

    scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        kwargs=kwargs
    )
    logger.info(f"Scheduled job '{job_id}' with cron: {cron_expression}")


def list_jobs() -> list[dict]:
    """List all scheduled jobs."""
    if not scheduler:
        return []

    return [
        {
            "id": job.id,
            "next_run": str(job.next_run_time),
            "trigger": str(job.trigger)
        }
        for job in scheduler.get_jobs()
    ]
