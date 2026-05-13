import asyncio
from typing import AsyncGenerator

_order_events: dict[int, list[asyncio.Queue]] = {}


def publish(checkout_order_id: int, event_type: str, data: dict) -> None:
    queues = _order_events.get(checkout_order_id, [])
    for queue in queues:
        queue.put_nowait({"event": event_type, "data": data})


async def subscribe(checkout_order_id: int) -> AsyncGenerator[dict, None]:
    queue: asyncio.Queue = asyncio.Queue()
    _order_events.setdefault(checkout_order_id, []).append(queue)
    try:
        while True:
            event = await queue.get()
            yield event
    finally:
        queues = _order_events.get(checkout_order_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues and checkout_order_id in _order_events:
            del _order_events[checkout_order_id]
