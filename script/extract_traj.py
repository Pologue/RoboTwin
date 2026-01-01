import argparse
import os
import pickle
from pathlib import Path
from typing import Dict, Any

import numpy as np


def load_traj(traj_path: Path) -> Dict[str, Any]:
    if not traj_path.is_file():
        raise FileNotFoundError(f"Trajectory file not found: {traj_path}")
    with traj_path.open("rb") as f:
        return pickle.load(f)


def summarize_traj(traj: Dict[str, Any]) -> str:
    lines = ["Trajectory summary:"]
    for arm_key in ("left_joint_path", "right_joint_path"):
        seq = traj.get(arm_key, []) or []
        lines.append(f"- {arm_key}: {len(seq)} segments")
        for idx, segment in enumerate(seq):
            status = segment.get("status", "?")
            pos = segment.get("position")
            vel = segment.get("velocity")
            pos_shape = getattr(pos, "shape", None)
            vel_shape = getattr(vel, "shape", None)
            lines.append(
                f"  * segment {idx}: status={status}, position_shape={pos_shape}, velocity_shape={vel_shape}"
            )
    return "\n".join(lines)


def save_npz(traj: Dict[str, Any], out_path: Path) -> None:
    npz_dict = {}
    for key, segments in traj.items():
        for idx, segment in enumerate(segments):
            for name in ("position", "velocity"):
                if name in segment:
                    npz_dict[f"{key}_{idx}_{name}"] = np.array(segment[name])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out_path, **npz_dict)
    print(f"Saved NPZ to {out_path} with keys: {list(npz_dict.keys())}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract trajectory data from _traj_data/episodeX.pkl.")
    parser.add_argument("dataset_root", type=Path, help="Path to task folder (e.g., data/adjust_bottle/test1)")
    parser.add_argument("--episode", type=int, default=0, help="Episode index (default: 0)")
    parser.add_argument("--save-npz", dest="save_npz_flag", action="store_true", help="Save trajectories to NPZ")
    parser.add_argument("--npz-name", type=str, default=None, help="Custom NPZ filename (defaults to episodeX_traj.npz)")
    args = parser.parse_args()

    traj_path = args.dataset_root / "_traj_data" / f"episode{args.episode}.pkl"
    traj = load_traj(traj_path)

    print(summarize_traj(traj))

    if args.save_npz_flag:
        default_name = args.npz_name or f"episode{args.episode}_traj.npz"
        out_path = args.dataset_root / default_name
        save_npz(traj, out_path)


if __name__ == "__main__":
    main()
