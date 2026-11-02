from openpyxl import load_workbook

wb = load_workbook(r"C:\Users\w136437\Downloads\RARS Sanity Test After AWS Lambda.xlsx")

sheet = wb["Daily Automation Report"]

for row in range(1, 15):
    values = []
    for col in range(1, 12):
        values.append(str(sheet.cell(row=row, column=col).value))
    print(f"Row {row}: {values}")