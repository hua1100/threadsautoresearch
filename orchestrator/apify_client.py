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
    url = (
        f"https://api.apify.com/v2/acts/{actor_id}"
        f"/run-sync-get-dataset-items"
        f"?token={token}&timeout={timeout}"
    )

    try:
        resp = requests.post(url, json=actor_input, timeout=timeout + 10)
    except requests.Timeout:
        raise ApifyError(f"timeout after {timeout}s running {actor_id}")
    except requests.RequestException as e:
        raise ApifyError(f"request error: {e}")

    if resp.status_code != 200:
        raise ApifyError(f"{resp.status_code} from Apify: {resp.text[:200]}")

    return resp.json() or []
