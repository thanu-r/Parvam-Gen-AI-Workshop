import csv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Default values
DEFAULT_DEPARTMENT = "IT"
DEFAULT_ID_PREFIX = "EMP"

# Step 1: Take ONLY ONE input
name = input("Enter employee name: ")
salary = float(input(f"Enter salary for {name}: "))

# Auto-generate Employee ID
emp_id = DEFAULT_ID_PREFIX + "001"

print(f"Saved for {name}")

# Step 2: Save to CSV
with open("employee_salary.csv", "w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Employee ID", "Name", "Department", "Salary"])
    writer.writerow([emp_id, name, DEFAULT_DEPARTMENT, salary])

print("CSV file created!")

# Step 3: Show details
print("\nEmployee Details:")
print(f"ID: {emp_id}")
print(f"Name: {name}")
print(f"Department: {DEFAULT_DEPARTMENT}")
print(f"Salary: {salary}")

# Step 4: Create PDF salary slip
styles = getSampleStyleSheet()

pdf_file = f"{name}_Salary_Slip.pdf"
doc = SimpleDocTemplate(pdf_file)

content = []
content.append(Paragraph("Salary Slip", styles['Title']))
content.append(Spacer(1, 20))

content.append(Paragraph(f"Employee ID: {emp_id}", styles['Normal']))
content.append(Spacer(1, 10))

content.append(Paragraph(f"Employee Name: {name}", styles['Normal']))
content.append(Spacer(1, 10))

content.append(Paragraph(f"Department: {DEFAULT_DEPARTMENT}", styles['Normal']))
content.append(Spacer(1, 10))

content.append(Paragraph(f"Salary: {salary}", styles['Normal']))
content.append(Spacer(1, 10))

doc.build(content)

print(f"PDF created: {pdf_file}")