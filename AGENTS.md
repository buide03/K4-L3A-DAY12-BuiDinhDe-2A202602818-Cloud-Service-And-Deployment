# Repository Guidelines

## Objective, Sources & Workflow

Target **100/100 through verified implementation and real evidence**. This is an individual Python 3.11+ deployment lab using FastAPI, Redis, and an offline mock LLM.

Use `RUBRIC.md` for scoring, `CHECKPOINTS.md` for checkpoint outcomes and “Cần hiểu” topics, `LAB_GUIDE.md` for implementation guidance, `SUBMISSION.md` for submission requirements, and `RULES.md` for academic integrity and security. Match existing source contracts and supplied tests. If documentation and observed behavior differ, explain the discrepancy rather than silently changing the grading contract.

Work CP0–CP5 in order: inspect requirements, implement, run checkpoint tests, verify actual behavior, record evidence for reflections, explain the concepts, then commit. Report failures, skips, and blockers accurately. During the timed lab, record a blocker and seek Lab Coach help after ten minutes; return to incomplete work before claiming completion.

| Deliverable | Points | Completion evidence |
|---|---:|---|
| CP1: configuration, health, logging | 15 | CP1 tests and real health/log output |
| CP2: containers | 15 | CP2 tests, actual build/run, image size |
| CP3: API security | 20 | CP3 tests and authentication/limit behavior |
| CP4: reliability | 20 | CP4 tests, shared history and shutdown checks |
| CP5: cloud deployment | 15 | HTTPS service, CP5 tests, deployment evidence |
| Reflections | 15 | Ten personal, observation-based answers |
| Optional CI/CD | +10 | Passing bonus tests, real workflow and badge |

Final score is capped at 100. Local fallback limits CP5 to 9/15. Nginx/load balancing earns no separate bonus.

## Project Structure & Coding Conventions

- `app/`: settings, logging, authentication, rate limiting, budgets, Redis storage, lifecycle, and FastAPI endpoints.
- `utils/mock_llm.py`: offline LLM; no external provider key is needed.
- `tests/test_cp1.py` through `test_cp5.py`, `test_bonus_cicd.py`, and `conftest.py`: supplied checks and fixtures using pytest, HTTPX, and fakeredis.
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`: container packaging; `nginx/nginx.conf`: optional proxy.
- `railway.toml`, `render.yaml`: platform configuration. `DEPLOYMENT.md`, `screenshots/`, `exercises.md`: submission evidence. `grade.py`: local grader.

Follow PEP 8, four-space indentation, type hints, snake_case modules/functions, PascalCase classes, and UPPER_SNAKE_CASE constants/environment variables. Name new tests `test_<behavior>_<expected_result>` in the relevant suite. No formatter, linter, or coverage threshold is configured. Preserve public signatures, dependency providers, fixtures, supplied tests, and `grade.py`; never weaken checks to obtain points.

## CP0 — Environment & Baseline

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Only when .env does not already exist:
cp .env.example .env
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. Set a privately generated `AGENT_API_KEY`; never expose it in evidence. Start Redis with `docker compose up -d redis` and inspect `docker compose ps`. `REDIS_URL=fake://` is a temporary local/testing option, never a production or multi-instance substitute.

Run `pytest tests/ -v -m "not docker"`. Failures from unimplemented code are expected; resolve import and environment errors first. This marker excludes Docker-marked checks only, so deployment/network checks can still fail before CP5 or bonus completion.

## CP1 — 12-Factor Configuration, Logging & Liveness

Implement `Settings` in `app/config.py` with the existing `.env` loading and cached `get_settings()`:

| Field / environment variable | Type | Default |
|---|---|---|
| `port` / `PORT` | int | 8000 |
| `agent_api_key` / `AGENT_API_KEY` | str | Required; no default |
| `redis_url` / `REDIS_URL` | str | `redis://localhost:6379/0` |
| `rate_limit_per_minute` / `RATE_LIMIT_PER_MINUTE` | int | 10 |
| `monthly_budget_usd` / `MONTHLY_BUDGET_USD` | float | 10.0 |
| `log_level` / `LOG_LEVEL` | str | `INFO` |

