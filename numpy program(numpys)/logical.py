import numpy as np

# Function for logical operations
def logical_operations(arr1, arr2):
    print("Array 1:", arr1)
    print("Array 2:", arr2)

    print("\nGreater (arr1 > arr2):", np.greater(arr1, arr2))
    print("Less (arr1 < arr2):", np.less(arr1, arr2))
    print("Equal (arr1 == arr2):", np.equal(arr1, arr2))
    print("Logical AND:", np.logical_and(arr1 > 2, arr2 > 2))
    print("Logical OR:", np.logical_or(arr1 > 2, arr2 > 2))
    print("Logical NOT (arr1 > 2):", np.logical_not(arr1 > 2))

# Example arrays
a = np.array([1, 2, 3, 4, 5])
b = np.array([3, 2, 1, 4, 6])

# Function call
logical_operations(a, b)
