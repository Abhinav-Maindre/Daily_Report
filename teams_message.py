import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
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


def generate_teams_message():
    links = []
    print("\nFetching latest pipeline links for Teams message...")
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

    report_date = datetime.now().strftime("%d-%m-%Y")

    # Generate HTML with native bullet points and active hyperlinks for 1-click paste
    html_msg = f"""<!DOCTYPE html>
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
        <div>Hi All, below are automation test reports for each feature/project: {report_date}</div>
        <br><br>
        <div><strong>Pipelines:</strong></div>
        <ul>
"""
    for item in links:
        html_msg += f'            <li>{item["name"]}: <a href="{item["url"]}" target="_blank">Pipelines - Run {item["build_id"]}</a></li>\n'

    html_msg += """        </ul>
        <div class="hint">
            <strong>Tip:</strong> Press <code>Ctrl + A</code>, then <code>Ctrl + C</code> and paste directly into your Microsoft Teams chat!
        </div>
    </div>
</body>
</html>"""

    # Generate Markdown format
    md_lines = [
        f"Hi All, below are automation test reports for each feature/project: {report_date}\n\n\n\n",
        "Pipelines:\n"
    ]
    for item in links:
        md_lines.append(f"- {item['name']}: [Pipelines - Run {item['build_id']}]({item['url']})\n")

    # Export to teams_message.html and teams_message.md
    teams_html_file = os.path.join(BASE_DIR, "teams_message.html")
    with open(teams_html_file, "w", encoding="utf-8") as f:
        f.write(html_msg)

    teams_md_file = os.path.join(BASE_DIR, "teams_message.md")
    with open(teams_md_file, "w", encoding="utf-8") as f:
        f.writelines(md_lines)

    # Print to terminal
    print("\n" + "=" * 70)
    print("TEAMS READY MESSAGE:")
    print("=" * 70)
    print(f"Hi All, below are automation test reports for each feature/project: {report_date}\n\n\n")
    print("Pipelines:")
    for item in links:
        print(f"• {item['name']}: Pipelines - Run {item['build_id']}")
    print("=" * 70)
    print(f"[SUCCESS] Files generated:")
    print(f"  - HTML (for Teams rich paste): {teams_html_file}")
    print(f"  - Markdown (for chat):         {teams_md_file}")
    print("=" * 70)

    return links


if __name__ == "__main__":
    generate_teams_message()
