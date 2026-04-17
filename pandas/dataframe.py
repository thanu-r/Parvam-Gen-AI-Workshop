import pandas as pd

# Create DataFrame
data = {
"Name": ["John", "Alice", "Bob"],
"Age": [25, 30, 22],
"Marks": [85, 90, 78]
}

df = pd.DataFrame(data)

print(df)
