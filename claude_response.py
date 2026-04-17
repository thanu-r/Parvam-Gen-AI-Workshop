def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def get_primes_in_range(start, end):
    """Return a list of prime numbers in a given range."""
    return [n for n in range(start, end + 1) if is_prime(n)]


def print_primes(start, end):
    """Print all prime numbers between start and end."""
    primes = get_primes_in_range(start, end)
    if not primes:
        print(f"No prime numbers found between {start} and {end}.")
        return
    print(f"Prime numbers between {start} and {end}:")
    print(", ".join(map(str, primes)))
    print(f"Total count: {len(primes)}")


def print_nth_prime(n):
    """Print the nth prime number."""
    count = 0
    num = 1
    while count < n:
        num += 1
        if is_prime(num):
            count += 1
    print(f"The {n}th prime number is: {num}")


# ----------------------------
# Main Program
# ----------------------------
if __name__ == "__main__":
    # Print primes in a range
    print_primes(1, 50)

    print()

    # Print the nth prime
    print_nth_prime(10)

    print()

    # Check if a specific number is prime
    number = 97
    if is_prime(number):
        print(f"{number} is a prime number.")
    else:
        print(f"{number} is NOT a prime number.")