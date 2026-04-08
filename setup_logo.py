import os
import shutil
from pathlib import Path

# Define paths
logo_dir = Path("matoleo_system/static/images")
logo_path = logo_dir / "logo.png"

# Create directory if it doesn't exist
logo_dir.mkdir(parents=True, exist_ok=True)

# Check if old logo exists and delete it
if logo_path.exists():
    os.remove(logo_path)
    print(f"✓ Deleted old logo")

print(f"✓ Logo directory ready at: {logo_path.absolute()}")
print(f"\nTo add your church logo:")
print(f"1. Save your logo as: {logo_path}")
print(f"2. The logo will automatically appear in:")
print(f"   - PDF downloads of expense & retirement forms")
print(f"   - System will gracefully handle if logo is missing")
