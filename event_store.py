
from events import Event
import config

class EventStore:
    def __init__(self) -> None:
        """Initialize the event store."""
        self.events: list[Event] = []
        self._api_client: ApiClient | None = None

    def emit_event(self, event: Event) -> None:
        """Emit an event."""
        print(f"Event emitted: {event}")
        self.events.append(event)
    
    def _get_authenticated_client(self) -> ApiClient:
        """Get or create an authenticated API client using OAuth2 device flow."""
    
    def push(self) -> None:
        """Push events to the API endpoint using OAuth2 device flow authentication."""
