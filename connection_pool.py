from collections import defaultdict
from starlette.websockets import WebSocket

# This ensures every key will have a default value of an empty set
active_connections: dict[str, set[WebSocket]] = defaultdict(set)
