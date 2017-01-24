from functools import lru_cache

from aiohttp_session import get_session
from wtforms import Form, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import Required, EqualTo, Length, Email
from wtforms.csrf.session import SessionCSRF

from .cfg import cfg
from .utils import is_confirmation_expired


def get(name):
    return create()[name]


@lru_cache()
def create():
    # We don't have real settings on import stage, so we need to defer
    # initialization of forms

    class BaseForm(Form):
        @classmethod
        async def init(cls, request, *args, **kwargs):
            session = await get_session(request)
            kwargs.setdefault('meta', {})['csrf_context'] = session
            return cls(await request.post(), *args, **kwargs)

        class Meta:
            csrf = True
            csrf_class = SessionCSRF
            csrf_secret = cfg.CSRF_SECRET.encode('utf-8')
            csrf_time_limit = None

            def bind_field(self, form, unbound_field, options):
                # auto add strip_filter
                filters = unbound_field.kwargs.get('filters', [])
                filters.append(strip_filter)
                return unbound_field.bind(
                    form=form, filters=filters, **options)

        def validate(self):
            result = super().validate()
            if 'csrf_token' in self.errors:
                for field in self:
                    field.errors.append(self.errors['csrf_token'][0])
                    break
            return result

    def strip_filter(value):
        if value is not None and hasattr(value, 'strip'):
            return value.strip()
        return value

    class Registration(BaseForm):
        email = EmailField('Email', [
            Required(),
            Email(),
        ])
        password = PasswordField('Password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
            EqualTo('confirm', message=cfg.MSG_PASSWORDS_NOT_MATCH),
        ])
        confirm = PasswordField('Repeat password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
        ])

        async def validate(self):
            db = cfg.STORAGE
            if not super().validate():
                return False

            user = await db.get_user({'email': self.email.data})
            if not user:
                return True

            if user['status'] == 'confirmation':
                confirmation = await db.get_confirmation(
                    {'user': user, 'action': 'registration'})

                if is_confirmation_expired(confirmation):
                    await db.delete_confirmation(confirmation)
                    await db.delete_user(user)
                    return True

            self.email.errors.append(cfg.MSG_EMAIL_EXISTS)
            return False

    class Login(BaseForm):
        email = EmailField('Email', [
            Required(),
            Email(),
        ])
        password = PasswordField('Password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
        ])

    class ResetPasswordRequest(BaseForm):
        email = EmailField('Email', [
            Required(),
            Email(),
        ])

    class ResetPassword(BaseForm):
        password = PasswordField('New password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
            EqualTo('confirm', message=cfg.MSG_PASSWORDS_NOT_MATCH),
        ])
        confirm = PasswordField('Repeat password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
        ])

    class ChangeEmail(BaseForm):
        email = EmailField('New email', [Email()])

        def validate(self, cur_email):
            return super().validate() and self.email.data != cur_email

    class ChangePassword(BaseForm):
        cur_password = PasswordField('Current password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
        ])
        new_password = PasswordField('New password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
            EqualTo('confirm', message=cfg.MSG_PASSWORDS_NOT_MATCH),
        ])
        confirm = PasswordField('Repeat new password', [
            Required(),
            Length(*cfg.PASSWORD_LEN),
        ])

    return locals()
