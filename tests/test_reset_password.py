from utils import get_csrf, NewUser, parse_link
from utils import *  # noqa
from aiohttp_login import cfg, url_for
from aiohttp_login.utils import get_random_string


EMAIL, PASSWORD = 'tester@test.com', 'password'


async def test_form_availibility(client):
    reset_url = url_for('auth_reset_password')
    r = await client.get(reset_url)
    assert r.status == 200
    assert r.url_obj.path == reset_url.path


async def test_csrf(client):
    reset_url = url_for('auth_reset_password')
    r = await client.post(reset_url, data={
        'email': EMAIL,
    })
    assert r.url_obj.path == reset_url.path
    assert r.status == 200
    assert 'CSRF token missing' in await r.text()

    r = await client.post(reset_url, data={
        'email': EMAIL,
        'csrf_token': '##wrong',
    })
    assert r.url_obj.path == reset_url.path
    assert r.status == 200
    assert 'CSRF failed' in await r.text()


async def test_unknown_email(client):
    url = url_for('auth_reset_password')
    r = await client.get(url)
    assert r.url_obj.path == url.path
    assert cfg.MSG_UNKNOWN_EMAIL not in await r.text()

    r = await client.post(url, data={
        'email': EMAIL,
        'csrf_token': await get_csrf(r),
    })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_UNKNOWN_EMAIL in await r.text()


async def test_banned_user(client):
    url = url_for('auth_reset_password')
    r = await client.get(url)
    assert r.url_obj.path == url.path
    assert cfg.MSG_USER_BANNED not in await r.text()

    async with NewUser({'status': 'banned'}) as user:
        r = await client.post(url, data={
            'email': user['email'],
            'csrf_token': await get_csrf(r),
        })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_USER_BANNED in await r.text()


async def test_inactive_user(client):
    url = url_for('auth_reset_password')
    r = await client.get(url)
    assert cfg.MSG_ACTIVATION_REQUIRED not in await r.text()

    async with NewUser({'status': 'confirmation'}) as user:
        r = await client.post(url, data={
            'email': user['email'],
            'csrf_token': await get_csrf(r),
        })
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_ACTIVATION_REQUIRED in await r.text()


async def test_too_often(client):
    db = cfg.STORAGE
    url = url_for('auth_reset_password')
    r = await client.get(url)
    assert cfg.MSG_OFTEN_RESET_PASSWORD not in await r.text()

    async with NewUser() as user:
        confirmation = await db.create_confirmation(user, 'reset_password')
        r = await client.post(url, data={
            'email': user['email'],
            'csrf_token': await get_csrf(r),
        })
        await db.delete_confirmation(confirmation)
    assert r.status == 200
    assert r.url_obj.path == url.path
    assert cfg.MSG_OFTEN_RESET_PASSWORD in await r.text()


async def test_reset_and_confirm(client, capsys):
    url = url_for('auth_reset_password')
    login_url = url_for('auth_login')
    r = await client.get(url)

    async with NewUser() as user:
        r = await client.post(url, data={
            'email': user['email'],
            'csrf_token': await get_csrf(r),
        })
        assert r.status == 200
        assert r.url_obj.path == url_for('auth_reset_password_requested').path

        out, err = capsys.readouterr()
        confirmation_url = parse_link(out)
        r = await client.get(confirmation_url)
        assert r.status == 200

        new_password = get_random_string(10)
        r = await client.post(confirmation_url, data={
            'password': new_password,
            'confirm': new_password,
            'csrf_token': await get_csrf(r),
        })
        assert r.status == 200
        assert r.url_obj.path == url_for(cfg.LOGIN_REDIRECT).path
        assert cfg.MSG_PASSWORD_CHANGED in await r.text()
        assert cfg.MSG_LOGGED_IN in await r.text()

        r = await client.get(url_for('auth_logout'))
        assert r.status == 200
        assert r.url_obj.path == login_url.path

        r = await client.post(login_url, data={
            'email': user['email'],
            'password': new_password,
            'csrf_token': await get_csrf(r),
        })
        assert r.status == 200
        assert r.url_obj.path == url_for(cfg.LOGIN_REDIRECT).path
        assert cfg.MSG_LOGGED_IN in await r.text()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '--maxfail=1'])
