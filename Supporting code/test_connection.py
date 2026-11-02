import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
organization = get_org()
project = "Reference Data Service"

url = f"https://dev.azure.com/{organization}/{project}/_apis/build/builds?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

print("Status Code:", response.status_code)

if response.status_code == 200:
    data = response.json()
    print("Connection Successful!")
    print("Number of builds found:", len(data["value"]))

    if data["value"]:
        latest_build = data["value"][0]
        print("Latest Build ID:", latest_build["id"])
        print("Build Number:", latest_build["buildNumber"])
else:
    print(response.text)