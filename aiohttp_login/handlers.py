import logging

from aiohttp_jinja2 import render_template
from aiohttp_session import get_session

from .cfg import cfg
from . import forms
from . import oauth
from . import flash
from .decorators import login_required
from .utils import (encrypt_password, make_confirmation_link,
                    check_password, authorize_user, is_confirmation_allowed,
                    get_random_string, url_for, get_client_ip, redirect,
                    render_and_send_mail, is_confirmation_expired, themed,
                    common_themed, social_url)


log = logging.getLogger(__name__)


async def social(request):
    provider = request.match_info['provider']
    data = await getattr(oauth, provider)(request)
    db = cfg.STORAGE

    user = None
    while 'user_id' in data:
        # try to find user by provider_id
        user = await db.get_user({provider: data['user_id']})
        if user:
            break

        if data['email']:
            # try to find user by email
            user = await db.get_user({'email': data['email']})
            if user:
                await db.update_user(user, {provider: data['user_id']})
                break

            # register new user
            password = get_random_string(*cfg.PASSWORD_LEN)
            user = await db.create_user({
                'name': data['name'],
                'email': data['email'],
                'password': encrypt_password(password),
                'status': 'active',
                'created_ip': get_client_ip(request),
                provider: data['user_id'],
            })
            break
        break

    if user:
        await authorize_user(request, user)
        flash.success(request, cfg.MSG_LOGGED_IN)
        url = data['back_to'] or cfg.LOGIN_REDIRECT
        if provider in ['google', 'facebook']:
            return render_template(
                common_themed('http_redirect.html'),
                request, {'url': url})
        return redirect(url)

    flash.error(request, cfg.MSG_AUTH_FAILED)
    return redirect('auth_login')


async def registration(request):
    form = await forms.get('Registration').init(request)
    db = cfg.STORAGE

    while request.method == 'POST' and await form.validate():

        user = await db.create_user({
            'name': form.email.data.split('@')[0],
            'email': form.email.data,
            'password': encrypt_password(form.password.data),
            'status': ('confirmation' if cfg.REGISTRATION_CONFIRMATION_REQUIRED
                       else 'active'),
            'created_ip': get_client_ip(request),
        })

        if not cfg.REGISTRATION_CONFIRMATION_REQUIRED:
            await authorize_user(request, user)
            flash.success(request, cfg.MSG_LOGGED_IN)
            return redirect(cfg.LOGIN_REDIRECT)

        confirmation = await db.create_confirmation(user, 'registration')
        link = await make_confirmation_link(request, confirmation)
        try:
            await render_and_send_mail(
                request, form.email.data,
                common_themed('registration_email.html'), {
                    'host': request.host,
                    'link': link,
                })
        except Exception as e:
            log.error('Can not send email', exc_info=e)
            form.email.errors.append(cfg.MSG_CANT_SEND_MAIL)
            await db.delete_confirmation(confirmation)
            await db.delete_user(user)
            break

        return redirect('auth_registration_requested')

    return render_template(themed('registration.html'), request, {
        'auth': {
            'url_for': url_for,
            'cfg': cfg,
            'form': form,
            'social_url': social_url(request),
        }
    })


async def login(request):
    form = await forms.get('Login').init(request)

    while request.method == 'POST' and form.validate():

        user = await cfg.STORAGE.get_user({'email': form.email.data})
        if not user:
            form.email.errors.append(cfg.MSG_UNKNOWN_EMAIL)
            break

        if not check_password(form.password.data, user['password']):
            form.password.errors.append(cfg.MSG_WRONG_PASSWORD)
            break

        if user['status'] == 'banned':
            form.email.errors.append(cfg.MSG_USER_BANNED)
            break
        if user['status'] == 'confirmation':
            form.email.errors.append(cfg.MSG_ACTIVATION_REQUIRED)
            break
        assert user['status'] == 'active'

        await authorize_user(request, user)
        flash.success(request, cfg.MSG_LOGGED_IN)
        url = request.GET.get(cfg.BACK_URL_QS_KEY, cfg.LOGIN_REDIRECT)
        return redirect(url)

    return render_template(themed('login.html'), request, {
        'auth': {
            'url_for': url_for,
            'cfg': cfg,
            'form': form,
            'social_url': social_url(request),
        }
    })


async def logout(request):
    session = await get_session(request)
    session.pop(cfg.SESSION_USER_KEY, None)
    flash.info(request, cfg.MSG_LOGGED_OUT)
    return redirect(cfg.LOGOUT_REDIRECT)


