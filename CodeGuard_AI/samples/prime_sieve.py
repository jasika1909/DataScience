"""Prime utilities that have nothing to do with grade books."""
import math


def sieve(limit):
    flags = [True] * (limit + 1)
    flags[0:2] = [False, False]
    for p in range(2, int(math.sqrt(limit)) + 1):
        if flags[p]:
            for multiple in range(p * p, limit + 1, p):
                flags[multiple] = False
    return [i for i, ok in enumerate(flags) if ok]


def is_perfect(n):
    divisors = [d for d in range(1, n) if n % d == 0]
    return sum(divisors) == n


def twin_primes(limit):
    primes = sieve(limit)
    return [(a, b) for a, b in zip(primes, primes[1:]) if b - a == 2]


if __name__ == "__main__":
    print(sieve(50))
    print([n for n in range(2, 500) if is_perfect(n)])
    print(twin_primes(100))
