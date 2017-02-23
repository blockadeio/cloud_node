"""Basic REST API interface for Blockade."""
import datetime
import hashlib
import random
from flask import request
from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_pymongo import PyMongo

CONST_CORE_DB = 'blockade'
CONST_EXT_KEY = 'EXTMONGO'
CONST_PYMONGO = 'pymongo'

app = Flask(__name__)
app.config['MONGO_DBNAME'] = CONST_CORE_DB
api = Api(app)
mongo = PyMongo(app)

parser = reqparse.RequestParser()
parser.add_argument('api_key')
parser.add_argument('email')
parser.add_argument('events')
parser.add_argument('indicators')
parser.add_argument('user_email')
parser.add_argument('user_name')
parser.add_argument('user_role')


def check_auth(args, role=None):
    """Check the user authentication."""
    if mongo.db.users.count() == 0:
        return {'success': True, 'message': None}
    if not (args.get('email', None) and args.get('api_key', None)):
        mesg = "Invalid request: `email` and `api_key` are required"
        return {'success': False, 'message': mesg}
    user = mongo.db.users.find_one({'email': args['email']}, {'_id': 0})
    if not user:
        return {'success': False, 'message': 'User does not exist.'}
    if user['api_key'] != args['api_key']:
        return {'success': False, 'message': 'API key was invalid.'}
    if role:
        if user['role'] not in role:
            mesg = 'User is not authorized to make this change.'
            return {'success': False, 'message': mesg}
    return {'success': True, 'message': None, 'user': user}


def db_setup(f):
    """Handle tasking before and after any wrapped calls.

    For channels, we want the user to be able to specify which database to
    pull or send data to based on the URL slug. After loading a PyMongo
    instance, it will pollute the session space and throw errors unless cleaned
    up. Wrapping methods that require the database to be dynamic lets us do
    the needed session setup and tear-down for any call.
    """
    def wrapper(self, sub_id=None):
        if not sub_id:
            sub_id = CONST_CORE_DB
        # Silently drop any non-DB name characters
        sub_id = ''.join(e for e in sub_id if e.isalnum() or e == '_')
        app.config[CONST_EXT_KEY + "_DBNAME"] = sub_id
        ext_mongo = PyMongo(app, config_prefix=CONST_EXT_KEY)
        results = f(self, ext_mongo)
        for key in app.config.keys():
            if not key.startswith(CONST_EXT_KEY):
                continue
            app.config.pop(key, None)
        app.extensions[CONST_PYMONGO].pop(CONST_EXT_KEY, None)
        return results
    return wrapper


class ExtensionActions(Resource):

    """Endpoints for the pubic uses for information."""

    @db_setup
    def get(self, ext_mongo):
        """Get the indicators from the database."""
        output = {'success': True, 'indicators': list(), 'indicatorCount': 0}
        indicators = [x for x in ext_mongo.db.indicators.find({}, {'_id': 0})]
        for item in indicators:
            indicator = item.get('indicator', None)
            if not indicator:
                continue
            output['indicators'].append(indicator)
        output['indicators'] = list(set(output['indicators']))
        output['indicatorCount'] = len(output['indicators'])
        return output

    @db_setup
    def post(self, ext_mongo):
        """Save the events into the local database."""
        args = request.get_json(force=True)
        events = args.get('events', list())
        if len(events) == 0:
            return {'success': False, 'message': "No events sent in"}
        for idx, event in enumerate(events):
            event['sourceIp'] = request.remote_addr
            event['event'] = hashlib.sha256(str(event)).hexdigest()
            metadata = event['metadata']
            timestamp = str(event['metadata']['timeStamp'])
            events[idx]['metadata']['timeStamp'] = timestamp
            obj = {
                'match': event['indicatorMatch'],
                'type': metadata['type'],
                'url': metadata['url'],
                'method': metadata['method'].lower(),
                'time': event['analysisTime'],
                'userAgent': event['userAgent'],
                'ip': request.remote_addr
            }
            ext_mongo.db.events.insert(obj)
        mesg = "Wrote {} events to the cloud".format(len(events))
        return {'success': True, 'message': mesg}


class IndicatorIngest(Resource):

    """Perform actions related to indicators."""

    def post(self):
        """Save indicators into the local database."""
        args = request.get_json(force=True)
        auth = check_auth(args, role=["analyst", "admin"])
        if not auth['success']:
            return auth
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        indicators = args.get('indicators', list())
        for item in indicators:
            #  Expecting MD5 indicators, nothing else.
            if len(item) != 32:
                continue
            obj = {'indicator': item, 'creator': auth['user']['email'],
                   'datetime': current_time}
            mongo.db.indicators.insert(obj)
        msg = "Wrote {} indicators".format(len(indicators))
        return {'success': True, 'message': msg, 'writeCount': len(indicators)}


class EventsManagement(Resource):

    """Perform actions related to events."""

    def get(self):
        """Get recorded events."""
        args = parser.parse_args()
        auth = check_auth(args, role=["analyst", "admin"])
        if not auth['success']:
            return auth

        output = {'success': True, 'events': list(), 'eventsCount': 0}
        output['events'] = [x for x in mongo.db.events.find({}, {'_id': 0})]
        output['eventsCount'] = len(output['events'])
        return output

class UserManagement(Resource):

    """Perform actions related to users."""

    def post(self):
        """Added new users to the system."""
        args = parser.parse_args()
        auth = check_auth(args, role=["admin"])
        if not auth['success']:
            return auth
        user_email = args.get('user_email', None)
        if not user_email:
            msg = "Missing email parameter in your request."
            return {'success': False, 'message': msg}
        user_role = args.get('user_role', None)
        if not user_role:
            msg = "Missing user role: `admin`, `analyst`"
            return {'success': False, 'message': msg}
        user_name = args.get('user_name', '')
        seed = random.randint(100000000, 999999999)
        hash_key = "{}{}".format(user_email, seed)
        api_key = hashlib.sha256(hash_key).hexdigest()
        obj = {'email': user_email, 'name': user_name, 'api_key': api_key,
               'role': 'analyst'}
        mongo.db.users.insert(obj)
        obj.pop('_id', None)
        return obj


api.add_resource(ExtensionActions, '/<string:sub_id>/get-indicators',
                                   '/<string:sub_id>/send-events',
                                   '/get-indicators', '/send-events')
api.add_resource(IndicatorIngest, '/admin/add-indicators')
api.add_resource(EventsManagement, '/admin/get-events')
api.add_resource(UserManagement, '/admin/add-user')

if __name__ == '__main__':
    app.run(debug=True)
