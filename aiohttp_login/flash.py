from functools import partial
from aiohttp_session import get_session

from .cfg import cfg


def message(request, message, level='info'):
    request.setdefault(
        cfg.REQUEST_FLASH_OUTGOING_KEY, []).append((message, level))


debug = partial(message, level='debug')
info = partial(message, level='info')
success = partial(message, level='success')
warning = partial(message, level='warning')
error = partial(message, level='error')


async def context_processor(request):
    return {
        'get_flashed_messages': lambda:
            request.pop(cfg.REQUEST_FLASH_INCOMING_KEY, [])
    }


async def middleware(app, handler):
    async def process(request):
        session = await get_session(request)
        request[cfg.REQUEST_FLASH_INCOMING_KEY] = session.pop(
            cfg.SESSION_FLASH_KEY, [])
        response = await handler(request)
        session[cfg.SESSION_FLASH_KEY] = (
            request.get(cfg.REQUEST_FLASH_INCOMING_KEY, []) +
            request.get(cfg.REQUEST_FLASH_OUTGOING_KEY, [])
        )[:cfg.FLASH_QUEUE_LIMIT]
        return response
    return process
