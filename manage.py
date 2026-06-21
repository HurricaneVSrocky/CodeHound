import os
import sys
import zipfile
import subprocess
import signal
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def run_command(cmd, cwd=None):
    print(f"[{cwd if cwd else 'root'}] Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error executing: {cmd}")
        sys.exit(result.returncode)

def extract_zip(zip_path, extract_to):
    if not os.path.exists(zip_path):
        print(f"Warning: {zip_path} not found.")
        return
    print(f"Extracting {zip_path} to {extract_to}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def build():
    print("=== Step 1: Prepare Third-Party Dependencies ===")
    third_party_dir = os.path.join(PROJECT_ROOT, "third_party")
    
    pybind_dir = os.path.join(third_party_dir, "pybind11-2.11.1")
    pybind_zip = os.path.join(third_party_dir, "pybind11-2.11.1.zip")
    if not os.path.exists(pybind_dir) and os.path.exists(pybind_zip):
        extract_zip(pybind_zip, third_party_dir)

    flatbuffers_dir = os.path.join(third_party_dir, "flatbuffers-23.5.26")
    flatbuffers_zip = os.path.join(third_party_dir, "flatbuffers-23.5.26.zip")
    if not os.path.exists(flatbuffers_dir) and os.path.exists(flatbuffers_zip):
        extract_zip(flatbuffers_zip, third_party_dir)

    print("\n=== Step 2: Build C++ Engine ===")
    run_command("cmake -B build", cwd=PROJECT_ROOT)
    run_command("cmake --build build --config Release", cwd=PROJECT_ROOT)

    print("\n=== Step 3: Install Backend Dependencies ===")
    run_command("pip install -r backend/requirements.txt", cwd=PROJECT_ROOT)

    print("\n=== Step 4: Install Frontend Dependencies ===")
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    run_command("npm install", cwd=frontend_dir)

    print("\n✅ Build completed successfully!")

def start():
    print("=== Starting CodeHound Services ===")
    
    backend_proc = subprocess.Popen([sys.executable, "backend/main.py"], cwd=PROJECT_ROOT)
    
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    frontend_cmd = "npm run dev" if sys.platform != "win32" else "npm.cmd run dev"
    frontend_proc = subprocess.Popen(frontend_cmd, shell=True, cwd=frontend_dir)
    
    def signal_handler(sig, frame):
        print("\nStopping services...")
        backend_proc.terminate()
        # npm/vite might need extra handling on Windows, but terminate usually works
        frontend_proc.terminate()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Services are running. Press Ctrl+C to stop.")
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage.py [build|start]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    if cmd == "build":
        build()
    elif cmd == "start":
        start()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python manage.py [build|start]")
        sys.exit(1)
