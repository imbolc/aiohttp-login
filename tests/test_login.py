from utils import get_csrf, NewUser
from utils import *  # noqa
from aiohttp_login import cfg, url_for


EMAIL, PASSWORD = 'tester@test.com', 'password'


async def test_login_availibility(client):
    r = await client.get(url_for('auth_login'))
    assert r.status == 200


async def test_login_csrf(client):
    url = url_for('auth_login')
    r = await client.post(url, data={
        'email': EMAIL,
        'password': PASSWORD,
    })
    assert r.status == 200
    assert 'CSRF token missing' in await r.text()

    r = await client.post(url, data={
        'email': EMAIL,
        'password': PASSWORD,
        'csrf_token': '##wrong',
    })
    assert r.status == 200
    assert 'CSRF failed' in await r.text()


async def test_login_with_unknown_email(client):
    url = url_for('auth_login')
    r = await client.get(url)
    assert cfg.MSG_UNKNOWN_EMAIL not in await r.text()
    r = await client.post(url, data={
        'email': 'unknown@email.com',
        'password': 'wrong.',
        'csrf_token': await get_csrf(r),
    })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_UNKNOWN_EMAIL in await r.text()


async def test_login_with_wrong_password(client):
    url = url_for('auth_login')
    r = await client.get(url)
    assert cfg.MSG_WRONG_PASSWORD not in await r.text()

    async with NewUser() as user:
        r = await client.post(url, data={
            'email': user['email'],
            'password': 'wrong.',
            'csrf_token': await get_csrf(r),
        })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_WRONG_PASSWORD in await r.text()


async def test_login_banned_user(client):
    url = url_for('auth_login')
    r = await client.get(url)
    assert cfg.MSG_USER_BANNED not in await r.text()

    async with NewUser({'status': 'banned'}) as user:
        r = await client.post(url, data={
            'email': user['email'],
            'password': user['raw_password'],
            'csrf_token': await get_csrf(r),
        })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_USER_BANNED in await r.text()


async def test_login_inactive_user(client):
    url = url_for('auth_login')
    r = await client.get(url)
    assert cfg.MSG_ACTIVATION_REQUIRED not in await r.text()

    async with NewUser({'status': 'confirmation'}) as user:
        r = await client.post(url, data={
            'email': user['email'],
            'password': user['raw_password'],
            'csrf_token': await get_csrf(r),
        })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_ACTIVATION_REQUIRED in await r.text()


async def test_login_successfully(client):
    url = url_for('auth_login')
    r = await client.get(url)
    async with NewUser() as user:
        r = await client.post(url, data={
            'email': user['email'],
            'password': user['raw_password'],
            'csrf_token': await get_csrf(r),
        })
    assert r.status == 200
    assert r.url_obj.path == url_for(cfg.LOGIN_REDIRECT).path
    assert cfg.MSG_LOGGED_IN in await r.text()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '--maxfail=1'])
