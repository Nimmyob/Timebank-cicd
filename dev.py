"""Run everything locally without Docker/Postgres (SQLite). http://localhost:8080"""
import os, subprocess, sys, requests
from flask import Flask, Response, request, send_from_directory

root = os.path.dirname(os.path.abspath(__file__))
procs = [
    subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run", "-p", "5001"], cwd=f"{root}/skills"),
    subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run", "-p", "5002"], cwd=f"{root}/ledger",
                     env={**os.environ, "SKILLS_URL": "http://localhost:5001"}),
]
app = Flask(__name__)
PORTS = {"skills": 5001, "ledger": 5002}

@app.route("/")
def index(): return send_from_directory(f"{root}/web", "index.html")

@app.route("/api/<svc>/<path:p>", methods=["GET", "POST", "DELETE"])
def proxy(svc, p):
    r = requests.request(request.method, f"http://localhost:{PORTS[svc]}/{p}", params=request.args,
                         data=request.get_data(), headers={"Content-Type": request.content_type or ""})
    return Response(r.content, r.status_code, {"Content-Type": r.headers.get("Content-Type", "application/json")})

if __name__ == "__main__":
    try: app.run(port=8080)
    finally: [p.terminate() for p in procs]
