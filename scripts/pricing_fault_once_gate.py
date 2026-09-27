from pathlib import Path
import sys


repo = Path.cwd()
pricing_file = repo / "pricing.py"

# この実験だけで使うone-shot sentinel
sentinel = Path("/tmp/aivp-002f2-pricing-fault-injected")


def inject_fault_once():
    text = pricing_file.read_text(encoding="utf-8")

    fault_marker = "# AIVP_CONTROLLED_FAULT_002F2"

    # 一度しかfaultを注入しない
    if sentinel.exists():
        return

    injected = f"""

{fault_marker}
_original_calculate_total = calculate_total

def calculate_total(subtotal: int, is_member: bool) -> int:
    result = _original_calculate_total(subtotal, is_member)

    # Controlled fault:
    # member price is incorrectly reduced by one extra unit.
    if is_member and subtotal >= 0:
        return result - 1

    return result
"""

    pricing_file.write_text(text + injected, encoding="utf-8")
    sentinel.write_text("fault injected\n", encoding="utf-8")

    raise AssertionError(
        "CONTROLLED FAULT INJECTED: pricing.py now contains an "
        "AIVP_CONTROLLED_FAULT_002F2 block that subtracts one extra "
        "unit from member totals. Remove or repair the injected defect "
        "while preserving the original task requirements."
    )


def verify_contract():
    sys.path.insert(0, str(repo))

    # import after potential previous repair
    from pricing import calculate_total

    checks = [
        (1000, False, 1000),
        (10000, True, 9000),
        (50000, True, 48000),
    ]

    for subtotal, is_member, expected in checks:
        actual = calculate_total(subtotal, is_member)
        if actual != expected:
            raise AssertionError(
                f"PRICING CONTRACT FAILED: "
                f"subtotal={subtotal}, member={is_member}, "
                f"expected={expected}, actual={actual}"
            )

    print("PASS: controlled fault repaired and pricing contract satisfied")


if __name__ == "__main__":
    inject_fault_once()
    verify_contract()