from functools import wraps

from aiohttp.web import HTTPForbidden, json_response, StreamResponse
try:
    import ujson as json
except ImportError:
    import json

from .cfg import cfg
from .utils import url_for, redirect, get_cur_user


def user_to_request(handler):
    '''Add user to request if user logged in'''
    @wraps(handler)
    async def decorator(request):
        request[cfg.REQUEST_USER_KEY] = await get_cur_user(request)
        return await handler(request)
    return decorator


def login_required(handler):
    @user_to_request
    @wraps(handler)
    async def decorator(request):
        if not request[cfg.REQUEST_USER_KEY]:
            return redirect(get_login_url(request))
        return await handler(request)
    return decorator


def restricted_api(handler):
    @user_to_request
    @wraps(handler)
    async def decorator(request):
        if not request[cfg.REQUEST_USER_KEY]:
            return json_response({'error': 'Access denied'}, status=403)
        response = await handler(request)
        if not isinstance(response, StreamResponse):
            response = json_response(response, dumps=json.dumps)
        return response
    return decorator


def admin_required(handler):
    @wraps(handler)
    async def decorator(request):
        response = await login_required(handler)(request)
        if request['user']['email'] not in cfg.ADMIN_EMAILS:
            raise HTTPForbidden(reason='You are not admin')
        return response
    return decorator


def get_login_url(request):
    return url_for('auth_login').with_query({
        cfg.BACK_URL_QS_KEY: request.path_qs})
