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

test_url = f"https://dev.azure.com/{organization}/{project}/_apis/testresults/resultsummarybybuild?buildId={build_id}&api-version=7.1-preview.1"

test_response = requests.get(
    test_url,
    auth=HTTPBasicAuth("", PAT)
)

print("Status:", test_response.status_code)

if test_response.status_code == 200:
    data = test_response.json()

    print("Type:", type(data))
    print("Keys:", list(data.keys()))

runs_url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs?api-version=7.1"

runs_response = requests.get(
    runs_url,
    auth=HTTPBasicAuth("", PAT)
)

print("Runs API Status:", runs_response.status_code)

if runs_response.status_code == 200:
    runs_data = runs_response.json()

    print("Total Test Runs:", runs_data["count"])

    if runs_data["count"] > 0:
        latest_run = runs_data["value"][0]

        print("Run ID:", latest_run["id"])
        print("Run Name:", latest_run["name"])
        print("Passed:", latest_run.get("passedTests"))
        print("Incomplete:", latest_run.get("incompleteTests"))
        print("Not Applicable:", latest_run.get("notApplicableTests"))
        print("Total:", latest_run.get("totalTests"))