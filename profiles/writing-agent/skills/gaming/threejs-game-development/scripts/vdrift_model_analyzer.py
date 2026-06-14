#!/usr/bin/env python3
"""
VDrift Model Coordinate Analyzer — determines exact orientation and wheel positions.

Usage:
    python3 vdrift_model_analyzer.py <path_to_json_model>

Output:
    - Coordinate system (which axis is forward/up/right)
    - Front/rear wheel positions in original coordinates
    - Converted positions for Three.js Y-up (using (x, z, -y))
    - Suggested bodyGroup rotation
"""

import json
import sys
from pathlib import Path


def analyze_model(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)

    verts = data["verts"]
    num_verts = len(verts) // 3

    # Basic bounds
    xs = verts[0::3]
    ys = verts[1::3]
    zs = verts[2::3]

    result = {
        "name": data.get("name", Path(path).stem),
        "verts": num_verts,
        "tris": data.get("numTris", 0),
        "bounds": {
            "x": (min(xs), max(xs)),
            "y": (min(ys), max(ys)),
            "z": (min(zs), max(zs)),
        }
    }

    # Determine which y-direction is forward
    # By checking high-z vertex distribution at both y-extremes
    high_z = [(verts[i], verts[i+1], verts[i+2])
              for i in range(0, len(verts), 3) if verts[i+2] > 0.1]
    y_pos_high = [v for v in high_z if v[1] > 0]
    y_neg_high = [v for v in high_z if v[1] < 0]

    y_pos_max_z = max(v[2] for v in y_pos_high) if y_pos_high else 0
    y_neg_max_z = max(v[2] for v in y_neg_high) if y_neg_high else 0

    # The side with more high-z vertices and higher max-z is FRONT (hood)
    front_is_y_positive = len(y_pos_high) >= len(y_neg_high) and y_pos_max_z >= y_neg_max_z

    result["direction"] = {
        "forward_is_y_positive": front_is_y_positive,
        "y_pos_high_verts": len(y_pos_high),
        "y_neg_high_verts": len(y_neg_high),
        "y_pos_max_z": round(y_pos_max_z, 3),
        "y_neg_max_z": round(y_neg_max_z, 3),
    }

    # Find wheel positions (ground-level vertices at extremes)
    ground = [(verts[i], verts[i+1], verts[i+2])
              for i in range(0, len(verts), 3)
              if 0 < verts[i+2] < 0.15]

    if front_is_y_positive:
        front_y = max(v[1] for v in ground)
        rear_y = min(v[1] for v in ground)
    else:
        front_y = min(v[1] for v in ground)
        rear_y = max(v[1] for v in ground)

    front_verts = [v for v in ground if abs(v[1] - front_y) < 0.3]
    rear_verts = [v for v in ground if abs(v[1] - rear_y) < 0.3]

    front_left = min(v[0] for v in front_verts)
    front_right = max(v[0] for v in front_verts)
    rear_left = min(v[0] for v in rear_verts)
    rear_right = max(v[0] for v in rear_verts)

    # Converted positions using (x, z, -y)
    front_z = -front_y
    rear_z = -rear_y

    result["wheels"] = {
        "original": {
            "front": {"x": (round(front_left, 3), round(front_right, 3)), "y": round(front_y, 3), "z": round(front_verts[0][2], 3)},
            "rear": {"x": (round(rear_left, 3), round(rear_right, 3)), "y": round(rear_y, 3), "z": round(rear_verts[0][2], 3)},
        },
        "converted": {
            "front": {"x": (round(-front_left, 3), round(-front_right, 3)), "y": round(front_verts[0][2], 3), "z": round(front_z, 3)},
            "rear": {"x": (round(-rear_left, 3), round(-rear_right, 3)), "y": round(rear_verts[0][2], 3), "z": round(rear_z, 3)},
        },
        "specs": {
            "front_track_m": round(front_right - front_left, 3),
            "rear_track_m": round(rear_right - rear_left, 3),
            "wheelbase_m": round(abs(front_z - rear_z), 3),
        }
    }

    # Suggested code
    result["suggested_code"] = f"""
// === {result['name']} Wheel Positions ===
// Forward is Y-{'positive' if front_is_y_positive else 'negative'} (original)
// Convert with (x, z, -y): front at z={result['wheels']['converted']['front']['z']}
const wheelPositions = [
    [{result['wheels']['converted']['front']['x'][0]}, {result['wheels']['converted']['front']['y']}, {result['wheels']['converted']['front']['z']}],  // front-left
    [{result['wheels']['converted']['front']['x'][1]}, {result['wheels']['converted']['front']['y']}, {result['wheels']['converted']['front']['z']}],  // front-right
    [{result['wheels']['converted']['rear']['x'][0]}, {result['wheels']['converted']['rear']['y']}, {result['wheels']['converted']['rear']['z']}],   // rear-left
    [{result['wheels']['converted']['rear']['x'][1]}, {result['wheels']['converted']['rear']['y']}, {result['wheels']['converted']['rear']['z']}],   // rear-right
];
"""

    return result


def print_report(r: dict):
    print(f"=== VDrift Model: {r['name']} ===")
    print(f"  Vertices: {r['verts']}, Tris: {r['tris']}")
    print()
    print("Bounds (original VDrift):")
    print(f"  X: {r['bounds']['x'][0]:.3f} ~ {r['bounds']['x'][1]:.3f} (width)")
    print(f"  Y: {r['bounds']['y'][0]:.3f} ~ {r['bounds']['y'][1]:.3f} (length)")
    print(f"  Z: {r['bounds']['z'][0]:.3f} ~ {r['bounds']['z'][1]:.3f} (height)")
    print()
    print("Forward direction:")
    fwd = "Y-positive (+Y)" if r["direction"]["forward_is_y_positive"] else "Y-negative (-Y)"
    print(f"  Front is on: {fwd}")
    print(f"  High-z verts y+: {r['direction']['y_pos_high_verts']} (max-z: {r['direction']['y_pos_max_z']})")
    print(f"  High-z verts y-: {r['direction']['y_neg_high_verts']} (max-z: {r['direction']['y_neg_max_z']})")
    print()
    print("Wheel positions (original):")
    w = r["wheels"]["original"]
    print(f"  Front: x={w['front']['x']}, y={w['front']['y']}, z={w['front']['z']}")
    print(f"  Rear:  x={w['rear']['x']}, y={w['rear']['y']}, z={w['rear']['z']}")
    print()
    print("Wheel positions (converted to Y-up via (x,z,-y)):")
    wc = r["wheels"]["converted"]
    print(f"  Front: x={wc['front']['x']}, y={wc['front']['y']}, z={wc['front']['z']}")
    print(f"  Rear:  x={wc['rear']['x']}, y={wc['rear']['y']}, z={wc['rear']['z']}")
    print()
    s = r["wheels"]["specs"]
    print(f"Specs: track_F={s['front_track_m']}m, track_R={s['rear_track_m']}m, wheelbase={s['wheelbase_m']}m")
    print()
    print(r["suggested_code"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: vdrift_model_analyzer.py <path_to_model.json>")
        print("       vdrift_model_analyzer.py <dir/>  (analyzes all .json models in dir)")
        sys.exit(1)

    path = sys.argv[1]
    files = []
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("*.json"))
    elif p.is_file():
        files = [p]

    for f in files:
        r = analyze_model(str(f))
        print_report(r)
        print("=" * 50)
