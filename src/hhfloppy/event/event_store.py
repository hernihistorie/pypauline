import random
from string import ascii_letters, digits
import time

import json
from typing import Sequence
import requests
import msgspec

from .events import Event

PUSH_KEY_LENGTH = 24
EVENT_STORE_API_ADDRESS = "http://127.0.0.1:5000/event_store"

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
    
    def emit_events(self, events: Sequence[Event]) -> None:
        """Emit multiple events."""
        for event in events:
            self.emit_event(event)
    
    def push(self) -> None:
        """Push events to the API endpoint."""

        print(f"Serializing {len(self.events)} events...")

        # INFO: we could be more efficient here by:
        # - not encoding/decoding json
        # - using msgspec.msgpack
        # We do it so we can add the key and namespace and use all the
        # json machinery that's already in place.
        # Once we have a command protocol (like in Trovery), these
        # improvements should be incorporated.
        serialized_events = json.loads(msgspec.json.encode(self.events))

        print("Serialized data:", serialized_events)

        print("Pushing events to rhinventory...")

        push_key = "pushkey_" + ''.join([random.choice(ascii_letters + digits) for _ in range(PUSH_KEY_LENGTH)])

        print()
        print("Please authorize this push by visiting the following URL in your browser:")
        print(f"{EVENT_STORE_API_ADDRESS}/authorize?key={push_key}&namespace={self.namespace}&application_name={self.app}")
        print()

        time.sleep(2)

        authorized = False
        attempts = 0
        while not authorized:
            print(f"\rChecking authorization...  (attempt {attempts})", end="")
            response = requests.get(
                f"{EVENT_STORE_API_ADDRESS}/check_key/",
                params={"key": push_key, "namespace": self.namespace, "app": self.app},
                timeout=5,
            )
            if response.status_code == 200:
                authorized = response.json().get("authorized", False)
                if authorized:
                    break
            attempts += 1
            time.sleep(2)
        
        print("\nAuthorization confirmed.")

        push_data = {
            "namespace": self.namespace,
            "key": push_key,
            "serialized_events": serialized_events,
        }

        response = requests.post(
            f"{EVENT_STORE_API_ADDRESS}/ingest/",
            json=push_data,
            timeout=10,
        )

        if response.status_code == 200:
            print("Events successfully pushed.")
        else:
            print(f"Failed to push events. Status code: {response.status_code}")
            print("Response:", response.text)
