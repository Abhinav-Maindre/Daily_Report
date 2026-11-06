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

import json
from bs4 import BeautifulSoup
import re

promise_to_pay_build_id = None
promise_to_pay_build_url = None
pipeline_results = {}
pipeline_links = {}
extracted_failed_scenarios = []
extracted_skipped_scenarios = []


def extract_full_assertion_error(error_msg, stack_trace=None):
    """Extract complete assertion failure including 'Object: ... is missing' or status details."""
    raw_source = stack_trace if (stack_trace and "assert" in stack_trace.lower()) else error_msg
    if not raw_source:
        return "No error message provided"

    # Remove java.lang.AssertionError: prefix wherever it appears
    raw_source = re.sub(r'java\.lang\.AssertionError:\s*', '', raw_source)

    lines = [line.rstrip() for line in raw_source.strip().split("\n")]
    result_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("at ") or stripped.startswith("... ") or (stripped.startswith("Caused by:") and "Assertion" not in stripped):
            break
        if stripped:
            result_lines.append(line)

    if result_lines:
        return "\n".join(result_lines)
    return error_msg.strip() if error_msg else "No error message provided"


def parse_request_body_step(step_text):
    """Parse key-value pairs from Cucumber request body step into a JSON dictionary."""
    pattern = r'(\w+)\s+"([^"]*)"'
    matches = re.findall(pattern, step_text)
    if not matches:
        return None
    data = {}
    for key, val in matches:
        if key in ["numberOfAdults", "numberOfChildren", "amount"]:
            try:
                data[key] = int(val)
            except ValueError:
                data[key] = val
        elif key == "railcards":
            if val:
                data[key] = [r.strip() for r in val.split(",") if r.strip()]
            else:
                data[key] = []
        else:
            data[key] = val
    return data


def parse_promise_to_pay_failures(html_file):
    """Extract failed scenarios, endpoints, and request bodies from Promise to Pay Cucumber HTML report."""
    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    failed_scenarios = []

    panels = soup.find_all("div", class_="panel")
    for panel in panels:
        danger_label = panel.find("span", class_="label-danger")
        if danger_label and "Steps Failed" in danger_label.get("title", ""):
            title_div = panel.find("div", class_="ellipsis")
            scenario_name = title_div.get_text(strip=True) if title_div else "Unknown Scenario"

            panel_text = panel.get_text()
            endpoint = None
            method = "POST"

            endpoint_match = re.search(r"API Request Details\s*=\s*(POST|GET|PUT|DELETE)?\s*Request Endpoint\s*:\s*([^\s<]+)", panel_text, re.IGNORECASE)
            if not endpoint_match:
                endpoint_match = re.search(r"API Request Details\s*=\s*(POST|GET|PUT|DELETE)?\s*(.*?):\s*([^\s<]+)", panel_text, re.IGNORECASE)

            if endpoint_match:
                if endpoint_match.group(1):
                    method = endpoint_match.group(1).upper()
                endpoint = endpoint_match.group(len(endpoint_match.groups())).strip()

            failed_step = None
            error_message = None
            request_body = None
            asset_id = None

            steps = panel.find_all("div", class_="steps")
            for step in steps:
                lbl = step.find("span", class_="label")
                status = lbl.get("title") if lbl else ""
                step_name_el = step.find("span", class_="stepname")
                step_name = step_name_el.get_text(strip=True) if step_name_el else ""

                if "request body having" in step_name.lower():
                    request_body = parse_request_body_step(step_name)

                if "assetid" in step_name.lower():
                    asset_match = re.search(r'AssetId\s+"([^"]+)"', step_name, re.IGNORECASE)
                    if asset_match:
                        asset_id = asset_match.group(1)

                if "Failed" in status or (lbl and "label-danger" in lbl.get("class", [])):
                    kw = step.find("span", class_="keyword")
                    kw_text = kw.get_text(strip=True) if kw else ""
                    failed_step = f"{kw_text} {step_name}".strip()

                    error_modal = step.find("div", class_="modal-body")
                    if error_modal and error_modal.find("pre"):
                        error_message = error_modal.find("pre").get_text(strip=True)
                    else:
                        coll = step.find("div", class_="collapse")
                        if coll and coll.find("pre"):
                            error_message = coll.find("pre").get_text(strip=True)

            failed_scenarios.append({
                "project": "Promise to Pay",
                "scenario": scenario_name,
                "failed_step": failed_step or "Unknown Step",
                "error_message": extract_full_assertion_error(error_message),
                "method": method,
                "endpoint": endpoint or "https://ticketing-test.worldline.global/fulfil/promisetopay",
                "asset_id": asset_id,
                "request_body": request_body
            })

    return failed_scenarios


