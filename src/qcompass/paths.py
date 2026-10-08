"""All mutable application files stay inside the project by default."""

import os
from pathlib import Path


def project_root() -> Path:
    return Path(os.environ.get("QCOMPASS_ROOT", Path(__file__).resolve().parents[2])).resolve()
