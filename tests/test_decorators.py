from utils import log_client_in
from utils import *  # noqa
from aiohttp_login import cfg, url_for


async def test_restricred_api(client):
    api_url = url_for('api_hello')
    r = await client.get(api_url)
    assert r.url_obj.path == api_url.path
    assert r.status == 403
    assert 'Access denied' in await r.text()

    user = await log_client_in(client)

    r = await client.get(api_url)
    assert r.url_obj.path == api_url.path
    assert r.status == 200
    assert 'hello' in await r.text()

    await cfg.STORAGE.delete_user(user)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '--maxfail=1'])