Missing required configuration must fail at startup; environment-specific values must not require source edits.

`log_event()` emits and returns one JSON line containing `event`, lowercase `level`, UTC ISO timestamp, and additional fields. Preserve Unicode; do not pretty-print or log credentials.

`GET /health` returns 200 with `status`, `service`, and `version`, without Redis calls or dependency injection that opens external connections. During shutdown return 503 with `status: shutting_down`.

Verify with `pytest tests/test_cp1.py -v`, `uvicorn app.main:app --reload --port 8000`, and a health request from another terminal. Explain code versus configuration, fail-fast behavior, structured logs, and dependency-independent liveness.

## CP2 — Container Packaging & Networking

- Build with a slim multi-stage Dockerfile. Install dependencies before copying application source; copy installed artifacts into runtime. Include both `app/` and `utils/`; keep compilers out of runtime and run as a non-root user.
- Keep the final image below 500MB. Record original single-stage size before replacing it, then measure the final image and observe rebuild caching for reflection questions.
- Bind Uvicorn to `0.0.0.0`, read `${PORT:-8000}`, and make healthchecks use the same port. Ensure the startup process forwards shutdown signals to Uvicorn, for example by using `exec` in a shell command.
- Exclude `.env`, `__pycache__`, `.git`, `.venv`, and tests from the build context. Retain `app`, `utils`, and `requirements.txt`.
- Compose must provide `agent` and `redis`, build the agent image, publish its local port, declare the Redis dependency, and include healthchecks. Interpolate `${AGENT_API_KEY}`; use `redis://redis:6379/0` inside Compose, not localhost.

```bash
pytest tests/test_cp2.py -v
docker build -t day12-agent:prod .
docker images day12-agent:prod
docker compose up -d --build
curl -i http://localhost:8000/health
docker compose logs agent
```

`pytest tests/test_cp2.py -v -m "not docker"` is a structural check, not proof that the image builds or runs. Explain layer caching, container networking, non-root execution, and build-context secrecy.

## CP3 — Authentication, Rate Limits & Budgets

- `verify_api_key()` checks `X-API-Key` with `secrets.compare_digest`; missing/incorrect keys return 401. Return `X-User-Id` or the existing `ANONYMOUS_USER` fallback.
- Rate limiting uses per-user Redis sorted sets over 60 seconds. Remove expired entries, count, reject at the limit with 429 and `Retry-After`, then insert a unique timestamp/UUID member and set TTL. Respect the injectable `now`, including zero; concurrent timestamps must not overwrite members.
- Cost keys use `cost:<user>:<YYYY-MM>` in UTC. Missing spend is `0.0`; reject when spend plus estimated cost exceeds budget. Record with `incrbyfloat` and the existing 40-day TTL. Preserve optional `month` arguments.
- Keep `/ask` ordering: authentication → limiter → budget check → history → mock LLM → append user and assistant messages → record actual cost → structured completion log → response.
- Preserve the response contract: `answer`, `user_id`, `history_length` measured before appending, `cost_usd`, and `tokens.in/out`. Preserve question validation at 1–2000 characters and HTTP 422 for invalid bodies.

Run `pytest tests/test_cp3.py -v`; verify missing/wrong key, valid request, budget rejection, sliding-window boundaries, per-user isolation, and repeated timestamps. Explain 401/402/429 and why rate limits and budgets serve different purposes. The lab's spend check is not a reservation system guaranteeing a hard ceiling across concurrent LLM calls.

## CP4 — Shared History, Readiness & Shutdown

Store JSON messages in Redis lists by user. Retain the newest `HISTORY_MAX_MESSAGES` (20), refresh `HISTORY_TTL_SECONDS` (seven days), return history oldest-first, and return an empty list when absent. `ping()` catches exceptions and returns `False`.

`GET /ready` returns 200 with `status: ready, redis: true`, or 503 with `status: not ready, redis: false`; shutdown takes precedence and returns `status: shutting_down`. Redis failure must not break `/health`.