def get_ado_failed_test_requests(project_name, project_id, build_id):
    """Retrieve failed test scenarios, endpoints, and request bodies from ADO test runs & attachments."""
    failed_details = []
    try:
        runs_url = (
            f"https://dev.azure.com/{ORG}/{project_id}/_apis/test/runs"
            f"?buildUri=vstfs:///Build/Build/{build_id}"
            f"&api-version=7.1"
        )
        runs_resp = requests.get(runs_url, auth=HTTPBasicAuth("", PAT))
        runs_resp.raise_for_status()
        runs = runs_resp.json().get("value", [])

        for run in runs:
            run_id = run["id"]
            results_url = (
                f"https://dev.azure.com/{ORG}/{project_id}/_apis/test/Runs/{run_id}/results"
                f"?api-version=7.1"
            )
            res_resp = requests.get(results_url, auth=HTTPBasicAuth("", PAT))
            if res_resp.status_code != 200:
                continue

            results = res_resp.json().get("value", [])
            for res in results:
                if res.get("outcome") == "Failed":
                    test_title = res.get("testCaseTitle") or res.get("automatedTestName") or "Unknown Test"
                    error_msg = res.get("errorMessage") or "No error message"
                    result_id = res.get("id")

                    scenario_name = test_title
                    match = re.search(r'runScenario\["([^"]+)"', test_title)
                    if match:
                        scenario_name = match.group(1)

                    method = None
                    endpoint = None
                    request_body = None

                    att_url = (
                        f"https://dev.azure.com/{ORG}/{project_id}/_apis/test/runs/{run_id}/results/{result_id}/attachments"
                        f"?api-version=7.1"
                    )
                    att_resp = requests.get(att_url, auth=HTTPBasicAuth("", PAT))
                    if att_resp.status_code == 200:
                        attachments = att_resp.json().get("value", [])
                        for att in attachments:
                            if att.get("fileName") == "Standard_Console_Output.log":
                                download_url = att.get("url")
                                log_resp = requests.get(download_url, auth=HTTPBasicAuth("", PAT))
                                if log_resp.status_code == 200:
                                    log_text = log_resp.text

                                    req_matches = list(re.finditer(r"Request method:\s+([A-Z]+)\s+Request URI:\s+([^\s\n]+)", log_text))
                                    chosen_req = None
                                    for rm in req_matches:
                                        if "oauth" not in rm.group(2).lower():
                                            chosen_req = rm
                                            break
                                    if not chosen_req and req_matches:
                                        chosen_req = req_matches[-1]

                                    if chosen_req:
                                        method = chosen_req.group(1)
                                        endpoint = chosen_req.group(2)

                                    body_match = re.search(r"Body:\s*\n(\{.*?\n\})\s*\n", log_text, re.DOTALL)
                                    if body_match:
                                        try:
                                            request_body = json.loads(body_match.group(1))
                                        except Exception:
                                            request_body = body_match.group(1).strip()

                    stack_trace = res.get("stackTrace")
                    full_error = extract_full_assertion_error(error_msg, stack_trace)

                    failed_details.append({
                        "project": project_name,
                        "test_case": test_title,
                        "scenario": scenario_name,
                        "error_message": full_error,
                        "method": method or "GET",
                        "endpoint": endpoint or "Endpoint not identified in logs",
                        "request_body": request_body
                    })

    except Exception as ex:
        print(f"  [ERROR] fetching failure logs for {project_name}: {ex}")

    return failed_details


