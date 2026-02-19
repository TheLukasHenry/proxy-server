"""Scheduled task manager using APScheduler."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Callable, Any
import httpx
import logging

from config import settings

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

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": getattr(job, "name", job.id),
            "next_run": str(getattr(job, "next_run_time", None)),
            "trigger": str(job.trigger),
        })
    return jobs


def trigger_job(job_id: str) -> dict:
    """
    Manually trigger a scheduled job immediately.

    Returns:
        Result dict with success status and message.
    """
    if not scheduler:
        return {"success": False, "error": "Scheduler not initialized"}

    job = scheduler.get_job(job_id)
    if not job:
        return {"success": False, "error": f"Job '{job_id}' not found"}

    # Modify the job to run now (next tick)
    job.modify(next_run_time=None)
    # APScheduler: setting next_run_time to None pauses it; instead reschedule
    # Use the scheduler's modify_job to add an immediate run
    try:
        from datetime import datetime, timezone
        scheduler.modify_job(job_id, next_run_time=datetime.now(timezone.utc))
        return {"success": True, "message": f"Job '{job_id}' triggered"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Default scheduled jobs
# ---------------------------------------------------------------------------

SERVICE_ENDPOINTS = {
    "open-webui": f"{settings.openwebui_url}/api/config",
    "mcp-proxy": f"{settings.mcp_proxy_url}/health",
    "n8n": f"{settings.n8n_url}/healthz",
    "webhook-handler": "http://localhost:8086/health",
}


async def _check_service_health(name: str, url: str, timeout: float = 10.0) -> dict:
    """Check a single service health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return {
                "service": name,
                "url": url,
                "status": "healthy" if resp.status_code < 400 else "unhealthy",
                "status_code": resp.status_code,
            }
    except Exception as e:
        return {
            "service": name,
            "url": url,
            "status": "unreachable",
            "error": str(e),
        }


async def daily_health_report(slack_client=None, slack_channel: str = ""):
    """
    Daily health check of all services.

    Runs at noon every day. Checks every registered service endpoint,
    logs the results, and posts to Slack if configured.
    """
    logger.info("=== Daily Health Report ===")
    results = []
    for name, url in SERVICE_ENDPOINTS.items():
        result = await _check_service_health(name, url)
        results.append(result)
        status_emoji = "OK" if result["status"] == "healthy" else "FAIL"
        logger.info(f"  [{status_emoji}] {name}: {result['status']} ({url})")

    healthy = sum(1 for r in results if r["status"] == "healthy")
    total = len(results)
    logger.info(f"=== Health Report: {healthy}/{total} services healthy ===")

    # Post to Slack if configured
    if slack_client and slack_channel:
        lines = [f"*Service Health Report* ({healthy}/{total} healthy)\n"]
        for r in results:
            emoji = "white_check_mark" if r["status"] == "healthy" else "x"
            lines.append(f":{emoji}: {r['service']}: {r['status']}")
        try:
            await slack_client.post_message(channel=slack_channel, text="\n".join(lines))
        except Exception as e:
            logger.error(f"Failed to post health report to Slack: {e}")

    return results


async def hourly_n8n_workflow_check():
    """
    Hourly check of active n8n workflows.

    Lists all workflows via the n8n API and logs their status.
    """
    if not settings.n8n_api_key:
        logger.warning("Skipping n8n workflow check: N8N_API_KEY not set")
        return []

    url = f"{settings.n8n_url}/api/v1/workflows"
    headers = {
        "X-N8N-API-KEY": settings.n8n_api_key,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            workflows = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(workflows, list):
                workflows = []

        active = [w for w in workflows if w.get("active", False)]
        inactive = [w for w in workflows if not w.get("active", False)]

        logger.info(f"=== n8n Workflow Check: {len(active)} active, {len(inactive)} inactive ===")
        for wf in active:
            logger.info(f"  [ACTIVE]   {wf.get('name', 'unnamed')} (id={wf.get('id')})")
        for wf in inactive:
            logger.info(f"  [INACTIVE] {wf.get('name', 'unnamed')} (id={wf.get('id')})")

        return {
            "total": len(workflows),
            "active": len(active),
            "inactive": len(inactive),
            "workflows": [
                {"id": w.get("id"), "name": w.get("name"), "active": w.get("active", False)}
                for w in workflows
            ],
        }

    except Exception as e:
        logger.error(f"n8n workflow check failed: {e}")
        return {"error": str(e)}


def register_default_jobs(slack_client=None, slack_channel: str = ""):
    """Register the built-in scheduled jobs."""
    if not scheduler:
        logger.error("Cannot register jobs: scheduler not initialized")
        return

    # Daily health report at noon (12:00)
    add_cron_job(
        func=daily_health_report,
        job_id="daily_health_report",
        cron_expression="0 12 * * *",
        slack_client=slack_client,
        slack_channel=slack_channel,
    )

    # Hourly n8n workflow status check (every hour at :00)
    add_cron_job(
        func=hourly_n8n_workflow_check,
        job_id="hourly_n8n_check",
        cron_expression="0 * * * *",
    )

    job_count = len(scheduler.get_jobs()) if scheduler else 0
    logger.info(f"Registered {job_count} default scheduled jobs")
