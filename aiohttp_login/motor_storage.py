from logging import getLogger
from datetime import datetime

from bson.objectid import ObjectId
from bson.errors import InvalidId

from .utils import get_random_string, get_client_ip


log = getLogger(__name__)


class MotorStorage:
    def __init__(self, db, *,
                 user_coll_name='users',
                 confirmation_coll_name='confirmations'):
        self.users = db[user_coll_name]
        self.confirmations = db[confirmation_coll_name]

    async def get_user(self, filter):
        if 'id' in filter:
            filter['_id'] = filter.pop('id')
        return await self.users.find_one(filter)

    async def create_user(self, data):
        data.setdefault('created_at', datetime.utcnow())
        data['_id'] = await self.users.insert(data)
        return data

    def update_user(self, user, updates):
        return self.users.update({'_id': user['_id']}, {'$set': updates})

    def delete_user(self, user):
        return self.users.remove({'_id': user['_id']})

    async def create_confirmation(self, user, action, data=None):
        while True:
            code = get_random_string(30)
            if not await self.confirmations.find_one(code):
                break

        confirmation = {
            'code': code,
            'user_id': user['_id'],
            'action': action,
            'data': data,
            'created_at': datetime.utcnow(),
        }
        await self.confirmations.insert(confirmation)
        return confirmation

    def get_confirmation(self, filter):
        if 'user' in filter:
            filter['user_id'] = filter.pop('user')['_id']
        return self.confirmations.find_one(filter)

    def delete_confirmation(self, confirmation):
        return self.confirmations.remove(confirmation['_id'])

    def user_id_from_string(self, id_str):
        try:
            return ObjectId(id_str)
        except (TypeError, InvalidId) as ex:
            log.error('Can\'t convert string into id', exc_info=ex)

    def user_session_id(self, user):
        return str(user['_id'])
