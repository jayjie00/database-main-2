import os
from pathlib import Path


def load_env_file(start_path=None, filename=".env"):
    base_path = Path(start_path or __file__).resolve()
    search_dir = base_path.parent if base_path.is_file() else base_path

    for current_dir in [search_dir, *search_dir.parents]:
        env_path = current_dir / filename
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            os.environ.setdefault(key, value)
        return env_path

    return None