Save existing SIGTERM/SIGINT handlers, set the shutdown flag, and forward to callable previous handlers. Keep signal handling lightweight so Uvicorn can drain requests and exit. Process-local lifecycle flags and cached clients are appropriate; user history, spending, and limits must be shared in Redis.

Run `pytest tests/test_cp4.py -v`. Verify real Redis failure/recovery and graceful termination. For three-instance testing, first resolve fixed host-port conflicts: use a Compose override with distinct/dynamic ports or a single proxy exposing the host port. Then run `docker compose up -d --scale agent=3` with that configuration. Repeated requests for one user must share history across instances; history grows until the configured cap. Record evidence for reflection question 9. Do not assume scaling works with every replica publishing `8000:8000`.

## CP5 — Cloud Deployment & Evidence

Use the chosen platform's configuration and real shared Redis. Configure all six settings appropriately, let the platform supply `PORT`, and keep credentials in its secret store. Inspect build/runtime logs when startup fails. Verify current platform pricing and CLI behavior before provisioning; the guide's plan/pricing examples are not guarantees.

Check HTTPS `/health` and `/ready` return 200, unauthenticated `/ask` returns 401, authenticated requests succeed, and repeated calls enforce rate limits. Set local `DEPLOY_API_KEY` to the deployed service's API key for the authenticated CP5 check; it is not a platform token. Keep `LOCAL_FALLBACK=false` for cloud verification.

Complete `DEPLOYMENT.md` with student identity, repository URL, actual service URL, platform, deployment date, configuration sources, and redacted real outputs. Provide `screenshots/dashboard.png` and `screenshots/health.png`. Remove placeholders. Run `pytest tests/test_cp5.py -v` and the documented curl checks. A shell curl example needs the key in its shell environment; application `.env` loading does not automatically export shell variables.

If cloud deployment is unavailable, document the blocker, set `LOCAL_FALLBACK=true`, run the local stack, and provide actual local evidence. State the 9/15 CP5 cap explicitly; do not report fallback as full cloud completion.

## Bonus — Verified GitHub Actions

After required work, create `.github/workflows/ci.yml`:

- Trigger on pushes and pull requests targeting `main`; checkout, set up Python, and install dependencies.
- Test CP1–CP4 using dummy `AGENT_API_KEY` and `REDIS_URL=fake://`. Exclude CP5 and bonus tests from this job to avoid deployment dependency and badge self-reference.
- Build the Docker image on the runner. Deploy must declare `needs: [test, build]` and run only on a push to `main`, never on pull requests.
- Store deployment tokens/hooks in GitHub Secrets and public URLs in Variables. Pin action versions; do not use moving `@main` references.
- Run a post-deploy smoke check using `curl -fsS` with bounded readiness retries. A successful deployment command alone is insufficient evidence.
- Add the real workflow badge to README, verify an actual passing run, then run `pytest tests/test_bonus_cicd.py -v` locally.

## Completion, Commits & Safety

Answer all ten reflection questions in the student's own words, using observed logs, measured image sizes/cache behavior, shared-history results, and actual deployment troubleshooting. Never invent errors, screenshots, URLs, measurements, or passing test results.

Commit after each checkpoint using `feat(cp1): ...` or `fix(cp3): ...`. PRs explain behavior changes, relevant issues, validation results, and deployment evidence. Summaries must distinguish completed work from environmental blockers.

Before submission, run `pytest tests/ -v`, `python grade.py`, and `git status --short`; check tracked files for secrets and remaining `NotImplementedError`s in `app/`. Skipped tests do not prove success. Submit a public repository with complete evidence and code the student can explain.

Required name: `K4-L3A-DAY12-BuiDinhDe-2A202602818-CloudServicesAndDeployment`. Verify the actual remote before submission; the previously observed `Cloud-Service-And-Deployment` suffix does not match and risks a five-point deduction.

Never commit `.env`, API keys, private keys, or platform tokens. Keep `.env.example` placeholders nonfunctional. Rotate any exposed secret; deleting it in a later commit does not remove it from history. Use `docker compose down` for normal cleanup; `down -v` deletes Redis volumes and must not be used when preserving lab evidence or data.
