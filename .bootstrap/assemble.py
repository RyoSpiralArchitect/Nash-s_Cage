from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = ROOT / ".bootstrap" / "payloads"

TARGETS = {
    "simulation_rvcim_sim.py": (
        ROOT / "simulation" / "rvcim_sim.py",
        "19f1ba76953706212e624fc65312ac1457fd4fe54b307c3b5d224251d4657dd5",
    ),
    "paper_nashs_cage_rvcim_v0_1.tex": (
        ROOT / "paper" / "nashs_cage_rvcim_v0_1.tex",
        "6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7",
    ),
    "paper_nashs_cage_rvcim_v0_2.tex": (
        ROOT / "paper" / "nashs_cage_rvcim_v0_2.tex",
        "98e00558edecbce9efdbe0799a9c9888d5376d1c2a568481e63a582cd68f8171",
    ),
    "paper_references.bib": (
        ROOT / "paper" / "references.bib",
        "99a0c194f5698d5b8a0c655b8bccb8e5970d616b994a213b3443c3499022e08b",
    ),
}


def read_payload(stem: str) -> str:
    whole = PAYLOADS / f"{stem}.gz.b64"
    if whole.exists():
        return whole.read_text(encoding="ascii")

    parts = sorted(PAYLOADS.glob(f"{stem}.gz.b64.part*"))
    if not parts:
        raise SystemExit(f"missing payload for {stem}")
    return "".join(part.read_text(encoding="ascii") for part in parts)


def main() -> int:
    for stem, (target, expected) in TARGETS.items():
        encoded = read_payload(stem)
        raw = gzip.decompress(base64.b64decode(encoded))
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise SystemExit(f"hash mismatch for {stem}: {actual}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        print(f"assembled {target.relative_to(ROOT)} ({len(raw)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
