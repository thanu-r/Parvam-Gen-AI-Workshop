import numpy as np

# Function for arithmetic operations
def arithmetic_operations(arr1, arr2):
 print("Array 1:", arr1)
 print("Array 2:", arr2)

 print("\nAddition:", arr1 + arr2)
 print("Subtraction:", arr1 - arr2)
 print("Multiplication:", arr1 * arr2)
 print("Division:", arr1 / arr2)

# Example arrays
a = np.array([10, 20, 30, 40, 50])
b = np.array([1, 2, 3, 4, 5])

# Function call
arithmetic_operations(a, b)
