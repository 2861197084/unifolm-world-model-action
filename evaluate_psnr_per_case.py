#!/usr/bin/env python3
import argparse
import glob
import json
import os
from typing import Optional

from psnr_score_for_challenge import process_video_psnr

SCENARIOS = [
    "unitree_g1_pack_camera",
    "unitree_z1_dual_arm_cleanup_pencils",
    "unitree_z1_dual_arm_stackbox",
    "unitree_z1_dual_arm_stackbox_v2",
    "unitree_z1_stackbox",
]


def find_pred_video(case_dir: str) -> Optional[str]:
    pattern = os.path.join(case_dir, "output", "inference", "*_full_fs*.mp4")
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return max(candidates, key=os.path.getmtime)


def eval_one_case(root_dir: str, scenario: str, case_id: int, strict: bool) -> bool:
    case_dir = os.path.join(root_dir, scenario, f"case{case_id}")
    gt_video = os.path.join(case_dir, f"{scenario}_case{case_id}.mp4")
    pred_video = find_pred_video(case_dir)
    output_file = os.path.join(case_dir, "psnr_result.json")

    if not os.path.exists(gt_video):
        msg = f"[MISS] GT video not found: {gt_video}"
        if strict:
            raise FileNotFoundError(msg)
        print(msg)
        return False

    if pred_video is None or not os.path.exists(pred_video):
        msg = f"[MISS] Pred video not found under: {os.path.join(case_dir, 'output', 'inference')}"
        if strict:
            raise FileNotFoundError(msg)
        print(msg)
        return False

    print(f"[RUN ] {scenario}/case{case_id}")
    print(f"       GT  : {gt_video}")
    print(f"       Pred: {pred_video}")

    psnr = process_video_psnr(gt_video, pred_video)
    if psnr is None:
        msg = f"[FAIL] PSNR compute failed: {scenario}/case{case_id}"
        if strict:
            raise RuntimeError(msg)
        print(msg)
        return False

    result = {
        "gt_video": os.path.relpath(gt_video, root_dir),
        "pred_video": os.path.relpath(pred_video, root_dir),
        "psnr": psnr,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"[SAVE] {output_file} (psnr={psnr:.4f})")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch PSNR evaluation for 5 scenarios x 4 cases, saving psnr_result.json in each case directory."
    )
    parser.add_argument(
        "--root_dir",
        type=str,
        default=".",
        help="Project root directory containing scenario folders.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Fail immediately if any case is missing files or PSNR computation fails.",
    )
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root_dir)
    total = 0
    success = 0

    for scenario in SCENARIOS:
        for case_id in range(1, 5):
            total += 1
            ok = eval_one_case(root_dir, scenario, case_id, args.strict)
            if ok:
                success += 1

    print("=" * 60)
    print(f"Finished: {success}/{total} cases generated psnr_result.json")
    if args.strict and success != total:
        raise RuntimeError(f"Strict mode expects {total}/{total}, got {success}/{total}")


if __name__ == "__main__":
    main()
