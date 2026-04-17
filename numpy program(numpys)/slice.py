import numpy as np

# Create array
arr = np.array([10, 20, 30, 40, 50, 60])

# Indexing
print("First element:", arr[0])
print("Last element:", arr[-1])
print("Third element:", arr[2])

# Slicing
print("\nElements from index 1 to 4:", arr[1:5])
print("Elements from start to index 3:", arr[:4])
print("Elements from index 2 to end:", arr[2:])
print("Every 2nd element:", arr[::2])

