#!/usr/bin/env python3
"""
Simple test script to demonstrate OAuth2 device flow authentication for event pushing.
"""

from event.events import TestEvent
from event_store import EventStore

def main():
    store = EventStore(namespace='test', app='test_app')
    
    test_event = TestEvent(test_data="Hello world!")
    
    store.emit_event(test_event)
    
    store.push()

if __name__ == "__main__":
    main()
