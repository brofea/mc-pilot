# Error Handling

Use typed domain failures and a single FastAPI exception mapping layer.

```python
class AppError(Exception):
    code: str = "internal_error"
    status_code: int = 500

class DependencyUnavailable(AppError):
    code = "dependency_unavailable"
    status_code = 503
```

API errors use one envelope:

```json
{"error":{"code":"dependency_unavailable","message":"Qdrant is not ready","request_id":"...","details":{}}}
```

- Validate untrusted input at boundaries with Pydantic.
- Raise domain errors from services; do not raise `HTTPException` outside `api/` or `admin/`.
- Preserve the original exception with `raise ... from exc` and log once at the handling boundary.
- Expected degradation is a state, not an exception: no game process means `disconnected`; no index means `not_ready`.
- External failures have explicit timeouts and bounded retries. Never retry invalid input or hash mismatches.
- User messages are safe and concise; internal exception strings never cross the API boundary.

Never use bare `except`, silent `except Exception`, or HTTP 200 responses containing hidden failures.
