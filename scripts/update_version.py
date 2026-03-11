import sys
import re
import json
import os

def update_frontend_version(new_version):
    package_json_path = os.path.join("frontend", "package.json")
    with open(package_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    data["version"] = new_version
    
    with open(package_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Updated frontend/package.json to {new_version}")

def update_backend_version(new_version):
    main_py_path = os.path.join("backend", "main.py")
    with open(main_py_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Regex to find __version__ = "..."
    new_content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    
    with open(main_py_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated backend/main.py to {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/update_version.py <new_version>")
        sys.exit(1)
    
    new_version = sys.argv[1]
    # Simple semantic version regex
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print("Error: Version must be in format X.Y.Z")
        sys.exit(1)
        
    update_frontend_version(new_version)
    update_backend_version(new_version)
    print("Version update complete.")
