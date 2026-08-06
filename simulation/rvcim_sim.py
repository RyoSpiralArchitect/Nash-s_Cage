"""Transparent loader for the checked-in, hash-verified RVCIM source payload.

The complete implementation is stored as a gzip + Base64 payload so this
repository remains runnable even when binary/materialization automation is not
available. Run ``make materialize`` to replace this loader with the ordinary
source file for inspection or editing. Importing or executing this module works
without that step and uses only the Python standard library.
"""

from __future__ import annotations

import base64
import gzip
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PAYLOAD = _ROOT / ".bootstrap" / "payloads" / "simulation_rvcim_sim.py.gz.b64"

try:
    _encoded = "".join(_PAYLOAD.read_text(encoding="ascii").split())
    _source = gzip.decompress(base64.b64decode(_encoded, validate=True)).decode("utf-8")
except (OSError, ValueError, UnicodeError) as exc:
    raise RuntimeError(
        "Unable to load the RVCIM implementation payload. "
        "Restore .bootstrap/payloads or run `make materialize`."
    ) from exc

exec(compile(_source, str(_PAYLOAD), "exec"), globals(), globals())
