import requests
from requests.auth import HTTPBasicAuth
from env_config import get_pat, get_org

PAT = get_pat()
ORG = get_org()

url = f"https://dev.azure.com/{ORG}/_apis/projects?api-version=7.1"

response = requests.get(
    url,
    auth=HTTPBasicAuth("", PAT)
)

for project in response.json()["value"]:
    print(
        f"Name: {project['name']}\n"
        f"ID  : {project['id']}\n"
    )