import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from env_config import get_pat, get_org

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Candidate locations for Promise to Pay HTML file
PROMISE_TO_PAY_FILE = os.path.join(BASE_DIR, "Promise to Pay.html")

# Excel file path (prioritizes Downloads, falls back to current directory)
DOWNLOADS_EXCEL = os.path.join(os.path.expanduser("~"), "Downloads", "RARS Sanity Test After AWS Lambda.xlsx")
LOCAL_EXCEL = os.path.join(BASE_DIR, "RARS Sanity Test After AWS Lambda.xlsx")
EXCEL_FILE = DOWNLOADS_EXCEL if os.path.exists(DOWNLOADS_EXCEL) else LOCAL_EXCEL

PAT = get_pat()
ORG = get_org()

PIPELINES = [
    {
        "name": "RDS",
        "project": "Reference Data Service",
        "project_id": "da89b102-2508-4bb1-82f8-40b8aa25c04f",
        "definition_id": 648
    },
    {
        "name": "Promise to Pay",
        "project": "Reference Data Service",
        "project_id": "da89b102-2508-4bb1-82f8-40b8aa25c04f",
        "definition_id": 661
    },
    {
        "name": "RARS (V2)",
        "project": "Tatooine",
        "project_id": "72db6f14-8ae1-45d1-b370-091a2d82026f",
        "definition_id": 700
    },
    {
        "name": "LSM",
        "project": "Dantooine",
        "project_id": "e46787cb-d678-412c-8334-a97f1bcfab63",
        "definition_id": 775
    }
]


def get_latest_build(project, definition_id):

    url = (
        f"https://dev.azure.com/{ORG}/{project}"
        f"/_apis/build/builds"
        f"?definitions={definition_id}"
        f"&$top=1"
        f"&api-version=7.1"
    )

    response = requests.get(
        url,
        auth=HTTPBasicAuth("", PAT)
    )

    
    response.raise_for_status()

    return response.json()["value"][0]

promise_to_pay_build_id = None
pipeline_results = {}


print("\nDAILY PIPELINE REPORT")
print("=" * 70)

def get_test_summary(project_id, build_id):

    url = (
        f"https://vstmr.dev.azure.com/{ORG}/{project_id}"
        f"/_apis/testresults/metrics"
        f"?pipelineId={build_id}"
        f"&metricNames=2"
    )

    response = requests.get(
        url,
        auth=HTTPBasicAuth("", PAT)
    )
    
   
    response.raise_for_status()

    data = response.json()
    
    summary_dict = data["resultSummary"]["resultSummaryByRunState"]

    first_key = list(summary_dict.keys())[0]
    summary = summary_dict[first_key]

    total = summary["totalTestCount"]

    outcomes = summary.get(
        "aggregatedResultDetailsByOutcome",
        {}
    )

    passed = outcomes.get(
     	"Passed",
    	{}
    ).get(
    	"count",
    	0
    )

    failed = outcomes.get(
    	"Failed",
   	 {}
    ).get(
    	"count",
   	 0
    )

    others = total - passed - failed

    duration = summary["duration"]

    return {
        "passed": passed,
        "failed": failed,
        "others": others,
        "total": total,
        "duration": duration
    }

def format_pipeline_duration(td):
    total_seconds = int(td.total_seconds())

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return f"{minutes}m {seconds}s"

for pipeline in PIPELINES:

    try:

        build = get_latest_build(
            pipeline["project"],
            pipeline["definition_id"]
        )

        start = datetime.fromisoformat(
            build["startTime"].replace("Z", "+00:00")
        )

        finish = datetime.fromisoformat(
            build["finishTime"].replace("Z", "+00:00")
        )

        duration = finish - start

        print(f"\nProject : {pipeline['name']}")
        print(f"Build ID: {build['id']}")
        print(f"Result  : {build.get('result')}")

        if pipeline["name"] != "Promise to Pay":

            summary = get_test_summary(
                pipeline["project_id"],
                build["id"]
            )
#added now(Optional)
            print(f"Raw Duration: {summary['duration']}")
            print(f"Pipeline Duration: {duration}")
            print(f"Test Duration: {summary['duration']}")

            print(f"Passed  : {summary['passed']}")
            print(f"Failed  : {summary['failed']}")
            print(f"Others  : {summary['others']}")
            print(f"Total   : {summary['total']}")
            print(f"Duration: {summary['duration']}")

            pipeline_results[pipeline["name"]] = {
            "passed": summary["passed"],
            "failed": summary["failed"],
            "others": summary["others"],
            "total": summary["total"],
            "duration": format_pipeline_duration(duration)
            }

        else:
            promise_to_pay_build_id = build["id"]
            print(f"Pipeline Duration: {duration}")
            print("Promise to Pay values will come from Cucumber Report")
            print(f"Promise To Pay Build ID: {promise_to_pay_build_id}")

    except Exception as ex:
        print(f"\nProject : {pipeline['name']}")
        print(f"ERROR   : {ex}")

from bs4 import BeautifulSoup
import re

