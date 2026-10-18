"""Start AppSail using the bundled Linux dependencies and assigned HTTP port."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
os.chdir(root)
vendor = root / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000")),
    )
