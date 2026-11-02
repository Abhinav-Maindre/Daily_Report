import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
organization = get_org()
project = "Reference Data Service"

run_id = 1102044   # Use one of the run IDs returned

url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs/{run_id}?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

data = response.json()

print("Available Fields:")
for key in sorted(data.keys()):
    print(key)

print("\nRun Statistics:")
print(data.get("runStatistics"))