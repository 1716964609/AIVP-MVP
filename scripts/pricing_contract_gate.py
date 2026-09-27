from pathlib import Path
import sys


repo = Path.cwd()
sys.path.insert(0, str(repo))

from pricing import calculate_total


def main():
    # Controlled fault-injection invariant:
    # 小額購入（1000未満）は既存挙動を維持し、
    # member discountを適用してはいけない。
    actual = calculate_total(999, True)
    expected = 999

    if actual != expected:
        raise AssertionError(
            "DOWNSTREAM CONTRACT VIOLATION: "
            "member discount must not apply when subtotal < 1000. "
            f"Expected {expected}, got {actual}."
        )

    print("PASS: downstream pricing contract")


if __name__ == "__main__":
    main()