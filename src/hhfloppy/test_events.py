#!/usr/bin/env python3
import click

from event.events import TestEvent
from event.event_store import EventStore

@click.command()
@click.option(
    '--test-data',
    type=str,
    default="Hello world!",
    help='Test text to include in the event'
)
def main(test_data: str):
    store = EventStore(namespace='hhfloppy', app='test_events.py')
    
    test_event = TestEvent(test_data=test_data)
    
    store.emit_event(test_event)
    
    store.push()

if __name__ == "__main__":
    main()
