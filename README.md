aiohttp-login
=============
Registration and authorization (including social) for aiohttp apps

With just a few settings you'll give for your [aiohttp][] site:

- registration with email confirmation
- authorization by email or social account
  (facebook, google and vkontakte for now)
- reset password by email
- change email with confirmation
- edit current password

You can see all of this staff alive [here][example]

Databases
---------
You can use this lib with different database backends:

- postgres with [asyncpg][]
- mongodb with [motor][]
- the db you need - *it's very easy to add a new backend*


UI themes
---------
The library designed to easily change UI themes.
Currently `bootstrap-3` and `bootstrap-4` themes are available.
But it's very easy to add new themes, actually theme - is just a folder
with jinja2 templates.


Installation and configuration
------------------------------
Just install the library from pypi:

    pip install aiohttp-login

Choice and configure one of database storages.

For postgres with [asyncpg][]:
```python
import asyncpg
from aiohttp_login.asyncpg_storage import AsyncpgStorage

pool = await asyncpg.create_pool(dsn='postgres:///your_db')
storage = AsyncpgStorage(pool)
```

For mongodb with [motor][]:
```python
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp_login.motor_storage import MotorStorage

db = AsyncIOMotorClient(io_loop=loop)['your_db']
storage = MotorStorage(db)
```

Now configure the library with a few settings:
```python
app = web.Application(loop=loop)
app.middlewares.append(aiohttp_login.flash.middleware)
aiohttp_jinja2.setup(
    app,
    loader=jinja_app_loader.Loader(),
    context_processors=[aiohttp_login.flash.context_processor],
)
aiohttp_login.setup(app, storage, {
    'CSRF_SECRET': 'secret',

    'VKONTAKTE_ID': 'your-id',
    'VKONTAKTE_SECRET': 'your-secret',
    'GOOGLE_ID': 'your-id',
    'GOOGLE_SECRET': 'your-secret',
    'FACEBOOK_ID': 'your-id',
    'FACEBOOK_SECRET': 'your-secret',

    'SMTP_SENDER': 'Your Name <your@gmail.com>',
    'SMTP_HOST': 'smtp.gmail.com',
    'SMTP_PORT': 465,
    'SMTP_USERNAME': 'your@gmail.com',
    'SMTP_PASSWORD': 'password'
})
```

That's all. Look at the [live example][example] and its code in the
[example][example-repo] folder.
Full list of available settings you can find in
[aiohttp_login/cfg.py][cfg] file.


Run the example
---------------
Create a virtual environment and install the dependencies:

    cd example
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Create postgres database and tables:

    createdb aiohttp_login
    psql -d aiohttp_login -f ../aiohttp_login/pg_tables.sql

Rename `settings.py.template` to `settings.py` and populate it with real data.

Run the server:

    python app.py


Run tests
---------

    pip install -r requirements-dev.txt
    py.test


[repo]: https://github.com/imbolc/aiohttp-login
[example]: http://aiohttp-login.imbolc.name/
[example-repo]: https://github.com/imbolc/aiohttp-login/tree/master/example
[aiohttp]: https://github.com/KeepSafe/aiohttp
[asyncpg]: https://github.com/MagicStack/asyncpg
[motor]: https://github.com/mongodb/motor
[cfg]: https://github.com/imbolc/aiohttp-login/blob/master/aiohttp_login/cfg.py
