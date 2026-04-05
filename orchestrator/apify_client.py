import requests
from orchestrator.config import APIFY_API_TOKEN


class ApifyError(Exception):
    pass


def run_actor(
    actor_id: str,
    actor_input: dict,
    api_token: str | None = None,
    timeout: int = 180,
) -> list[dict]:
    """
    Run an Apify actor synchronously and return dataset items.

    Uses the run-sync-get-dataset-items endpoint:
    POST /v2/acts/{actorId}/run-sync-get-dataset-items?token=...&timeout=...
    """
    token = api_token or APIFY_API_TOKEN
    # Apify URL format: owner/name → owner~name in path
    actor_slug = actor_id.replace("/", "~")
    url = (
        f"https://api.apify.com/v2/acts/{actor_slug}"
        f"/run-sync-get-dataset-items"
        f"?token={token}&timeout={timeout}"
    )

    try:
        resp = requests.post(url, json=actor_input, timeout=timeout + 10)
    except requests.Timeout:
        raise ApifyError(f"timeout after {timeout}s running {actor_id}")
    except requests.RequestException as e:
        raise ApifyError(f"request error: {e}")

    if not (200 <= resp.status_code < 300):
        raise ApifyError(f"{resp.status_code} from Apify: {resp.text[:200]}")

    try:
        return resp.json() or []
    except (ValueError, requests.exceptions.JSONDecodeError):
        raise ApifyError(f"invalid JSON in response from {actor_id}")
