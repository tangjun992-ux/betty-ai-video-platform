#!/usr/bin/env python3
"""
Betty full-stack boot orchestrator (WSL-safe).
Run BACKGROUND + notify_on_complete:
    terminal(command="python3 scripts/boot.py", background=True, notify_on_complete=True)

Encodes the betty-platform-ops WSL pitfalls:
  - uvicorn started with `python -u` (unbuffered) + logs to a FILE (no stdout-buffer deadlock)
  - NEVER foreground-curls a local service (urllib only -> no D-state zombie)
  - kills ONLY stale backend+celery, NEVER the :3000 frontend (that's AutoVideo)
  - clears __pycache__ so app.main picks the complete router, not stale bytecode
  - waits on log "Application startup complete" with early-exit on error patterns
  - spawns dedicated collector worker for VIS (queue: collector_q, concurrency=2)
Ports: backend 8000, redis 6379, Betty frontend 3200 (3000 = AutoVideo).
"""
import subprocess, time, os, glob, shutil, urllib.request, urllib.error, socket

BACKEND = "/home/tom/ai-video-platform/backend"
FE = "/home/tom/ai-video-platform/frontend"

def log(m): print(m, flush=True)

# ---- 0. resolve venv python (with fallbacks) ----
PY = f"{BACKEND}/.venv/bin/python"
if not os.path.exists(PY):
    for alt in [f"{BACKEND}/venv/bin/python",
                "/home/tom/ai-video-platform/.venv/bin/python",
                "/home/tom/ai-video-platform/venv/bin/python"]:
        if os.path.exists(alt):
            PY = alt; break
log(f"PY={PY} exists={os.path.exists(PY)}")
log(f"app.main={'yes' if os.path.exists(BACKEND+'/app/main.py') else 'NO'}")
cel = [p for p in ['celery_app.py','app/celery_app.py'] if os.path.exists(os.path.join(BACKEND,p))]
log(f"celery_app candidates={cel}")

def port_open(p, t=2):
    s=socket.socket(); s.settimeout(t)
    try: s.connect(("127.0.0.1",p)); s.close(); return True
    except Exception: return False

def http(url, t=10):
    try:
        with urllib.request.urlopen(url, timeout=t) as x:
            return x.status, x.read(300).decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)[:80]

# ---- 1. kill stale backend/celery only (NOT the 3000 frontend = AutoVideo) ----
for pat in ["uvicorn app.main", "celery -A celery_app", "celery_app worker"]:
    subprocess.run(["pkill","-9","-f",pat], timeout=8)
time.sleep(2)

# ---- 2. clear stale bytecode (avoids the __init__ stale-router trap) ----
for d in glob.glob(BACKEND+"/**/__pycache__", recursive=True):
    shutil.rmtree(d, ignore_errors=True)
log("cleared __pycache__")

def spawn(cmd, cwd, logf, env_extra=None):
    env=os.environ.copy(); env["PYTHONPATH"]="."; env["LOCAL_MODE"]="true"
    if env_extra: env.update(env_extra)
    return subprocess.Popen(cmd, cwd=cwd, stdout=open(logf,"w"),
        stderr=subprocess.STDOUT, env=env, start_new_session=True)  # survives script exit

# ---- 3/4/5/5b. spawn services ----
spawn([PY,"-u","-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000","--log-level","info"],
      BACKEND, "/tmp/betty_be.log");      log("spawned uvicorn :8000")
spawn([PY,"-m","celery","-A","celery_app","worker","-Q","video_q,image_q,pipeline_q,celery","--concurrency=4","--loglevel=info"],
      BACKEND, "/tmp/betty_celery.log");   log("spawned celery")
spawn([PY,"-m","celery","-A","celery_app","worker","-Q","collector_q","--concurrency=2","--loglevel=info","-n","collector@%h"],
      BACKEND, "/tmp/betty_collector.log"); log("spawned collector worker")
if not port_open(3200):
    spawn([f"{FE}/node_modules/.bin/next","dev","-p","3200"], FE, "/tmp/betty_fe.log",
          {"NEXT_PUBLIC_API_URL":"http://localhost:8000/api/v1","PORT":"3200"}); log("spawned next dev :3200")
else:
    log("frontend 3200 already up")

# ---- 6. wait for backend ready (poll log; early-exit on errors) ----
ok=False; blog=""
for _ in range(60):  # up to 120s
    time.sleep(2)
    try:
        with open("/tmp/betty_be.log") as f: blog=f.read()
    except FileNotFoundError: blog=""
    if "Application startup complete" in blog: ok=True; break
    if any(e in blog for e in ("Traceback","Error loading ASGI","ModuleNotFoundError")):
        log("!!! backend error:"); log(blog[-1500:]); break

s,_  = http("http://localhost:8000/api/v1/models/")
s2,_ = http("http://localhost:8000/openapi.json")
s3,_ = http("http://localhost:3200/", t=8)
try:
    with open("/tmp/betty_celery.log") as f: clog=f.read()
    cstate = "ready" if ("ready." in clog or "celery@" in clog) else ("error" if "Traceback" in clog else "starting")
except FileNotFoundError:
    cstate="no-log"
try:
    with open("/tmp/betty_collector.log") as f: vlog=f.read()
    vstate = "ready" if ("ready." in vlog or "celery@" in vlog) else ("error" if "Traceback" in vlog else "starting")
except FileNotFoundError:
    vstate="no-log"

log("="*40)
log(f"RESULT backend_ready={ok or s==200} models_http={s} openapi={s2} frontend3200={s3} celery={cstate} collector={vstate}")
if not (ok or s==200):
    log("---- backend log tail ----"); log(blog[-1800:] if blog else "(empty log)")