def parse_promise_to_pay_skipped(html_file):
    """Extract skipped scenarios, endpoints, and request bodies from Promise to Pay Cucumber HTML report."""
    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    skipped_scenarios = []

    panels = soup.find_all("div", class_="panel")
    for panel in panels:
        heading = panel.find("div", class_="panel-heading")
        if not heading:
            continue
        labels = heading.find_all("span", class_="label")
        titles = [l.get("title", "") for l in labels]
        has_skipped = any("Steps Skipped" in t for t in titles)
        has_failed = any("Steps Failed" in t for t in titles)

        if has_skipped and not has_failed:
            title_div = heading.find("div", class_="ellipsis")
            scenario_name = title_div.get_text(strip=True) if title_div else "Unknown Scenario"

            panel_text = panel.get_text()
            endpoint = None
            method = "POST"

            endpoint_match = re.search(r"API Request Details\s*=\s*(POST|GET|PUT|DELETE)?\s*Request Endpoint\s*:\s*([^\s<]+)", panel_text, re.IGNORECASE)
            if not endpoint_match:
                endpoint_match = re.search(r"API Request Details\s*=\s*(POST|GET|PUT|DELETE)?\s*(.*?):\s*([^\s<]+)", panel_text, re.IGNORECASE)

            if endpoint_match:
                if endpoint_match.group(1):
                    method = endpoint_match.group(1).upper()
                endpoint = endpoint_match.group(len(endpoint_match.groups())).strip()

            skipped_step = None
            request_body = None
            asset_id = None

            steps = panel.find_all("div", class_="steps")
            for step in steps:
                lbl = step.find("span", class_="label")
                status = lbl.get("title") if lbl else ""
                step_name_el = step.find("span", class_="stepname")
                step_name = step_name_el.get_text(strip=True) if step_name_el else ""

                if "request body having" in step_name.lower():
                    request_body = parse_request_body_step(step_name)

                if "assetid" in step_name.lower():
                    asset_match = re.search(r'AssetId\s+"([^"]+)"', step_name, re.IGNORECASE)
                    if asset_match:
                        asset_id = asset_match.group(1)

                if "Skipped" in status and not skipped_step:
                    kw = step.find("span", class_="keyword")
                    kw_text = kw.get_text(strip=True) if kw else ""
                    skipped_step = f"{kw_text} {step_name}".strip()

            skipped_scenarios.append({
                "project": "Promise to Pay",
                "scenario": scenario_name,
                "status": "Skipped",
                "first_skipped_step": skipped_step or "Prerequisite step skipped",
                "method": method,
                "endpoint": endpoint or "https://ticketing-test.worldline.global/fulfil/promisetopay",
                "asset_id": asset_id,
                "request_body": request_body
            })

    return skipped_scenarios


