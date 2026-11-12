# TimeBank - a neighbourhood skill exchange where time is the currency

Teach an hour, earn an hour, spend it learning something else. New members start with 3 free hours.

## Architecture (3 tiers, 2 microservices)

| Tier | Component | Details |
|------|-----------|---------|
| 1 Presentation | `web` | Nginx serving the UI; proxies `/api/skills/*` and `/api/ledger/*` |
| 2 Application | `skills` (Flask, :5001) | Catalogue of skill offers (CRUD, search, categories) |
| 2 Application | `ledger` (Flask, :5002) | Members, balances, bookings. Calls `skills` over HTTP to validate an offer, then moves credits atomically |
| 3 Data | `postgres` | StatefulSet + PVC. One database per service (`skills`, `ledger`) |

## Run without Docker (SQLite)
    pip install flask requests && python dev.py     # http://localhost:8080

## Run with Docker Compose
    docker compose up --build                       # http://localhost:8080

## Deploy to Kubernetes (kind / minikube / any cluster)
    # 1. build images
    docker build -t timebank/skills:1.0 skills
    docker build -t timebank/ledger:1.0 ledger
    docker build -t timebank/web:1.0    web
    # 2. make them available to the cluster
    kind load docker-image timebank/skills:1.0 timebank/ledger:1.0 timebank/web:1.0
    #    (minikube: minikube image load <each image>; real cluster: push to your registry and edit image: in k8s/)
    # 3. deploy
    kubectl apply -f k8s/
    kubectl -n timebank get pods -w
    # 4. open it
    kubectl -n timebank port-forward svc/web 8080:80      # http://localhost:8080
    #    or use the Ingress: add "<ingress-ip> timebank.local" to your hosts file

## What the manifests give you
Namespace + Secret (change the DB password!), Postgres StatefulSet with a volume, 2 replicas each of
skills/ledger/web, readiness + liveness probes, resource limits, CPU-based HPAs (needs metrics-server),
an Ingress, and NetworkPolicies so only the app tier can reach the database.

## Ideas to extend
Real login (JWT), ratings after a booking, a third `notifications` service, Prometheus metrics, Helm chart / CI pipeline.

## Tests and CI/CD (GitHub Actions)
Each service has a `test_app.py`. Run them locally:

    cd skills && pip install -r requirements.txt pytest && pytest
    cd ../ledger && pip install -r requirements.txt pytest && pytest

`.github/workflows/ci.yml` runs on every push and pull request:
1. **test** - pytest for `skills` and `ledger`
2. **validate-k8s** - checks every YAML in `k8s/` parses
3. **build-and-push** (only on `main`, after 1 and 2 pass) - builds the 3 Docker images and pushes them to
   GitHub Container Registry as `ghcr.io/<your-username>/timebank-<service>:latest` and `:<commit-sha>`
