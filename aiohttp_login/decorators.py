from functools import wraps

from aiohttp.abc import AbstractView
from aiohttp.web import HTTPForbidden, json_response, StreamResponse
try:
    import ujson as json
except ImportError:
    import json

from .cfg import cfg
from .utils import url_for, redirect, get_cur_user


def _get_request(args):
    # Supports class based views see web.View
    if isinstance(args[0], AbstractView):
        return args[0].request
    return args[-1]


def user_to_request(handler):
    '''Add user to request if user logged in'''
    @wraps(handler)
    async def decorator(*args):
        request = _get_request(args)
        request[cfg.REQUEST_USER_KEY] = await get_cur_user(request)
        return await handler(*args)
    return decorator


def login_required(handler):
    @user_to_request
    @wraps(handler)
    async def decorator(*args):
        request = _get_request(args)
        if not request[cfg.REQUEST_USER_KEY]:
            return redirect(get_login_url(request))
        return await handler(*args)
    return decorator


def restricted_api(handler):
    @user_to_request
    @wraps(handler)
    async def decorator(*args):
        request = _get_request(args)
        if not request[cfg.REQUEST_USER_KEY]:
            return json_response({'error': 'Access denied'}, status=403)
        response = await handler(*args)
        if not isinstance(response, StreamResponse):
            response = json_response(response, dumps=json.dumps)
        return response
    return decorator


def admin_required(handler):
    @wraps(handler)
    async def decorator(args):
        request = _get_request(args)
        response = await login_required(handler)(request)
        if request['user']['email'] not in cfg.ADMIN_EMAILS:
            raise HTTPForbidden(reason='You are not admin')
        return response
    return decorator


def get_login_url(request):
    return url_for('auth_login').with_query({
        cfg.BACK_URL_QS_KEY: request.path_qs})
