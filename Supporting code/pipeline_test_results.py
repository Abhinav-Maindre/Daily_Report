import requests
from requests.auth import HTTPBasicAuth
import json
from env_config import get_pat, get_org

PAT = get_pat()
ORG = get_org()
PROJECT = "Reference Data Service"

url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/test/runs?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

response.raise_for_status()

runs = response.json()["value"]

print("Total Runs:", len(runs))

if runs:
    print(json.dumps(runs[0], indent=2))