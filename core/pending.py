import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

TTL_SECONDS = 60.0


@dataclass
class PendingAction:
    tool: str
    args: dict
    user_id: int
    expires_at: float


class PendingStore:
    def __init__(self, ttl: float = TTL_SECONDS, clock: Callable[[], float] = time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self._items: dict[str, PendingAction] = {}

    def add(self, tool: str, args: dict, user_id: int) -> str:
        self._purge()
        action_id = secrets.token_urlsafe(6)
        self._items[action_id] = PendingAction(tool, args, user_id, self.clock() + self.ttl)
        return action_id

    def pop(self, action_id: str, user_id: int) -> PendingAction | None:
        self._purge()
        item = self._items.get(action_id)
        if item is None or item.user_id != user_id:
            return None
        del self._items[action_id]
        return item

    def _purge(self) -> None:
        now = self.clock()
        for key in [k for k, v in self._items.items() if v.expires_at <= now]:
            del self._items[key]