def get_ado_skipped_test_requests(project_name, project_id, build_id):
    """Retrieve skipped/unexecuted test scenarios, endpoints, and reasons from ADO test runs."""
    skipped_details = []
    try:
        runs_url = (
            f"https://dev.azure.com/{ORG}/{project_id}/_apis/test/runs"
            f"?buildUri=vstfs:///Build/Build/{build_id}"
            f"&api-version=7.1"
        )
        runs_resp = requests.get(runs_url, auth=HTTPBasicAuth("", PAT))
        runs_resp.raise_for_status()
        runs = runs_resp.json().get("value", [])

        for run in runs:
            run_id = run["id"]
            results_url = (
                f"https://dev.azure.com/{ORG}/{project_id}/_apis/test/Runs/{run_id}/results"
                f"?api-version=7.1"
            )
            res_resp = requests.get(results_url, auth=HTTPBasicAuth("", PAT))
            if res_resp.status_code != 200:
                continue

            results = res_resp.json().get("value", [])
            for res in results:
                outcome = res.get("outcome")
                if outcome not in ["Passed", "Failed"]:
                    test_title = res.get("testCaseTitle") or res.get("automatedTestName") or "Unknown Test"
                    error_msg = res.get("errorMessage") or f"Test status: {outcome}"
                    result_id = res.get("id")

                    scenario_name = test_title
                    match = re.search(r'runScenario\["([^"]+)"', test_title)
                    if match:
                        scenario_name = match.group(1)

                    method = "POST" if "POST" in scenario_name.upper() else ("PUT" if "PUT" in scenario_name.upper() else "GET")
                    endpoint = None
                    request_body = None

                    att_url = (
                        f"https://dev.azure.com/{ORG}/{project_id}/_apis/test/runs/{run_id}/results/{result_id}/attachments"
                        f"?api-version=7.1"
                    )
                    att_resp = requests.get(att_url, auth=HTTPBasicAuth("", PAT))
                    if att_resp.status_code == 200:
                        attachments = att_resp.json().get("value", [])
                        for att in attachments:
                            if att.get("fileName") == "Standard_Console_Output.log":
                                download_url = att.get("url")
                                log_resp = requests.get(download_url, auth=HTTPBasicAuth("", PAT))
                                if log_resp.status_code == 200:
                                    log_text = log_resp.text
                                    req_matches = list(re.finditer(r"Request method:\s+([A-Z]+)\s+Request URI:\s+([^\s\n]+)", log_text))
                                    chosen_req = None
                                    for rm in req_matches:
                                        if "oauth" not in rm.group(2).lower():
                                            chosen_req = rm
                                            break
                                    if not chosen_req and req_matches:
                                        chosen_req = req_matches[-1]

                                    if chosen_req:
                                        method = chosen_req.group(1)
                                        endpoint = chosen_req.group(2)

                                    body_match = re.search(r"Body:\s*\n(\{.*?\n\})\s*\n", log_text, re.DOTALL)
                                    if body_match:
                                        try:
                                            request_body = json.loads(body_match.group(1))
                                        except Exception:
                                            request_body = body_match.group(1).strip()

                    stack_trace = res.get("stackTrace")
                    full_reason = extract_full_assertion_error(error_msg, stack_trace)

                    skipped_details.append({
                        "project": project_name,
                        "test_case": test_title,
                        "scenario": scenario_name,
                        "status": outcome,
                        "reason": full_reason,
                        "method": method,
                        "endpoint": endpoint or "Endpoint inferred from scenario / not executed",
                        "request_body": request_body
                    })

    except Exception as ex:
        print(f"  [ERROR] fetching skipped logs for {project_name}: {ex}")

    return skipped_details


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
        build_id = build["id"]
        build_url = build.get("_links", {}).get("web", {}).get("href", f"https://dev.azure.com/{ORG}/{pipeline['project_id']}/_build/results?buildId={build_id}")
        pipeline_links[pipeline["name"]] = {
            "build_id": build_id,
            "build_url": build_url
        }

        print(f"\nProject : {pipeline['name']}")
        print(f"Build ID: {build_id}")
        print(f"Build URL: {build_url}")
        print(f"Result  : {build.get('result')}")

        if pipeline["name"] != "Promise to Pay":

            summary = get_test_summary(
                pipeline["project_id"],
                build_id
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
            "duration": format_pipeline_duration(duration),
            "build_id": build_id,
            "build_url": build_url
            }

            if summary["failed"] > 0:
                print(f"  Fetching failed scenario details, endpoints & request bodies for {pipeline['name']}...")
                ado_fails = get_ado_failed_test_requests(pipeline["name"], pipeline["project_id"], build_id)
                extracted_failed_scenarios.extend(ado_fails)
                print(f"  Extracted {len(ado_fails)} failed scenario(s) from {pipeline['name']}.")

            if summary["others"] > 0:
                print(f"  Fetching skipped scenario details & endpoints for {pipeline['name']}...")
                ado_skipped = get_ado_skipped_test_requests(pipeline["name"], pipeline["project_id"], build_id)
                extracted_skipped_scenarios.extend(ado_skipped)
                print(f"  Extracted {len(ado_skipped)} skipped scenario(s) from {pipeline['name']}.")

        else:
            promise_to_pay_build_id = build_id
            promise_to_pay_build_url = build_url
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

if int(results.get("Failed Scenarios", 0)) > 0:
    print("\n  Fetching failed scenario details, endpoints & request bodies for Promise to Pay...")
    p2p_fails = parse_promise_to_pay_failures(html_file)
    extracted_failed_scenarios.extend(p2p_fails)
    print(f"  Extracted {len(p2p_fails)} failed scenario(s) from Promise to Pay.")

if int(results.get("Skipped Scenarios", 0)) > 0:
    print("\n  Fetching skipped scenario details, endpoints & request bodies for Promise to Pay...")
    p2p_skipped = parse_promise_to_pay_skipped(html_file)
    extracted_skipped_scenarios.extend(p2p_skipped)
    print(f"  Extracted {len(p2p_skipped)} skipped scenario(s) from Promise to Pay.")


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
if rds.get("build_id"):
    ws["K3"].value = f"Pipelines - Run {rds.get('build_id')}"
    ws["K3"].hyperlink = rds.get("build_url")


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
if promise_to_pay_build_id:
    ws["K4"].value = f"Pipelines - Run {promise_to_pay_build_id}"
    ws["K4"].hyperlink = promise_to_pay_build_url


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
if lsm.get("build_id"):
    ws["K5"].value = f"Pipelines - Run {lsm.get('build_id')}"
    ws["K5"].hyperlink = lsm.get("build_url")

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
if rars.get("build_id"):
    ws["K6"].value = f"Pipelines - Run {rars.get('build_id')}"
    ws["K6"].hyperlink = rars.get("build_url")


