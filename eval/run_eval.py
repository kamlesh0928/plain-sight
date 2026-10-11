import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.analyzer import analyze_image  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="en", choices=["en", "hi", "mr"])
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between calls (rate limits)")
    args = parser.parse_args()

    cases = json.loads((ROOT / "eval" / "expected.json").read_text(encoding="utf-8"))
    rows, correct, missed, false_alarms, errors = [], 0, 0, 0, 0

    for case in cases:
        path = ROOT / "eval" / "samples" / case["file"]
        accept = case["accept"]
        try:
            result = analyze_image(path.read_bytes(), args.lang)
            predicted = result["risk_level"]
        except Exception as exc:  # keep going so one failure does not hide the rest
            predicted = f"ERROR ({type(exc).__name__})"
            errors += 1
        ok = predicted in accept
        correct += ok
        if "safe" not in accept and predicted == "safe":
            missed += 1
        if accept == ["safe"] and predicted == "likely_scam":
            false_alarms += 1
        rows.append((case["file"], "/".join(accept), predicted, "PASS" if ok else "FAIL"))
        print(f"{'PASS' if ok else 'FAIL'}  {case['file']:<26} expected {'/'.join(accept):<22} got {predicted}")
        time.sleep(args.delay)

    total = len(cases)
    summary = [
        f"Accuracy: {correct}/{total}",
        f"Dangerous samples called safe (must be 0): {missed}",
        f"Legitimate samples flagged as scam: {false_alarms}",
        f"Errors: {errors}",
    ]
    print("\n" + "\n".join(summary))

    lines = ["| Sample | Expected | Got | Result |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    report = f"# Eval results ({args.lang})\n\n" + "\n".join(f"- {s}" for s in summary) + "\n\n" + "\n".join(lines) + "\n"
    (ROOT / "eval" / "results.md").write_text(report, encoding="utf-8")
    print("Saved eval/results.md")


if __name__ == "__main__":
    main()
