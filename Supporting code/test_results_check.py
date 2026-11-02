import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
ORG = get_org()
PROJECT = "Reference Data Service"

RUN_ID = 1102044

url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/test/Runs/{RUN_ID}/results?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

print("Status:", response.status_code)

if response.status_code == 200:
    data = response.json()

    print("Count:", data.get("count"))

    print("\nFirst 10 Results:")
    for result in data.get("value", [])[:10]:
        print("Outcome:", result.get("outcome"))
else:
    print(response.text)