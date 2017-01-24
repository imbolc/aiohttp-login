from utils import log_client_in
from utils import *  # noqa
from aiohttp_login import cfg, url_for


async def test_logout(client):
    login_url = url_for('auth_login')
    change_email_url = url_for('auth_change_email')
    user = await log_client_in(client)

    # try to access protected page
    r = await client.get(change_email_url)
    assert r.url_obj.path == change_email_url.path

    # logout
    r = await client.get(url_for('auth_logout'))
    assert r.status == 200
    assert r.url_obj.path == login_url.path

    # and try again
    r = await client.get(change_email_url)
    assert r.url_obj.path == login_url.path

    await cfg.STORAGE.delete_user(user)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '--maxfail=1'])
