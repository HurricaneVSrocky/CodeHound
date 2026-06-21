import time
import subprocess
import os
import sys
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, engine, parser_path, out_bin, notify_callback):
        self.engine = engine
        self.parser_path = parser_path
        self.out_bin = out_bin
        self.notify_callback = notify_callback
        self.last_run = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(('.cpp', '.h', '.c', '.hpp')):
            return

        now = time.time()
        # Debounce for 1 second
        if now - self.last_run < 1.0:
            return
        self.last_run = now

        print(f"File modified: {event.src_path}")
        
        # 1. Run Parser
        print("Running codegraph-parser...")
        try:
            subprocess.run([
                sys.executable,
                self.parser_path, 
                event.src_path, 
                "--update", 
                "--out", self.out_bin
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Parser failed: {e}")
            return
        except FileNotFoundError:
            print(f"Parser not found at {self.parser_path}, skipping update.")
            return

        # 2. Apply Delta
        print("Applying delta to graph engine...")
        success = self.engine.apply_delta(self.out_bin)
        
        # 3. Notify Frontend
        if success:
            print("Delta applied successfully! Notifying frontend.")
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.notify_callback())
            except RuntimeError:
                asyncio.run(self.notify_callback())

def start_watcher(engine, project_dir, parser_path, out_bin, notify_callback):
    event_handler = CodeChangeHandler(engine, parser_path, out_bin, notify_callback)
    observer = Observer()
    observer.schedule(event_handler, project_dir, recursive=True)
    observer.start()
    return observer
