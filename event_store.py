import random
from string import ascii_letters, digits
import time

import requests

from events import Event

PUSH_KEY_LENGTH = 24
EVENT_STORE_API_ADDRESS = "https://127.0.0.1:8000"

class EventStore:
    def __init__(self, namespace: str, app: str) -> None:
        """Initialize the event store."""
        self.namespace = namespace
        self.app = app
        self.events: list[Event] = []

    def emit_event(self, event: Event) -> None:
        """Emit an event."""
        print(f"Event emitted: {event}")
        self.events.append(event)
    
    def push(self) -> None:
        """Push events to the API endpoint."""

        print("Pushing events to rhinventory...")

        push_key = "pushkey_".join([random.choice(ascii_letters + digits) for _ in range(PUSH_KEY_LENGTH)])

        print()
        print("Please authorize this push by visiting the following URL in your browser:")
        print(f"{EVENT_STORE_API_ADDRESS}/authorize_push/?push_key={push_key}&namespace={self.namespace}&app={self.app}")
        print()

        time.sleep(2)

        authorized = False
        attempts = 0
        while not authorized:
            print(f"\rChecking authorization...  (attempt {attempts})", end="")
            response = requests.get(
                f"{EVENT_STORE_API_ADDRESS}/check_key/",
                params={"push_key": push_key, "namespace": self.namespace, "app": self.app},
                timeout=5,
            )
            if response.status_code == 200:
                authorized = response.json().get("authorized", False)
                if authorized:
                    break
            attempts += 1
            time.sleep(2)
        
        print("\nAuthorization confirmed.")

        raise NotImplementedError("TODO actually push the events")
        