print("\nParsed Results:")
print("Total   :", results.get("All Scenarios"))
print("Passed  :", results.get("Passed Scenarios"))
print("Failed  :", results.get("Failed Scenarios"))
print("Skipped :", results.get("Skipped Scenarios"))
print("Duration:", duration)

print("\n" + "=" * 70)
print("PROJECT PIPELINE REPORT LINKS")
print("=" * 70)
print(f"RDS: Pipelines - Run {rds.get('build_id')} ({rds.get('build_url')})")
print(f"Promise to Pay: Pipelines - Run {promise_to_pay_build_id} ({promise_to_pay_build_url})")
print(f"LSM: Pipelines - Run {lsm.get('build_id')} ({lsm.get('build_url')})")
print(f"RARS: Pipelines - Run {rars.get('build_id')} ({rars.get('build_url')})")

# Export separate files for links
link_items = [
    {"name": "RDS", "build_id": rds.get("build_id"), "url": rds.get("build_url")},
    {"name": "Promise to Pay", "build_id": promise_to_pay_build_id, "url": promise_to_pay_build_url},
    {"name": "LSM", "build_id": lsm.get("build_id"), "url": lsm.get("build_url")},
    {"name": "RARS", "build_id": rars.get("build_id"), "url": rars.get("build_url")}
]

html_links_file = os.path.join(BASE_DIR, "pipeline_links.html")
with open(html_links_file, "w", encoding="utf-8") as f:
    f.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<title>Pipeline Report Links</title>\n')
    f.write('<style>body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 25px; line-height: 1.8; font-size: 16px; }\n')
    f.write('.item { margin-bottom: 10px; } .proj { font-weight: bold; display: inline-block; width: 140px; } a { color: #0078d4; text-decoration: underline; }</style>\n')
    f.write('</head>\n<body>\n<h3>Pipeline Report Links</h3>\n')
    for item in link_items:
        f.write(f'  <div class="item"><span class="proj">{item["name"]}:</span> <a href="{item["url"]}" target="_blank">Pipelines - Run {item["build_id"]}</a></div>\n')
    f.write('</body>\n</html>')

md_links_file = os.path.join(BASE_DIR, "pipeline_links.md")
with open(md_links_file, "w", encoding="utf-8") as f:
    f.write("# Pipeline Report Links\n\n")
    for item in link_items:
        f.write(f"- **{item['name']}**: [Pipelines - Run {item['build_id']}]({item['url']})\n")

