#!venv/bin/python
import asyncio
import logging

from aiohttp import web
import aiohttp_jinja2
import jinja_app_loader
import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import asyncpg

import aiohttp_login
from aiohttp_login.asyncpg_storage import AsyncpgStorage

import handlers
import settings


async def create_app(loop):
    app = web.Application(loop=loop, debug=settings.DEBUG)
    setup_jinja(app, settings.DEBUG)
    aiohttp_session.setup(app, EncryptedCookieStorage(
        settings.SESSION_SECRET.encode('utf-8'),
        max_age=settings.SESSION_MAX_AGE))
    app.middlewares.append(aiohttp_login.flash.middleware)

    app.router.add_get('/', handlers.index)
    app.router.add_get('/users/', handlers.users, name='users')

    app['db'] = await asyncpg.create_pool(dsn=settings.DATABASE, loop=loop)
    aiohttp_login.setup(app, AsyncpgStorage(app['db']), settings.AUTH)

    return app


def setup_jinja(app, debug):
    env = aiohttp_jinja2.setup(
        app,
        loader=jinja_app_loader.Loader(),
        auto_reload=debug,
        context_processors=[
            aiohttp_login.flash.context_processor,
        ],
    )
    return env


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(name)-8s %(message)s')
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(create_app(loop))
    web.run_app(app, port=settings.PORT)
