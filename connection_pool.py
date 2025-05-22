# connection_pool.py
from typing import Dict
from fastapi import WebSocket

active_connections: Dict[str, WebSocket] = {}
