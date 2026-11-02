import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
organization = get_org()

projects = [
    "Reference Data Service",
    "Tatooine",
    "Dantooine"
]

for project in projects:

    print(f"\n{'='*60}")
    print(f"PROJECT: {project}")
    print(f"{'='*60}")

    url = f"https://dev.azure.com/{organization}/{project}/_apis/build/definitions?api-version=7.1"

    response = requests.get(
        url,
        auth=HTTPBasicAuth("", PAT)
    )

    if response.status_code != 200:
        print("Failed:", response.status_code)
        continue

    data = response.json()

    for definition in data.get("value", []):
        print(
            f"ID: {definition['id']} | "
            f"Name: {definition['name']}"
        )