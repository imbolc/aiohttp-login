import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # noqa

import pytest
from aiohttp import web
import aiohttp_jinja2
import jinja_app_loader
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp_session import session_middleware, SimpleCookieStorage
import asyncpg
from yarl import URL

import aiohttp_login.utils
from aiohttp_login.utils import get_random_string, encrypt_password
from aiohttp_login.asyncpg_storage import AsyncpgStorage
from aiohttp_login.motor_storage import MotorStorage
from aiohttp_login import cfg, url_for, restricted_api


DATABASE = 'aiohttp_login_tests'


def pytest_generate_tests(metafunc):
    if 'client' in metafunc.fixturenames:
        metafunc.parametrize('client', ['asyncpg', 'motor'], indirect=True)


async def create_app(loop, db):
    app = web.Application(loop=loop, middlewares=[
        session_middleware(SimpleCookieStorage()),
    ])
    app.middlewares.append(aiohttp_login.flash.middleware)
    aiohttp_jinja2.setup(
        app,
        loader=jinja_app_loader.Loader(),
        context_processors=[aiohttp_login.flash.context_processor],
    )

    if db == 'asyncpg':
        pool = await asyncpg.create_pool(
            dsn='postgres:///' + DATABASE, loop=loop)
        storage = AsyncpgStorage(pool)
    elif db == 'motor':
        app['db'] = AsyncIOMotorClient(io_loop=loop)[DATABASE]
        storage = MotorStorage(app['db'])
    else:
        assert 0, 'unknown storage'

    aiohttp_login.setup(app, storage, {
        'CSRF_SECRET': 'secret',
        'LOGIN_REDIRECT': 'auth_change_email',
        'SMTP_SENDER': 'Your Name <your@gmail.com>',
        'SMTP_HOST': 'smtp.gmail.com',
        'SMTP_PORT': 465,
        'SMTP_USERNAME': 'your@gmail.com',
        'SMTP_PASSWORD': 'password'
    })

    @restricted_api
    async def api_hello_handler(request):
        return {'hello': 'world'}

    app.router.add_get('/api/hello', api_hello_handler, name='api_hello')

    return app


async def get_csrf(r):
    text = await r.text()
    return text.split('name="csrf_token" type="hidden" value="')[1].split(
        '"')[0]


@pytest.fixture
def client(loop, test_client, monkeypatch, request):
    path_mail(monkeypatch)
    app = loop.run_until_complete(create_app(loop, db=request.param))
    loop.run_until_complete(prepare_db(app, request.param))
    client = loop.run_until_complete(test_client(app))
    return client


def path_mail(monkeypatch):
    async def send_mail(*args):
        print('=== EMAIL TO: {}\n=== SUBJECT: {}\n=== BODY:\n{}'.format(*args))

    monkeypatch.setattr(aiohttp_login.utils, 'send_mail', send_mail)


async def prepare_db(app, db):
    if db == 'asyncpg':
        os.system('psql -d {} -f aiohttp_login/pg_tables.sql'.format(DATABASE))
    elif db == 'motor':
        await app['db']['users'].remove({})
        await app['db']['confirmations'].remove({})
    else:
        assert 0, 'Unknown db'


async def log_client_in(client, user_data=None):
    user = await create_user(user_data)
    url = url_for('auth_login')
    r = await client.get(url)
    assert r.status == 200
    r = await client.post(url, data={
        'email': user['email'],
        'password': user['raw_password'],
        'csrf_token': await get_csrf(r),
    })
    assert cfg.MSG_LOGGED_IN in await r.text()
    assert r.url_obj.path == url_for(cfg.LOGIN_REDIRECT).path
    return user


class NewUser:
    def __init__(self, params=None):
        self.params = params

    async def __aenter__(self):
        self.user = await create_user(self.params)
        return self.user

    async def __aexit__(self, *args):
        await cfg.STORAGE.delete_user(self.user)


class LoggedUser(NewUser):
    def __init__(self, client, params=None):
        self.client = client
        self.params = params

    async def __aenter__(self):
        self.user = await log_client_in(self.client, self.params)
        return self.user


async def create_user(data=None):
    data = data or {}
    password = get_random_string(10)
    params = {
        'name': get_random_string(10),
        'email': '{}@gmail.com'.format(get_random_string(10)),
        'password': encrypt_password(password)
    }
    params.update(data)
    params.setdefault('status', 'active')
    params.setdefault('created_ip', '127.0.0.1')
    user = await cfg.STORAGE.create_user(params)
    user['raw_password'] = password
    return user


def parse_link(text):
    link = text.split('<a href="')[1].split('"')[0]
    assert '/auth/confirmation/' in link
    return URL(link).path
