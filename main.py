import os
import io
import zipfile
import asyncio
import secrets
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import yaml

from src.compliance_checker.models import UsageRules, DatasetInfo
from src.compliance_checker.pdf_rule_extractor import extract_rules_from_pdf
from src.compliance_checker.codebase_loader import load_codebase
from worker import analyze_codebase_task
from celery_app import celery_app

app = FastAPI(title="ACEP API", description="Agentic Compliance Enforcement Platform")

# ── Session middleware (must be added BEFORE CORSMiddleware) ────────────────
# SESSION_SECRET must be set in .env — any long random string works.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", secrets.token_hex(32)),
    session_cookie="acep_session",
    max_age=60 * 60 * 24,  # 1 day
    same_site="lax",
    https_only=False,  # set True in production with HTTPS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── GitHub OAuth constants ──────────────────────────────────────────────────
GITHUB_CLIENT_ID     = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI  = os.environ.get("GITHUB_REDIRECT_URI", "http://localhost:5001/auth/github/callback")
GITHUB_SCOPES        = "repo read:user"  # `repo` grants access to private repos

BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIR = BASE_DIR / "webapp"

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv", ".tox", "dist", "build", ".pytest_cache"}

def parse_rules_from_yaml(content: str) -> UsageRules:
    raw = yaml.safe_load(content)
    return UsageRules(**raw)

def parse_rules_from_pdf(file_bytes: bytes, api_key: str = "") -> UsageRules:
    """Extract rules from a legal PDF using LLM-powered structured extraction."""
    return extract_rules_from_pdf(file_bytes, api_key=api_key)

def load_from_zip(zip_bytes: bytes, extensions: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            parts = Path(name).parts
            if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
                continue
            if Path(name).suffix in extensions:
                try:
                    content = zf.read(name).decode("utf-8", errors="replace")
                    files[name] = content
                except Exception:
                    pass
    return files

async def load_from_uploaded_files(files_list: List[UploadFile], extensions: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in files_list:
        fname = f.filename
        if Path(fname).suffix in extensions:
            try:
                content = (await f.read()).decode("utf-8", errors="replace")
                result[fname] = content
            except Exception:
                pass
    return result

class AnalysisTaskResponse(BaseModel):
    task_id: str
    status: str


# ═══════════════════════════════════════════════════════════════════════════
# GitHub OAuth Routes
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/auth/github")
async def github_login(request: Request):
    """
    Step 1 – Redirect the user to GitHub's OAuth authorization page.
    A random `state` token is stored in the session to prevent CSRF.
    """
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not configured.")

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state

    params = urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": GITHUB_SCOPES,
        "state": state,
    })
    return RedirectResponse(url=f"https://github.com/login/oauth/authorize?{params}")


@app.get("/auth/github/callback")
async def github_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """
    Step 2 – GitHub redirects here after the user approves.
    Exchange the `code` for an access token, store it in the session,
    then redirect back to the frontend.
    """
    # OAuth error from GitHub (user denied, etc.)
    if error:
        return RedirectResponse(url=f"/?auth_error={error}")

    # CSRF check
    stored_state = request.session.pop("oauth_state", None)
    if not stored_state or stored_state != state:
        return RedirectResponse(url="/?auth_error=state_mismatch")

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id":     GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code":          code,
                "redirect_uri":  GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )

    token_data = token_res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        err_msg = token_data.get("error_description", "no_token")
        return RedirectResponse(url=f"/?auth_error={err_msg}")

    # Fetch basic user info
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
    user_data = user_res.json()

    # Persist in session
    request.session["github_token"]    = access_token
    request.session["github_username"] = user_data.get("login", "")
    request.session["github_avatar"]   = user_data.get("avatar_url", "")

    return RedirectResponse(url="/?auth=success")


@app.get("/auth/status")
async def auth_status(request: Request):
    """Returns whether the user is logged in and their GitHub username."""
    token = request.session.get("github_token")
    if token:
        return {
            "logged_in": True,
            "username":  request.session.get("github_username"),
            "avatar":    request.session.get("github_avatar"),
        }
    return {"logged_in": False, "username": None, "avatar": None}


@app.post("/auth/logout")
async def logout(request: Request):
    """Clear the GitHub OAuth session."""
    request.session.clear()
    return {"message": "Logged out successfully."}


@app.get("/api/repos")
async def list_repos(request: Request):
    """
    Returns the authenticated user's repositories (public + private),
    sorted by most recently pushed.
    Requires the user to be logged in via GitHub OAuth.
    """
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect your GitHub account.")

    repos = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            res = await client.get(
                "https://api.github.com/user/repos",
                params={"per_page": 100, "page": page, "sort": "pushed", "affiliation": "owner,collaborator"},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            )
            batch = res.json()
            if not batch or not isinstance(batch, list):
                break
            repos.extend([
                {
                    "full_name":    r["full_name"],
                    "name":         r["name"],
                    "private":      r["private"],
                    "description":  r.get("description") or "",
                    "html_url":     r["html_url"],
                    "updated_at":   r.get("pushed_at") or r.get("updated_at"),
                }
                for r in batch
            ])
            if len(batch) < 100:
                break
            page += 1

    return {"repos": repos, "total": len(repos)}

