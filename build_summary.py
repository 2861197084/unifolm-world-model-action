#!/usr/bin/env python3
import argparse
import json
import os
import re
from typing import Optional

SCENARIOS = [
    "unitree_g1_pack_camera",
    "unitree_z1_dual_arm_cleanup_pencils",
    "unitree_z1_dual_arm_stackbox",
    "unitree_z1_dual_arm_stackbox_v2",
    "unitree_z1_stackbox",
]


def parse_real_time_seconds(log_path: str) -> Optional[float]:
    if not os.path.exists(log_path):
        return None

    pattern = re.compile(r"^real\s+(?:(\d+)m)?([0-9]+(?:\.[0-9]+)?)s\s*$")
    last_match = None

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                last_match = match

    if last_match is None:
        return None

    minutes = int(last_match.group(1)) if last_match.group(1) else 0
    seconds = float(last_match.group(2))
    return minutes * 60 + seconds


def parse_psnr(psnr_json_path: str) -> Optional[float]:
    if not os.path.exists(psnr_json_path):
        return None
    try:
        with open(psnr_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return float(data["psnr"])
    except Exception:
        return None


def build_case_result(
    before_root: str,
    after_root: str,
    scenario: str,
    case_id: int,
    strict: bool,
) -> dict:
    before_case_dir = os.path.join(before_root, scenario, f"case{case_id}")
    after_case_dir = os.path.join(after_root, scenario, f"case{case_id}")

    before_log = os.path.join(before_case_dir, "output.log")
    after_log = os.path.join(after_case_dir, "output.log")
    after_psnr_json = os.path.join(after_case_dir, "psnr_result.json")

    time_before_optim = parse_real_time_seconds(before_log)
    time_after_optim = parse_real_time_seconds(after_log)
    psnr = parse_psnr(after_psnr_json)

    if strict:
        missing = []
        if not os.path.exists(before_log):
            missing.append(f"missing before log: {before_log}")
        if not os.path.exists(after_log):
            missing.append(f"missing after log: {after_log}")
        if not os.path.exists(after_psnr_json):
            missing.append(f"missing psnr json: {after_psnr_json}")
        if time_before_optim is None:
            missing.append(f"cannot parse before real time: {before_log}")
        if time_after_optim is None:
            missing.append(f"cannot parse after real time: {after_log}")
        if psnr is None:
            missing.append(f"cannot parse psnr: {after_psnr_json}")
        if missing:
            raise ValueError(
                f"{scenario}/case{case_id} invalid for strict summary: "
                + "; ".join(missing)
            )

    return {
        "scenario": scenario,
        "case_id": case_id,
        "time_before_optim": round(float(time_before_optim), 3)
        if time_before_optim is not None else None,
        "time_after_optim": round(float(time_after_optim), 3)
        if time_after_optim is not None else None,
        "psnr": round(float(psnr), 4) if psnr is not None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build Task-goal compliant summary.json using before/after logs and "
            "after-optimization psnr_result.json files."
        )
    )
    parser.add_argument(
        "--before_root",
        type=str,
        default="Results before optimization",
        help="Root directory for before-optimization results.",
    )
    parser.add_argument(
        "--after_root",
        type=str,
        default=".",
        help="Root directory for after-optimization results (scenario folders).",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="summary.json",
        help="Output summary JSON path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Require complete 20-case data with valid numeric fields.",
    )
    parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Allow missing values and write null for incomplete cases.",
    )
    args = parser.parse_args()

    before_root = os.path.abspath(args.before_root)
    after_root = os.path.abspath(args.after_root)

    results = []
    for scenario in SCENARIOS:
        for case_id in range(1, 5):
            print(f"Collecting {scenario}/case{case_id} ...")
            result = build_case_result(
                before_root=before_root,
                after_root=after_root,
                scenario=scenario,
                case_id=case_id,
                strict=args.strict,
            )
            results.append(result)

    if args.strict and len(results) != 20:
        raise RuntimeError(f"summary.json must contain 20 entries, got {len(results)}")

    output_file = args.output_file
    if not os.path.isabs(output_file):
        output_file = os.path.join(after_root, output_file)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Saved {len(results)} entries to: {output_file}")


if __name__ == "__main__":
    main()
