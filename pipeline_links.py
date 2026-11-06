import os
import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
        "name": "LSM",
        "project": "Dantooine",
        "project_id": "e46787cb-d678-412c-8334-a97f1bcfab63",
        "definition_id": 775
    },
    {
        "name": "RARS",
        "project": "Tatooine",
        "project_id": "72db6f14-8ae1-45d1-b370-091a2d82026f",
        "definition_id": 700
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
    response = requests.get(url, auth=HTTPBasicAuth("", PAT))
    response.raise_for_status()
    return response.json()["value"][0]


def extract_pipeline_links():
    links = []
    print("\nFetching latest pipeline links...")
    print("=" * 60)
    for p in PIPELINES:
        try:
            build = get_latest_build(p["project"], p["definition_id"])
            build_id = build["id"]
            build_url = build.get("_links", {}).get("web", {}).get("href", f"https://dev.azure.com/{ORG}/{p['project_id']}/_build/results?buildId={build_id}")
            links.append({
                "name": p["name"],
                "build_id": build_id,
                "url": build_url
            })
            print(f"{p['name']}: Pipelines - Run {build_id} -> {build_url}")
        except Exception as e:
            print(f"Error fetching {p['name']}: {e}")

    # Generate HTML file with clickable hyperlinks inside "Pipelines - Run {build_id}"
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Pipeline Report Links</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 30px;
            line-height: 1.8;
            font-size: 16px;
            color: #333;
        }
        .container {
            max-width: 650px;
            margin: 0 auto;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        h3 {
            margin-top: 0;
            color: #1a1a1a;
            border-bottom: 2px solid #0078d4;
            padding-bottom: 8px;
        }
        .item {
            margin-bottom: 12px;
            font-size: 16px;
        }
        .project {
            font-weight: 600;
            display: inline-block;
            width: 130px;
        }
        a {
            color: #0078d4;
            text-decoration: underline;
            font-weight: 500;
        }
        a:hover {
            color: #004578;
        }
    </style>
</head>
<body>
    <div class="container">
        <h3>Pipeline Report Links</h3>
"""
    for item in links:
        html_content += f'        <div class="item"><span class="project">{item["name"]}:</span> <a href="{item["url"]}" target="_blank">Pipelines - Run {item["build_id"]}</a></div>\n'
    html_content += """    </div>
</body>
</html>"""

    html_file = os.path.join(BASE_DIR, "pipeline_links.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Generate Markdown file
    md_lines = ["# Pipeline Report Links\n\n"]
    for item in links:
        md_lines.append(f"- **{item['name']}**: [Pipelines - Run {item['build_id']}]({item['url']})\n")

    md_file = os.path.join(BASE_DIR, "pipeline_links.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.writelines(md_lines)

    print("=" * 60)
    print(f"[SUCCESS] Exported:")
    print(f"  1. HTML (clickable links in browser/Teams): {html_file}")
    print(f"  2. Markdown (formatted for chat):         {md_file}")
    print("=" * 60)

    return links


if __name__ == "__main__":
    extract_pipeline_links()
