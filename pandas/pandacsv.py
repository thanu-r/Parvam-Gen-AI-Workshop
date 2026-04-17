import pandas as pd

# Step 1: Create Data
data = {
    "Name": ["John", "Alice", "Bob", "David", "Emma"],
    "Age": [25, 30, 22, 35, 28],
    "Marks": [85, 90, 78, 88, 92]
}

# Step 2: Create DataFrame
df = pd.DataFrame(data)

# Step 3: Save CSV file automatically in current folder
df.to_csv("students.csv", index=False)
print("CSV file created successfully!")

# Step 4: Read CSV file
df = pd.read_csv("students.csv")

print("\n--- Full Data ---")
print(df)

# Step 5: Selecting Data
print("\n--- Select Name Column ---")
print(df["Name"])

print("\n--- Select Name & Marks ---")
print(df[["Name", "Marks"]])

print("\n--- Select First Row ---")
print(df.iloc[0])

# Step 6: Filtering Data
print("\n--- Students with Marks > 85 ---")
filtered = df[df["Marks"] > 85]
print(filtered)

# Step 7: Add New Column
df["Grade"] = ["B", "A", "C", "B", "A"]
print("\n--- After Adding Grade Column ---")
print(df)

# Step 8: Basic Operations
print("\n--- Statistics ---")
print("Average Marks:", df["Marks"].mean())
print("Maximum Marks:", df["Marks"].max())
print("Minimum Marks:", df["Marks"].min())

