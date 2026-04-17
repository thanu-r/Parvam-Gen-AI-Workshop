def is_prime(n):
    """Check if a number is prime"""
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def print_primes(limit):
    """Print all prime numbers up to a given limit"""
    for num in range(2, limit + 1):
        if is_prime(num):
            print(num, end=" ")

# Example usage
limit = int(input("Enter the limit: "))
print("Prime numbers up to", limit, "are:")
print_primes(limit)