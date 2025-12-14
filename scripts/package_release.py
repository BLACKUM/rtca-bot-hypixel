import os
import zipfile
import shutil
from pathlib import Path

def package_release():
    project_root = Path(__file__).parent.parent
    release_dir = project_root / "release"
    version = os.environ.get("RELEASE_VERSION")
    if version:
        output_filename = f"rtca-bot-hypixel-{version}.zip"
    else:
        output_filename = "rtca-bot-hypixel-release.zip"
    
    release_dir.mkdir(exist_ok=True)
    
    excludes = {
        '.git', '.gitignore', '.venv', 'venv', '__pycache__', 
        '.vscode', '.idea', 'release', 'scripts', '.github',
        '.gemini', 'setup.py', 'secrets.py', '.env', 'data'
    }
    
    print(f"Packaging release from {project_root}...")
    
    zip_path = release_dir / output_filename
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in excludes]
            
            for file in files:
                if file in excludes or file.endswith('.pyc'):
                    continue
                    
                file_path = Path(root) / file
                archive_name = file_path.relative_to(project_root)
                
                print(f"Adding: {archive_name}")
                zipf.write(file_path, archive_name)
                    
        zip_info = zipfile.ZipInfo("data/")
        zipf.writestr(zip_info, "")
        print("Adding: data/ (empty)")
                
    print(f"\nRelease packaged successfully at: {zip_path}")

if __name__ == "__main__":
    package_release()
