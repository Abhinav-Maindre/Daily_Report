import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from env_config import get_pat, get_org

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

            print(f"Passed  : {summary['passed']}")
            print(f"Failed  : {summary['failed']}")
            print(f"Others  : {summary['others']}")
            print(f"Total   : {summary['total']}")
            print(f"Duration: {summary['duration']}")

        else:

            print(f"Pipeline Duration: {duration}")
            print("Promise to Pay values will come from Cucumber Report")

    except Exception as ex:
        print(f"\nProject : {pipeline['name']}")
        print(f"ERROR   : {ex}")
