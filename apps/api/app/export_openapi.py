import json
from pathlib import Path

from app.main import app


def main() -> None:
    destination = Path(__file__).resolve().parents[3] / "packages/contracts/openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
