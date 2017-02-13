from .cfg import cfg
from . import handlers
from .decorators import (login_required, admin_required, user_to_request,  # noqa
                         restricted_api)
from .utils import url_for  # noqa
from . import flash  # noqa


def setup(app, storage, config=None):
    config = (config or {}).copy()
    config['APP'] = app
    config['STORAGE'] = storage
    cfg.configure(config)

    add_route = app.router.add_route
    add_resource = app.router.add_resource

    # === Registration
    router = add_resource('/auth/registration/', name='auth_registration')
    router.add_route('GET', handlers.registration)
    router.add_route('POST', handlers.registration)

    add_route('GET', '/auth/registration/requested/',
              handlers.template_handler('registration_requested.html', {
                  'auth': {'cfg': cfg}}),
              name='auth_registration_requested')

    # === Login
    router = add_resource('/auth/login/', name='auth_login')
    router.add_route('GET', handlers.login)
    router.add_route('POST', handlers.login)

    # === Social login
    add_route('GET', '/auth/login/{provider:google|vkontakte|facebook}',
              handlers.social, name='auth_social')

    # === Logout
    add_route('GET', '/auth/logout/', handlers.logout, name='auth_logout')

    # === Reset password
    router = add_resource('/auth/reset-password/',
                          name='auth_reset_password')
    router.add_route('GET', handlers.reset_password)
    router.add_route('POST', handlers.reset_password)

    add_route('GET', '/auth/reset-password/requested',
              handlers.template_handler('reset_password_requested.html', {
                  'auth': {'cfg': cfg}}),
              name='auth_reset_password_requested')

    # === Change email
    router = add_resource('/auth/change-email/',
                          name='auth_change_email')
    router.add_route('GET', handlers.change_email)
    router.add_route('POST', handlers.change_email)

    # === Change password
    router = add_resource('/auth/change-password/',
                          name='auth_change_password')
    router.add_route('GET', handlers.change_password)
    router.add_route('POST', handlers.change_password)

    # === Email-based confirmation
    router = add_resource('/auth/confirmation/{code}',
                          name='auth_confirmation')
    router.add_route('GET', handlers.confirmation)
    router.add_route('POST', handlers.confirmation)