def download_promise_to_pay_html(attachments):

    for item in attachments["value"]:

        if item["name"] == "Promise to Pay.html":

            download_url = item["_links"]["self"]["href"]

            response = requests.get(
                download_url,
                auth=HTTPBasicAuth("", PAT)
            )

            response.raise_for_status()

            file_path = PROMISE_TO_PAY_FILE

            with open(file_path, "wb") as f:
                f.write(response.content)

            print("\nPromise to Pay HTML downloaded")
            print(f"Downloaded file location: {file_path}")

            return file_path

    # Fallback to local or desktop file if not found in attachments
    fallback_locations = [
        PROMISE_TO_PAY_FILE,
        os.path.join(os.path.expanduser("~"), "OneDrive - Magellan Partners", "Desktop", "Promise to Pay.html"),
        os.path.join(os.path.expanduser("~"), "Desktop", "Promise to Pay.html"),
    ]

    for candidate in fallback_locations:
        if os.path.exists(candidate):
            print(f"\nAttachment not found in build; using existing file at: {candidate}")
            return candidate

    raise Exception("Promise to Pay.html not found in build attachments or local/desktop directories")


def get_cucumber_attachments(project_id, plan_id):

    url = (
        f"https://dev.azure.com/{ORG}/{project_id}"
        f"/_apis/distributedtask/hubs/build/plans/{plan_id}"
        f"/attachments/cucumber.report"
        f"?api-version=7.1"
    )

    response = requests.get(
        url,
        auth=HTTPBasicAuth("", PAT)
    )

    response.raise_for_status()

    return response.json()


print("\n=== PROMISE TO PAY TIMELINE ===")


url = (
    f"https://dev.azure.com/{ORG}/Reference Data Service"
    f"/_apis/build/builds/{promise_to_pay_build_id}/timeline"
    f"?api-version=7.1"
)

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

data = response.json()

if "id" not in data:
    raise Exception("Timeline ID not found")

print("\nTIMELINE ID:")
print(data["id"])


attachments = get_cucumber_attachments(
    "da89b102-2508-4bb1-82f8-40b8aa25c04f",
    data["id"]   # timeline/plan id
)


print("\nATTACHMENTS:")
print(attachments)



html_file = download_promise_to_pay_html(
    attachments
)

with open(
    html_file,
    "r",
    encoding="utf-8",
    errors="ignore"
) as f:
    html = f.read()

# Execution Time
match = re.search(r'Execution Time:\s*([^\n<]+)', html)

duration = match.group(1).strip() if match else ""

soup = BeautifulSoup(html, "html.parser")

cards = soup.find_all("div", class_="card")


results = {}

for card in cards:

    title = card.find("h4")
    value = card.find("h5")

    if title and value:

        title_text = title.get_text(strip=True)
        value_text = value.get_text(strip=True)

        print(title_text, "=", value_text)

        results[title_text] = value_text


if not cards:
    raise Exception(
        "No scenario cards found in Promise To Pay report"
    )


from openpyxl import load_workbook

print(f"\nTarget Excel File: {EXCEL_FILE}")

wb = load_workbook(EXCEL_FILE)
ws = wb["Daily Automation Report"]

report_date = datetime.now().date()

# RDS - Row 3
rds = pipeline_results.get("RDS", {})
ws["B3"] = report_date
ws["B3"].number_format = "dd-mm-yyyy"
ws["C3"] = "RDS"
ws["D3"] = "System Test"
ws["E3"] = rds.get("passed", 0)
ws["F3"] = rds.get("failed", 0)
ws["G3"] = rds.get("others", 0)
ws["H3"] = rds.get("total", 0)
ws["I3"] = rds.get("duration", "")



# Promise To Pay - Row 4
print("Duration:", duration)
ws["B4"] = report_date
ws["B4"].number_format = "dd-mm-yyyy"
ws["C4"] = "Promise to Pay"
ws["D4"] = "System Test"
ws["E4"] = results.get("Passed Scenarios", 0)
ws["F4"] = results.get("Failed Scenarios", 0)
ws["G4"] = results.get("Skipped Scenarios", 0)
ws["H4"] = results.get("All Scenarios", 0)
ws["I4"] = duration


# LSM - Row 5
lsm = pipeline_results.get("LSM", {})
ws["B5"] = report_date
ws["B5"].number_format = "dd-mm-yyyy"
ws["C5"] = "LSM"
ws["D5"] = "System Test"
ws["E5"] = lsm.get("passed", 0)
ws["F5"] = lsm.get("failed", 0)
ws["G5"] = lsm.get("others", 0)
ws["H5"] = lsm.get("total", 0)
ws["I5"] = lsm.get("duration", "")

# RARS - Row 6
rars = pipeline_results.get("RARS (V2)", {})
ws["B6"] = report_date
ws["B6"].number_format = "dd-mm-yyyy"
ws["C6"] = "RARS (V2)"
ws["D6"] = "System Test"
ws["E6"] = rars.get("passed", 0)
ws["F6"] = rars.get("failed", 0)
ws["G6"] = rars.get("others", 0)
ws["H6"] = rars.get("total", 0)
ws["I6"] = rars.get("duration", "")


print("\nParsed Results:")
print("Total   :", results.get("All Scenarios"))
print("Passed  :", results.get("Passed Scenarios"))
print("Failed  :", results.get("Failed Scenarios"))
print("Skipped :", results.get("Skipped Scenarios"))
print("Duration:", duration)

try:
    wb.save(EXCEL_FILE)
    print("Excel Updated Successfully")
except PermissionError:
    print(f"\n[ERROR] Permission denied: '{EXCEL_FILE}' is currently open in Excel.")
    print("Please close the Excel file and re-run the script.")