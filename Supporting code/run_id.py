import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
organization = get_org()
project = "Reference Data Service"

url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

print("Status:", response.status_code)

if response.status_code == 200:
    data = response.json()

    print("Count:", data.get("count"))

    for run in data.get("value", [])[:5]:
        print("-" * 50)
        print("Run ID:", run.get("id"))
        print("Name:", run.get("name"))
        print("State:", run.get("state"))
        print("Total Tests:", run.get("totalTests"))