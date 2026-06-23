import requests

FLOWGUARD_API = "https://flowguard-api-o6xo.onrender.com"

response = requests.post(
    f"{FLOWGUARD_API}/pipeline-runs",
    json={
        "pipeline_id": 1,
        "status": "SUCCESS",
        "duration_seconds": 120,
        "error_message": None
    }
)

print(response.json())