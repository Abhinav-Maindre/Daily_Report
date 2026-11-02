import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from env_config import get_pat, get_org

PAT = get_pat()
organization = get_org()
project = "Reference Data Service"

# Get latest build
url = f"https://dev.azure.com/{organization}/{project}/_apis/build/builds?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

if response.status_code != 200:
    print("Failed to fetch builds")
    print(response.text)
    exit()

data = response.json()

latest_build = data["value"][0]

build_id = latest_build["id"]
build_number = latest_build["buildNumber"]

start_time = latest_build["startTime"]
finish_time = latest_build["finishTime"]

start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
finish_dt = datetime.fromisoformat(finish_time.replace("Z", "+00:00"))

duration = finish_dt - start_dt

print("Build ID:", build_id)
print("Build Number:", build_number)
print("Status:", latest_build["status"])
print("Result:", latest_build.get("result"))
print("Duration:", duration)

print("\nDefinition:")
print(latest_build["definition"])

print("\nAvailable Build Keys:")
for key in sorted(latest_build.keys()):
    print(key)