import time
import tomllib
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

WATCH_FILE = Path(config["WATCH_FILE"])
USER_FOLDER = config["USER_FOLDER"]
BACKEND_URL = config["BACKEND_URL"]
STABILITY_WAIT = config["STABILITY_WAIT"]
DEBOUNCE_SECONDS = config["DEBOUNCE_SECONDS"]

def upload_file(file_path: Path, user_folder: str) -> None:
    """Send the file to the backend."""

    try:
        with file_path.open("rb") as f:
            response = requests.post(
                BACKEND_URL,
                files={"file": (file_path.name, f)},
                data={"user_folder": user_folder},
                timeout=5
            )

        if response.ok:
            print(f"File uploaded: {file_path.name}")
        else:
            print(f"Error uploading file: ({response.status_code})")

    except requests.RequestException as exc:
        print(f"Network error while uploading: {exc}")


class HeaderHandler(FileSystemEventHandler):
    """Handles filesystem events for the watched file."""

    def __init__(self, watch_file: Path, user_folder: str):
        self.watch_file = watch_file.resolve()
        self.user_folder = user_folder
        self.last_upload_time = 0.0

    def _is_target_file(self, path: str) -> bool:
        """Check if the event refers to the file we care about."""
        return Path(path).resolve() == self.watch_file

    def _debounce(self) -> bool:
        """Prevent duplicate uploads triggered by multiple events."""
        now = time.time()

        if now - self.last_upload_time < DEBOUNCE_SECONDS:
            return False

        self.last_upload_time = now
        return True

    def _handle_event(self, path: str) -> None:
        """Main event handler."""

        if not self._is_target_file(path):
            return

        if not self._debounce():
            return

        print(f"Change detected: {self.watch_file}")

        time.sleep(STABILITY_WAIT)

        upload_file(self.watch_file, self.user_folder)

    def on_modified(self, event):
        self._handle_event(event.src_path)

    def on_created(self, event):
        self._handle_event(event.src_path)

    def on_moved(self, event):
        self._handle_event(event.dest_path)


def start_watcher() -> None:

    if not WATCH_FILE.exists():
        print(f"File not found: {WATCH_FILE}")
        return

    event_handler = HeaderHandler(WATCH_FILE, USER_FOLDER)

    observer = Observer()
    observer.schedule(event_handler, WATCH_FILE.parent, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Watcher stopped")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_watcher()