async def reset_password(request):
    db = cfg.STORAGE
    form = await forms.get('ResetPasswordRequest').init(request)

    while request.method == 'POST' and form.validate():
        user = await db.get_user({'email': form.email.data})
        if not user:
            form.email.errors.append(cfg.MSG_UNKNOWN_EMAIL)
            break

        if user['status'] == 'banned':
            form.email.errors.append(cfg.MSG_USER_BANNED)
            break
        if user['status'] == 'confirmation':
            form.email.errors.append(cfg.MSG_ACTIVATION_REQUIRED)
            break
        assert user['status'] == 'active'

        if not await is_confirmation_allowed(user, 'reset_password'):
            form.email.errors.append(cfg.MSG_OFTEN_RESET_PASSWORD)
            break

        confirmation = await db.create_confirmation(user, 'reset_password')
        link = await make_confirmation_link(request, confirmation)
        try:
            await render_and_send_mail(
                request, form.email.data,
                common_themed('reset_password_email.html'), {
                    'host': request.host,
                    'link': link,
                })
        except Exception as e:
            log.error('Can not send email', exc_info=e)
            form.email.errors.append(cfg.MSG_CANT_SEND_MAIL)
            await db.delete_confirmation(confirmation)
            break

        return redirect('auth_reset_password_requested')

    return render_template(themed('reset_password.html'), request, {
        'auth': {
            'url_for': url_for,
            'cfg': cfg,
            'form': form,
        }
    })


async def reset_password_allowed(request, confirmation):
    db = cfg.STORAGE
    form = await forms.get('ResetPassword').init(request)
    user = await db.get_user({'id': confirmation['user_id']})
    assert user

    while request.method == 'POST' and form.validate():
        await db.update_user(
            user, {'password': encrypt_password(form.password.data)})
        await db.delete_confirmation(confirmation)
        await authorize_user(request, user)
        flash.success(request, cfg.MSG_PASSWORD_CHANGED)
        flash.success(request, cfg.MSG_LOGGED_IN)
        return redirect(cfg.LOGIN_REDIRECT)

    return render_template(themed('reset_password_allowed.html'), request, {
        'auth': {
            'url_for': url_for,
            'cfg': cfg,
            'form': form,
        }
    })


@login_required
async def change_email(request):
    db = cfg.STORAGE
    user = request[cfg.REQUEST_USER_KEY]
    form = await forms.get('ChangeEmail').init(
        request, email=user['email'])

    while request.method == 'POST' and form.validate(user['email']):
        confirmation = await db.get_confirmation(
            {'user': user, 'action': 'change_email'})
        if confirmation:
            await db.delete_confirmation(confirmation)

        confirmation = await db.create_confirmation(
            user, 'change_email', form.email.data)
        link = await make_confirmation_link(request, confirmation)
        try:
            await render_and_send_mail(
                request, form.email.data,
                common_themed('change_email_email.html'), {
                    'host': request.host,
                    'link': link,
                })
        except Exception as e:
            log.error('Can not send email', exc_info=e)
            form.email.errors.append(cfg.MSG_CANT_SEND_MAIL)
            await db.delete_confirmation(confirmation)
            break

        flash.success(request, cfg.MSG_CHANGE_EMAIL_REQUESTED)
        return redirect(request.path)

    return render_template(themed('change_email.html'), request, {
        'auth': {
            'cfg': cfg,
            'form': form
        }
    })


@login_required
async def change_password(request):
    db = cfg.STORAGE
    user = request[cfg.REQUEST_USER_KEY]
    form = await forms.get('ChangePassword').init(request)

    while request.method == 'POST' and form.validate():
        if not check_password(form.cur_password.data, user['password']):
            form.cur_password.errors.append(cfg.MSG_WRONG_PASSWORD)
            break

        password = encrypt_password(form.new_password.data)
        await db.update_user(user, {'password': password})

        flash.success(request, cfg.MSG_PASSWORD_CHANGED)
        return redirect(request.path)

    return render_template(themed('change_password.html'), request, {
        'auth': {
            'cfg': cfg,
            'form': form,
            'url_for': url_for,
        }
    })


async def confirmation(request):
    db = cfg.STORAGE
    code = request.match_info['code']

    confirmation = await db.get_confirmation({'code': code})
    if confirmation and is_confirmation_expired(confirmation):
        await db.delete_confirmation(confirmation)
        confirmation = None

    if confirmation:
        action = confirmation['action']

        if action == 'registration':
            user = await db.get_user({'id': confirmation['user_id']})
            await db.update_user(user, {'status': 'active'})
            await authorize_user(request, user)
            await db.delete_confirmation(confirmation)
            flash.success(request, cfg.MSG_ACTIVATED)
            flash.success(request, cfg.MSG_LOGGED_IN)
            return redirect(cfg.LOGIN_REDIRECT)

        if action == 'reset_password':
            return await reset_password_allowed(request, confirmation)

        if action == 'change_email':
            user = await db.get_user({'id': confirmation['user_id']})
            await db.update_user(user, {'email': confirmation['data']})
            await db.delete_confirmation(confirmation)
            flash.success(request, cfg.MSG_EMAIL_CHANGED)
            return redirect('auth_change_email')

    return render_template(themed('confirmation_error.html'), request)


def template_handler(template, context=None):
    async def handler(request):
        return render_template(themed(template), request, context)
    return handler
