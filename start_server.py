"""
Launcher script for Unicode Assignment Transformer & PDF Studio.
Locks port to 8080 (frees any stale process if needed), launches Uvicorn server, and opens the default web browser.
"""

import os
import sys
import time
import socket
import webbrowser
import threading
import asyncio
import subprocess
import uvicorn

# Unbuffered stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

# Ensure valid stdout/stderr for background pythonw / daemon execution
if sys.stdout is None or not hasattr(sys.stdout, "write"):
    sys.stdout = open("server.log", "a", encoding="utf-8")
if sys.stderr is None or not hasattr(sys.stderr, "write"):
    sys.stderr = open("server_err.log", "a", encoding="utf-8")

# Prevent WinError 10054 crash on Windows when mobile clients/browsers disconnect abruptly
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost

        def patched_call_connection_lost(self, exc):
            try:
                orig_call_connection_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass

        _ProactorBasePipeTransport._call_connection_lost = patched_call_connection_lost
    except Exception:
        pass

PORT = 8080

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def ensure_port_free(port: int):
    """Ensure port 8080 is freed from any orphaned process so the URL never changes."""
    if not is_port_in_use(port):
        return
    print(f"Port {port} is occupied. Attempting to release it...")
    try:
        # Use netstat to find PID on Windows
        res = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
        for line in res.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and "LISTENING" in parts:
                pid = int(parts[-1])
                if pid != os.getpid() and pid > 0:
                    print(f"Terminating old process (PID {pid}) on port {port}...")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        time.sleep(1.5)
    except Exception as e:
        print(f"Warning checking port: {e}")

def get_lan_ip() -> str:
    """Dynamically get current LAN IP address so DHCP changes never break the link."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def open_browser(url: str):
    time.sleep(1.2)
    print(f"Opening browser at: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    ensure_port_free(PORT)
    lan_ip = get_lan_ip()
    url = f"http://127.0.0.1:{PORT}"
    lan_url = f"http://{lan_ip}:{PORT}"
    
    print("=" * 65)
    print("   UNICODE ASSIGNMENT TRANSFORMER & PDF STUDIO")
    print(f"   Local PC URL:       {url}")
    print(f"   Local Network (LAN): {lan_url}")
    print("   Press Ctrl+C to stop the server.")
    print("=" * 65)
    
    # Launch browser in a background thread if on local machine
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    
    # Run uvicorn server with keep-alive and robust settings
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        timeout_keep_alive=65
    )
