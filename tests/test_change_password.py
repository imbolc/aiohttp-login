from utils import get_csrf, LoggedUser
from utils import *  # noqa
from aiohttp_login import cfg, url_for


NEW_PASSWORD = 'newpassword'


async def test_guest_access(client):
    r = await client.get(url_for('auth_change_password'))
    assert r.status == 200
    assert r.url_obj.path == url_for('auth_login').path


async def test_form_availibility(client):
    url = url_for('auth_change_password')
    async with LoggedUser(client):
        r = await client.get(url)
    assert r.status == 200
    assert r.url_obj.path == url.path


async def test_csrf(client):
    url = url_for('auth_change_password')
    async with LoggedUser(client) as user:
        r = await client.post(url, data={
            'cur_password': user['raw_password'],
            'new_password': NEW_PASSWORD,
            'confirm': NEW_PASSWORD,
        })
        assert r.url_obj.path == url.path
        assert r.status == 200
        assert 'CSRF token missing' in await r.text()

        r = await client.post(url, data={
            'cur_password': user['raw_password'],
            'new_password': NEW_PASSWORD,
            'confirm': NEW_PASSWORD,
            'csrf_token': '##wrong',
        })
        assert r.url_obj.path == url.path
        assert r.status == 200
        assert 'CSRF failed' in await r.text()


async def test_wrong_current_password(client):
    url = url_for('auth_change_password')
    r = await client.get(url)

    async with LoggedUser(client):
        r = await client.post(url, data={
            'cur_password': 'wrongpassword',
            'new_password': NEW_PASSWORD,
            'confirm': NEW_PASSWORD,
            'csrf_token': await get_csrf(r),
        })
        assert r.url_obj.path == url.path
        assert r.status == 200
        assert cfg.MSG_WRONG_PASSWORD in await r.text()


async def test_success(client):
    url = url_for('auth_change_password')
    login_url = url_for('auth_login')
    r = await client.get(url)

    async with LoggedUser(client) as user:
        r = await client.post(url, data={
            'cur_password': user['raw_password'],
            'new_password': NEW_PASSWORD,
            'confirm': NEW_PASSWORD,
            'csrf_token': await get_csrf(r),
        })
        assert r.url_obj.path == url.path
        assert r.status == 200
        assert cfg.MSG_PASSWORD_CHANGED in await r.text()

        r = await client.get(url_for('auth_logout'))
        assert r.status == 200
        assert r.url_obj.path == login_url.path

        r = await client.post(login_url, data={
            'email': user['email'],
            'password': NEW_PASSWORD,
            'csrf_token': await get_csrf(r),
        })
        assert r.status == 200
        assert r.url_obj.path == url_for(cfg.LOGIN_REDIRECT).path
        assert cfg.MSG_LOGGED_IN in await r.text()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '--maxfail=1'])
