from aiohttp_jinja2 import template
from aiohttp_login import user_to_request, url_for, cfg, login_required
from markdown import markdown


with open('./README.md') as f:
    readme = markdown(f.read())


@user_to_request
@template('index.html')
async def index(request):
    return {
        'auth': {'cfg': cfg},
        'cur_user': request['user'],
        'url_for': url_for,
        'readme': readme,
    }


@login_required
@template('users.html')
async def users(request):
    async with request.app['db'].acquire() as conn:
        users = await conn.fetch('SELECT * FROM users ORDER BY created_at')
    return {
        'users': users,
    }
