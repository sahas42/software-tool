import os
from typing import Optional
from celery_app import celery_app
from src.compliance_checker.models import UsageRules
from src.audit import analyze_advanced

@celery_app.task(bind=True, name="worker.analyze_codebase")
def analyze_codebase_task(
    self,
    rules_dict: dict,
    codebase: dict,
    api_key: str,
    repo_id: str = "default_repo",
    embed_model: str = "jina",
    use_hyde: bool = True
):
    """
    Celery task to analyze the codebase for compliance violations.
    Sends progress state up to Redis for the WebSocket to consume.
    """
    def progress_reporter(progress: int, status_msg: str):
        if self.is_aborted():  # Check if revoked
            raise Exception("Task cancelled by user")
        self.update_state(state="PROGRESS", meta={"progress": progress, "status": status_msg})

    try:
        if self.is_aborted():
            raise Exception("Task cancelled by user")
        
        progress_reporter(5, "Task starting...")
        
        rules = UsageRules(**rules_dict)
        
        # We assume the codebase content mapping {filepath: content} is passed explicitly here
        if not codebase:
            progress_reporter(100, "Error: No source files found")
            return {"error": "No source files found."}

        report = analyze_advanced(
            rules=rules,
            codebase=codebase,
            api_key=api_key,
            repo_id=rules.dataset.name,  # Use dataset name as a default repo context if none provided
            embed_model=embed_model,
            use_hyde=use_hyde,
            progress_callback=progress_reporter
        )
        
        progress_reporter(100, "Completed")
        return report.model_dump()
        
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e), "status": "Task failed"})
        raise e
