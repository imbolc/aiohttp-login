'''
Response: {
    user_id: str,
    email: str or None,
    name: str,
    back_url: str of None
} or {} if error occured
'''
import logging
from pprint import pformat

import aiohttp
from yarl import URL
from aiohttp.web import HTTPFound

from .cfg import cfg


log = logging.getLogger(__name__)


async def vkontakte(request):
    if 'error' in request.GET:
        return {}

    common_params = {
        'client_id': cfg.VKONTAKTE_ID,
        'redirect_uri': str(request.url.with_query(None)),
        'v': '5.60',
    }

    # Step 1: redirect browser to login dialog
    if 'code' not in request.GET:
        url = 'http://api.vkontakte.ru/oauth/authorize'
        params = common_params.copy()
        params['scope'] = 'email'
        if cfg.BACK_URL_QS_KEY in request.GET:
            params['state'] = request.GET[cfg.BACK_URL_QS_KEY]
        raise HTTPFound(URL(url).with_query(params))

    # Step 2: get access token
    url = 'https://oauth.vk.com/access_token'
    params = common_params.copy()
    params.update({
        'client_secret': cfg.VKONTAKTE_SECRET,
        'code': request.GET['code'],
    })
    async with aiohttp.ClientSession(loop=request.app.loop) as client:
        async with client.get(URL(url).with_query(params)) as resp:
            data = await resp.json()
        if 'user_id' not in data:
            log.error('Vkontakte: no user_id in data: %s', data)
            return {}

        # get user profile
        url = URL('https://api.vk.com/method/users.get').with_query(
            access_token=data['access_token'],
            uid=data['user_id'],
            fields='nickname,screen_name'
        )
        async with client.get(url) as resp:
            profile = await resp.json()

    assert 'response' in profile, profile
    profile = profile['response'][0]
    log.debug('vk profile: %s', pformat(profile))
    name = (profile['screen_name'] or profile['nickname']
            or profile['first_name'])
    if not name and 'email' in data:
        name = data['email'].split('@')[0]
    if not name:
        name = str(data['user_id'])
    return {
        'user_id': str(data['user_id']),
        'email': data.get('email'),
        'name': name,
        'back_to': request.GET.get('state'),
    }


async def google(request):
    if 'error' in request.GET:
        return {}

    common_params = {
        'client_id': cfg.GOOGLE_ID,
        'redirect_uri': str(request.url.with_query(None)),
    }

    # Step 1: redirect to get code
    if 'code' not in request.GET:
        url = 'https://accounts.google.com/o/oauth2/auth'
        params = common_params.copy()
        params.update({
            'response_type': 'code',
            'scope': ('https://www.googleapis.com/auth/userinfo.profile'
                      ' https://www.googleapis.com/auth/userinfo.email'),
        })
        if cfg.BACK_URL_QS_KEY in request.GET:
            params['state'] = request.GET[cfg.BACK_URL_QS_KEY]
        url = URL(url).with_query(params)
        raise HTTPFound(url)

    # Step 2: get access token
    url = 'https://accounts.google.com/o/oauth2/token'
    params = common_params.copy()
    params.update({
        'client_secret': cfg.GOOGLE_SECRET,
        'code': request.GET['code'],
        'grant_type': 'authorization_code',
    })
    async with aiohttp.ClientSession(loop=request.app.loop) as client:
        async with client.post(url, data=params) as resp:
            data = await resp.json()
        assert 'access_token' in data, data
        log.debug('data: %s', pformat(data))

        # get user profile
        headers = {'Authorization': 'Bearer ' + data['access_token']}
        url = 'https://www.googleapis.com/plus/v1/people/me'
        async with client.get(url, headers=headers) as resp:
            profile = await resp.json()

    log.debug('g+ profile: %s', pformat(profile))

    email = None
    for e in profile.get('emails', []):
        if e['type'] == 'account':
            email = e['value']
            break

    name = profile['displayName'] or profile.get('name', {}).get('givenName')
    if not name:
        if email:
            name = email.split('@')[0]
        else:
            name = str(data['id'])
    return {
        'user_id': profile['id'],
        'email': email,
        'name': name,
        'back_to': request.GET.get('state'),
    }


async def facebook(request):
    if 'error' in request.GET:
        return {}

    common_params = {
        'client_id': cfg.FACEBOOK_ID,
        'redirect_uri': str(request.url.with_query(None)),
    }

    # Step 1: redirect to get code
    if 'code' not in request.GET:
        params = common_params.copy()
        params.update({
            'response_type': 'code',
            'scope': 'email',
        })
        if cfg.BACK_URL_QS_KEY in request.GET:
            params['state'] = request.GET[cfg.BACK_URL_QS_KEY]
        url = URL(
            'https://www.facebook.com/v2.8/dialog/oauth').with_query(params)
        raise HTTPFound(url)

    # Step 2: get access token
    url = URL('https://graph.facebook.com/v2.8/oauth/access_token').with_query(
        dict(
            common_params,
            client_secret=cfg.FACEBOOK_SECRET,
            code=request.GET['code'],
        ))
    async with aiohttp.ClientSession(loop=request.app.loop) as client:
        async with client.get(url) as resp:
            data = await resp.json()
        assert 'access_token' in data, data

        # get profile
        url = URL('https://graph.facebook.com/v2.8/me').with_query(
            fields='id,email,first_name',
            access_token=data['access_token'])
        async with client.get(url) as resp:
            profile = await resp.json()
        log.debug('facebook profile: %s', pformat(profile))

    email = profile.get('email')
    name = profile.get('first_name')
    if not name:
        if email:
            name = email.split('@')[0]
        else:
            name = str(profile['id'])

    return {
        'user_id': profile['id'],
        'email': email,
        'name': name,
        'back_to': request.GET.get('state'),
    }
