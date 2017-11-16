#! /usr/bin/env python

"""Basic REST API interface for Blockade."""
import datetime
import hashlib
import os
import re
import random
from flask import Flask
from flask import render_template
from flask import request
from flask_misaka import Misaka
from flask_pymongo import PyMongo
from flask_restful import Resource, Api, reqparse

CONST_CORE_DB = 'blockade'
CONST_EXT_KEY = 'EXTMONGO'
CONST_PYMONGO = 'pymongo'
if os.environ.get('MONGO_HOST', None):
    CONST_MONGO_HOST = os.environ['MONGO_HOST']
else:
    CONST_MONGO_HOST = '127.0.0.1'

app = Flask(__name__)
app.config['MONGO_DBNAME'] = CONST_CORE_DB
app.config['MONGO_HOST'] = CONST_MONGO_HOST

api = Api(app)
mongo = PyMongo(app)
markdown = Misaka(app, wrap=True, fenced_code=True)

parser = reqparse.RequestParser()
parser.add_argument('api_key')
parser.add_argument('email')
parser.add_argument('events')
parser.add_argument('indicators')
parser.add_argument('user_email')
parser.add_argument('user_name')
parser.add_argument('user_role')


@app.route('/')
def docs():
    """Render the documentation."""
    return render_template('docs.html')

# TODO: this should be replaced with urlparse.
def extract_fqdn(url):
    """Extract the FQDN from a URL."""
    replace = ['http://', 'https://']
    for r in replace:
        url = url.replace(r, '')
    url = url.split('/')[0]
    return url


def check_auth(args, role=None):
    """Check the user authentication."""
    if mongo.db.users.count() == 0:
        return {'success': True, 'message': None, 'init': True}
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
        app.config[CONST_EXT_KEY + '_HOST'] = CONST_MONGO_HOST
        ext_mongo = PyMongo(app, config_prefix=CONST_EXT_KEY)
        results = f(self, ext_mongo)
        for key in app.config.keys():
            if not key.startswith(CONST_EXT_KEY):
                continue
            app.config.pop(key, None)
        app.extensions[CONST_PYMONGO].pop(CONST_EXT_KEY, None)
        return results
    return wrapper


def find_ip():
    """Run through the request to identify the client IP address."""
    ip = request.environ.get('HTTP_X_REAL_IP', None)
    if ip:
        return ip
    ip = request.access_route
    if len(ip) > 0:
        return ip[0]
    return request.remote_addr


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
        client_ip = find_ip()
        for idx, event in enumerate(events):
            event['sourceIp'] = client_ip
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
                'ip': client_ip,
                'contact': event['contact']
            }
            ext_mongo.db.events.insert_one(obj)
        mesg = "Wrote {} events to the cloud".format(len(events))
        return {'success': True, 'message': mesg}


class IndicatorManagement(Resource):

    """Perform actions related to indicators."""

    @db_setup
    def post(self, ext_mongo):
        """Save indicators into the local database."""
        args = request.get_json(force=True)
        auth = check_auth(args, role=["analyst", "admin"])
        if not auth['success']:
            return auth
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        indicators = args.get('indicators', list())
        indicators = list(set(indicators))
        tags = args.get('tags', list())
        for item in indicators:
            # Check if the indicator is already hashed.
            if re.search(r"^([a-fA-F\d]{32})$", item):
                orig = ""
                hashed = item
            # Otherwise it's an IOC in clear, we hash it and store the original.
            else:
                orig = extract_fqdn(item)
                # We hash it.
                hashed = hashlib.md5(orig).hexdigest()

            # Look-up hashed IOC.
            record = ext_mongo.db.indicators.find_one({'indicator': hashed})
            # Only insert if there wasn't a previous record of the same IOC.
            if not record:
                obj = {'indicator': hashed, 'orig': orig, 'tags': tags,
                       'creator': auth['user']['email'], 'datetime': current_time}
                ext_mongo.db.indicators.insert_one(obj)

        msg = "Wrote {} indicators".format(len(indicators))
        return {'success': True, 'message': msg, 'writeCount': len(indicators)}

    @db_setup
    def delete(self, ext_mongo):
        """Delete indicators from the local database."""
        args = request.get_json(force=True)
        auth = check_auth(args, role=['admin'])
        if not auth['success']:
            return auth
        deleted = 0
        indicators = args.get('indicators', list())
        indicators = list(set(indicators))
        for item in indicators:
            #  Expecting MD5 indicators, so hash everything else.
            if len(item) != 32:
                item = extract_fqdn(item)  # Just in case
                item = hashlib.md5(item).hexdigest()
            d = ext_mongo.db.events.delete_one({'indicator': item})
            deleted += d.deleted_count
        msg = "Deleted {} indicators".format(deleted)
        output = {'success': True, 'message': msg,
                  'deleteCount': deleted}
        return output


class EventsManagement(Resource):

    """Perform actions related to events."""

    @db_setup
    def get(self, ext_mongo):
        """Get recorded events."""
        args = parser.parse_args()
        auth = check_auth(args, role=['analyst', 'admin'])
        if not auth['success']:
            return auth
        output = {'success': True, 'events': list(), 'eventsCount': 0}
        output['events'] = [x for x in ext_mongo.db.events.find({}, {'_id': 0})]
        output['eventsCount'] = len(output['events'])
        return output

    @db_setup
    def delete(self, ext_mongo):
        """Delete recorded events."""
        args = parser.parse_args()
        auth = check_auth(args, role=['admin'])
        if not auth['success']:
            return auth
        ext_mongo.db.events.delete_many(dict())
        output = {'success': True}
        return output


class UserManagement(Resource):

    """Perform actions related to users."""

    def get(self):
        """Validate users to confirm their account."""
        args = parser.parse_args()
        auth = check_auth(args, role=["admin"])
        if not auth['success']:
            return auth
        return {'success': True, 'message': 'User is valid.'}

    def post(self):
        """Added new users to the system."""
        args = parser.parse_args()
        auth = check_auth(args, role=["admin"])
        if not auth['success']:
            return auth
        user_email = args.get('user_email', None)
        if not user_email:
            msg = "Missing user_email parameter in your request."
            return {'success': False, 'message': msg}
        user_role = args.get('user_role', None)
        if not user_role:
            msg = "Missing user role: `admin`, `analyst`"
            return {'success': False, 'message': msg}
        user_name = args.get('user_name', '')
        seed = random.randint(100000000, 999999999)
        hash_key = "{}{}".format(user_email, seed)
        api_key = hashlib.sha256(hash_key).hexdigest()
        if auth.get('init', False):
            user_role = 'admin'
        else:
            user_role = user_role
        obj = {'email': user_email, 'name': user_name, 'api_key': api_key,
               'role': user_role}
        mongo.db.users.insert_one(obj)
        obj.pop('_id', None)
        return obj


api.add_resource(ExtensionActions, '/<string:sub_id>/get-indicators',
                                   '/<string:sub_id>/send-events',
                                   '/get-indicators', '/send-events')
api.add_resource(IndicatorManagement, '/<string:sub_id>/admin/add-indicators',
                                      '/<string:sub_id>/admin/remove-indicators',
                                      '/admin/add-indicators',
                                      '/admin/remove-indicators')
api.add_resource(EventsManagement, '/<string:sub_id>/admin/get-events',
                                   '/<string:sub_id>/admin/flush-events',
                                   '/admin/get-events', '/admin/flush-events')
api.add_resource(UserManagement, '/admin/add-user', '/admin/validate-user')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
