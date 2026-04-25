import os
from celery_app import celery_app
from src.compliance_checker.models import UsageRules


@celery_app.task(bind=True, name="worker.analyze_codebase")
def analyze_codebase_task(
    self,
    rules_dict: dict,
    codebase: dict,
    api_key: str,
    pipeline_type: str = "vanilla",
    repo_id: str = "default_repo",
    embed_model: str = "bge",
    use_hyde: bool = True
):
    """
    Celery task to analyze the codebase for compliance violations.
    Sends progress state up to Redis for the WebSocket to consume.
    """
    def progress_reporter(progress: int, status_msg: str):
        self.update_state(state="PROGRESS", meta={"progress": progress, "status": status_msg})

    try:
        progress_reporter(5, "Task starting — loading AI models...")

        rules = UsageRules(**rules_dict)

        if not codebase:
            progress_reporter(100, "Error: No source files found")
            return {"error": "No source files found."}

        if pipeline_type == "advanced":
            # Import here to avoid circular/slow imports at worker startup
            from src.audit import analyze_advanced
            report = analyze_advanced(
                rules=rules,
                codebase=codebase,
                api_key=api_key,
                repo_id=repo_id,
                embed_model=embed_model,
                use_hyde=use_hyde,
                progress_callback=progress_reporter
            )
        else:
            from src.audit import analyze_vanilla
            report = analyze_vanilla(
                rules=rules,
                codebase=codebase,
                api_key=api_key,
                progress_callback=progress_reporter
            )

        progress_reporter(100, "Completed")
        return report.model_dump()

    except Exception as e:
        # Store as plain string — raw exception objects cause Redis deserialization crashes
        error_msg = str(e)
        self.update_state(
            state="FAILURE",
            meta={"error": error_msg, "status": "Task failed", "exc_type": type(e).__name__, "exc_message": error_msg}
        )
        # Re-raise a plain RuntimeError so Celery doesn't try to serialize the original exception
        raise RuntimeError(error_msg)

