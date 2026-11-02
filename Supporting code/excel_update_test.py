from openpyxl import load_workbook

EXCEL_FILE = r"C:\Users\w136437\Downloads\RARS Sanity Test After AWS Lambda.xlsx"

wb = load_workbook(EXCEL_FILE)
ws = wb["Daily Automation Report"]

# RDS - Row 3
ws["E3"] = 155
ws["F3"] = 5
ws["G3"] = 0
ws["H3"] = 160
ws["I3"] = "42m 21s"

# Promise to Pay - Row 4
ws["E4"] = 25
ws["F4"] = 1
ws["G4"] = 4
ws["H4"] = 30
ws["I4"] = "19s 856ms"

# LSM - Row 5
ws["E5"] = 64
ws["F5"] = 0
ws["G5"] = 0
ws["H5"] = 64
ws["I5"] = "3m 0s"

# RARS - Row 6
ws["E6"] = 89
ws["F6"] = 0
ws["G6"] = 0
ws["H6"] = 89
ws["I6"] = "45m 3s"

wb.save(EXCEL_FILE)

print("Excel Updated Successfully")