# Also update teams_message.html and teams_message.md with bullet points
today_str = datetime.now().strftime("%d-%m-%Y")
teams_html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Teams Ready Message</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 15px;
            color: #242424;
            padding: 30px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }}
        .card {{
            background: #ffffff;
            border: 1px solid #e1dfdd;
            border-radius: 8px;
            padding: 24px;
            max-width: 650px;
            margin: 0 auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        ul {{
            margin-top: 8px;
            margin-bottom: 8px;
            padding-left: 20px;
            line-height: 1.8;
        }}
        li {{
            margin-bottom: 4px;
        }}
        a {{
            color: #5b5fc7;
            text-decoration: underline;
            font-weight: 600;
        }}
        a:hover {{
            color: #444791;
        }}
        .hint {{
            margin-top: 24px;
            padding: 10px;
            background-color: #f0f4f8;
            border-left: 4px solid #5b5fc7;
            font-size: 13px;
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div>Hi All, below are automation test reports for each feature/project: {today_str}</div>
        <br><br>
        <div><strong>Pipelines:</strong></div>
        <ul>
"""
for item in link_items:
    teams_html_content += f'            <li>{item["name"]}: <a href="{item["url"]}" target="_blank">Pipelines - Run {item["build_id"]}</a></li>\n'

teams_html_content += """        </ul>
        <div class="hint">
            <strong>Tip:</strong> Press <code>Ctrl + A</code>, then <code>Ctrl + C</code> and paste directly into your Microsoft Teams chat!
        </div>
    </div>
</body>
</html>"""

teams_html_file = os.path.join(BASE_DIR, "teams_message.html")
with open(teams_html_file, "w", encoding="utf-8") as f:
    f.write(teams_html_content)

teams_md_lines = [
    f"Hi All, below are automation test reports for each feature/project: {today_str}\n\n\n\n",
    "Pipelines:\n"
]
for item in link_items:
    teams_md_lines.append(f"- {item['name']}: [Pipelines - Run {item['build_id']}]({item['url']})\n")

teams_md_file = os.path.join(BASE_DIR, "teams_message.md")
with open(teams_md_file, "w", encoding="utf-8") as f:
    f.writelines(teams_md_lines)

print(f"\n[INFO] All report files exported:")
print(f"  - Pipeline Links HTML:  {html_links_file}")
print(f"  - Pipeline Links MD:    {md_links_file}")
print(f"  - Teams Message HTML:   {teams_html_file}")
print(f"  - Teams Message MD:     {teams_md_file}")

try:
    wb.save(EXCEL_FILE)
    print("Excel Updated Successfully")
except PermissionError:
    print(f"\n[ERROR] Permission denied: '{EXCEL_FILE}' is currently open in Excel.")
    print("Please close the Excel file and re-run the script.")

# DISPLAY & EXPORT FAILED SCENARIOS FOR MANUAL EXECUTION
if extracted_failed_scenarios:
    print("\n" + "=" * 70)
    print("FAILED SCENARIOS EXTRACTED FOR MANUAL EXECUTION")
    print("=" * 70)
    for idx, item in enumerate(extracted_failed_scenarios, 1):
        print(f"\n[{idx}] Project     : {item.get('project')}")
        print(f"    Scenario    : {item.get('scenario')}")
        if item.get("failed_step"):
            print(f"    Failed Step : {item.get('failed_step')}")
        err = item.get("error_message", "")
        if "\n" in err:
            err_indented = err.replace("\n", "\n                  ")
            print(f"    Error Msg   : {err_indented}")
        else:
            print(f"    Error Msg   : {err}")
        print(f"    Endpoint    : {item.get('method')} {item.get('endpoint')}")
        if item.get("asset_id"):
            print(f"    Asset ID    : {item.get('asset_id')}")
        if item.get("request_body"):
            print(f"    Request Body:\n{json.dumps(item.get('request_body'), indent=6)}")
        else:
            print("    Request Body: None")

    output_file = os.path.join(BASE_DIR, "failed_scenarios_for_manual_run.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(extracted_failed_scenarios, f, indent=2)
    print("\n" + "=" * 70)
    print(f"[SUCCESS] All {len(extracted_failed_scenarios)} failed scenario request payload(s) exported to:")
    print(f"  {output_file}")
    print("=" * 70)

# DISPLAY & EXPORT SKIPPED SCENARIOS FOR MANUAL EXECUTION
if extracted_skipped_scenarios:
    print("\n" + "=" * 70)
    print("SKIPPED SCENARIOS EXTRACTED FOR MANUAL EXECUTION")
    print("=" * 70)
    for idx, item in enumerate(extracted_skipped_scenarios, 1):
        print(f"\n[{idx}] Project     : {item.get('project')}")
        print(f"    Scenario    : {item.get('scenario')}")
        if item.get("first_skipped_step"):
            print(f"    Skipped Step: {item.get('first_skipped_step')}")
        reason = item.get("reason", "")
        if "\n" in reason:
            reason_indented = reason.replace("\n", "\n                  ")
            print(f"    Reason      : {reason_indented}")
        elif reason:
            print(f"    Reason      : {reason}")
        print(f"    Endpoint    : {item.get('method')} {item.get('endpoint')}")
        if item.get("asset_id"):
            print(f"    Asset ID    : {item.get('asset_id')}")
        if item.get("request_body"):
            print(f"    Request Body:\n{json.dumps(item.get('request_body'), indent=6)}")
        else:
            print("    Request Body: None")

    skipped_output_file = os.path.join(BASE_DIR, "skipped_scenarios_for_manual_run.json")
    with open(skipped_output_file, "w", encoding="utf-8") as f:
        json.dump(extracted_skipped_scenarios, f, indent=2)
    print("\n" + "=" * 70)
    print(f"[SUCCESS] All {len(extracted_skipped_scenarios)} skipped scenario request payload(s) exported to:")
    print(f"  {skipped_output_file}")
    print("=" * 70)