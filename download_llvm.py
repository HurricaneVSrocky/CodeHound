import urllib.request
import sys
import os

url = "https://gh-proxy.com/https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/LLVM-18.1.8-win64.exe"
filename = "LLVM-18.1.8-win64.exe"

print(f"Downloading {url} to {filename}...")
try:
    urllib.request.urlretrieve(url, filename)
    print("Download complete.")
except Exception as e:
    print(f"Error downloading: {e}")
    sys.exit(1)
