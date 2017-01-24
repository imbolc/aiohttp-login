from utils import get_csrf, parse_link, LoggedUser
from utils import *  # noqa
from aiohttp_login import cfg, url_for


NEW_EMAIL = 'new@gmail.com'


async def test_guest_access(client):
    r = await client.get(url_for('auth_change_email'))
    assert r.status == 200
    assert r.url_obj.path == url_for('auth_login').path


async def test_form_availibility(client):
    url = url_for('auth_change_email')
    async with LoggedUser(client):
        r = await client.get(url)
    assert r.status == 200
    assert r.url_obj.path == url.path


async def test_csrf(client):
    url = url_for('auth_change_email')
    async with LoggedUser(client):
        r = await client.post(url, data={
            'email': NEW_EMAIL,
        })
        assert r.url_obj.path == url.path
        assert r.status == 200
        assert 'CSRF token missing' in await r.text()

        r = await client.post(url, data={
            'email': NEW_EMAIL,
            'csrf_token': '##wrong',
        })
        assert r.url_obj.path == url.path
        assert r.status == 200
        assert 'CSRF failed' in await r.text()


async def test_cnange_and_confirm(client, capsys):
    url = url_for('auth_change_email')
    login_url = url_for('auth_login')
    r = await client.get(url)

    async with LoggedUser(client) as user:
        r = await client.post(url, data={
            'email': NEW_EMAIL,
            'csrf_token': await get_csrf(r),
        })
        assert r.status == 200
        assert r.url_obj.path == url.path
        assert cfg.MSG_CHANGE_EMAIL_REQUESTED in await r.text()

        out, err = capsys.readouterr()
        link = parse_link(out)

        r = await client.get(link)
        assert r.status == 200
        assert r.url_obj.path == url.path
        assert cfg.MSG_EMAIL_CHANGED in await r.text()

        r = await client.get(url_for('auth_logout'))
        assert r.status == 200
        assert r.url_obj.path == login_url.path

        r = await client.post(login_url, data={
            'email': NEW_EMAIL,
            'password': user['raw_password'],
            'csrf_token': await get_csrf(r),
        })
        assert r.status == 200
        assert r.url_obj.path == url_for(cfg.LOGIN_REDIRECT).path
        assert cfg.MSG_LOGGED_IN in await r.text()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '--maxfail=1'])
