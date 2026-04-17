import pandas as pd
import matplotlib.pyplot as plt

# Step 1: Create employee data
data = {
    "Employee_ID": [101, 102, 103, 104, 105],
    "Name": ["Alice", "Bob", "Charlie", "David", "Eva"],
    "Department": ["HR", "IT", "Finance", "IT", "Marketing"],
    "Salary": [40000, 60000, 55000, 65000, 50000]
}

df = pd.DataFrame(data)

# Step 2: Save to CSV
csv_file = "employees.csv"
df.to_csv(csv_file, index=False)
print(f"\nCSV file '{csv_file}' created successfully!\n")

# Step 3: Display table output
print("Employee Data Table:\n")
print(df.to_string(index=False))  # clean table format

# Step 4: Plot graph (Salary comparison)
plt.figure(figsize=(8, 5))
plt.bar(df["Name"], df["Salary"], color="skyblue")

plt.title("Employee Salary Comparison")
plt.xlabel("Employee Name")
plt.ylabel("Salary")
plt.xticks(rotation=45)

# Show values on top of bars
for i, salary in enumerate(df["Salary"]):
    plt.text(i, salary + 500, str(salary), ha='center')

plt.tight_layout()
plt.show()