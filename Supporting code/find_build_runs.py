import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
ORG = get_org()
PROJECT = "Reference Data Service"

url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/test/runs?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

runs = response.json()["value"]

for run in runs[:20]:
    print("-" * 80)
    print("Run ID:", run.get("id"))
    print("Name:", run.get("name"))
    print("Total:", run.get("totalTests"))
    print("Passed:", run.get("passedTests"))
    print("Created:", run.get("createdDate"))
    print("Completed:", run.get("completedDate"))