@app.post("/api/analyze", response_model=AnalysisTaskResponse)
async def analyze_endpoint(
    request: Request,
    api_key: str = Form(os.environ.get("GEMINI_API_KEY", "")),
    codebase_type: str = Form("github"),
    extensions: str = Form(".py,.js,.ts,.java,.cpp,.c,.go,.rb,.rs"),
    codebase_url: Optional[str] = Form(None),
    codebase_zip: Optional[UploadFile] = File(None),
    codebase_files: Optional[List[UploadFile]] = File(None),
    rules_file: UploadFile = File(...),
    pipeline_type: str = Form("vanilla"),
    embed_model: str = Form("bge"),
    use_hyde: bool = Form(True)
):
    if not api_key:
        return JSONResponse(status_code=400, content={"error": "Gemini API key is required."})

    exts = [e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in extensions.split(",")]

    # Parse rules
    filename = rules_file.filename.lower()
    file_bytes = await rules_file.read()
    try:
        if filename.endswith((".yaml", ".yml")):
            rules = parse_rules_from_yaml(file_bytes.decode("utf-8"))
        elif filename.endswith(".pdf"):
            rules = parse_rules_from_pdf(file_bytes, api_key=api_key)
        else:
            try:
                rules = parse_rules_from_yaml(file_bytes.decode("utf-8", errors="ignore"))
            except Exception:
                rules = parse_rules_from_pdf(file_bytes, api_key=api_key)
    except Exception as e:
        return JSONResponse(status_code=422, content={"error": f"Failed to parse rules file: {e}"})

    # Load codebase
    try:
        if codebase_type == "github":
            if not codebase_url:
                return JSONResponse(status_code=400, content={"error": "GitHub URL is required."})
            # Use OAuth token if the user is logged in (enables private repo access)
            github_token = request.session.get("github_token") if hasattr(request, "session") else None
            if github_token:
                from src.compliance_checker.github_loader import load_private_repo
                codebase = await asyncio.to_thread(load_private_repo, codebase_url, github_token)
            else:
                codebase = await asyncio.to_thread(load_codebase, codebase_url)
        elif codebase_type == "zip":
            if not codebase_zip:
                return JSONResponse(status_code=400, content={"error": "ZIP file is required."})
            codebase = load_from_zip(await codebase_zip.read(), exts)
        elif codebase_type in ("files", "folder"):
            if not codebase_files:
                return JSONResponse(status_code=400, content={"error": "No files uploaded."})
            codebase = await load_from_uploaded_files(codebase_files, exts)
        else:
            return JSONResponse(status_code=400, content={"error": f"Unknown codebase_type: {codebase_type}"})
    except Exception as e:
        return JSONResponse(status_code=422, content={"error": f"Failed to load codebase: {e}"})

    if not codebase:
        return JSONResponse(status_code=422, content={"error": "No source files found. Check file types / extensions."})

    # Submit Celery Task
    repo_id = codebase_url if codebase_type == "github" else "local_upload"
    
    task = analyze_codebase_task.delay(
        rules_dict=rules.model_dump(),
        codebase=codebase,
        api_key=api_key,
        pipeline_type=pipeline_type,
        repo_id=repo_id,
        embed_model=embed_model,
        use_hyde=use_hyde
    )

    return {"task_id": task.id, "status": "PENDING"}

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {"message": f"Task {task_id} cancellation requested."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {e}")

@app.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            res = celery_app.AsyncResult(task_id)
            if res.state == "PENDING":
                progress = 0
                status_msg = "Pending..."
            elif res.state == "PROGRESS":
                progress = res.info.get("progress", 0) if res.info else 0
                status_msg = res.info.get("status", "Processing...") if res.info else "Processing..."
            elif res.state == "SUCCESS":
                progress = 100
                status_msg = "Completed"
            elif res.state == "FAILURE":
                progress = 100
                status_msg = "Failed"
            elif res.state == "REVOKED":
                progress = 0
                status_msg = "Cancelled"
            else:
                progress = 0
                status_msg = res.state

            # Robustly extract error info
            error_val = None
            if res.state == "FAILURE":
                if isinstance(res.info, dict):
                    error_val = res.info.get("error", str(res.result))
                else:
                    error_val = str(res.info) if res.info else str(res.result)

            await websocket.send_json({
                "task_id": task_id,
                "status": res.state,
                "progress": progress,
                "message": status_msg,
                "result": res.result if res.state == "SUCCESS" else None,
                "error": error_val
            })
            
            if res.ready() or res.state == "REVOKED":
                break
            
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for task {task_id}")
    finally:
        # Prevent "close() on closed connection" issues
        try:
            await websocket.close()
        except Exception:
            pass

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    res = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": res.state,
        "result": res.result if res.state == "SUCCESS" else None
    }

# Mount static files for the frontend
app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="webapp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
