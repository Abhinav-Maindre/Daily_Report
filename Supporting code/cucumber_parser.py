from bs4 import BeautifulSoup
import re

with open(
    r"C:\Users\w136437\OneDrive - Worldline\Bureau\Promise to Pay.html",
    "r",
    encoding="utf-8",
    errors="ignore"
) as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find all cards
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

# Execution Time
match = re.search(r'Execution Time:\s*([^\n<]+)', html)

duration = match.group(1).strip() if match else ""

print("\nParsed Results:")
print("Total   :", results.get("All Scenarios"))
print("Passed  :", results.get("Passed Scenarios"))
print("Failed  :", results.get("Failed Scenarios"))
print("Skipped :", results.get("Skipped Scenarios"))
print("Duration:", duration)