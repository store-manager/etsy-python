import os
import re
import tempfile
import time
from ._etsy_env import EtsyEnvSandbox, EtsyEnvProduction
import json
import requests
from requests_oauthlib import OAuth1
import logging

LOGFILE = 'etsy_log.txt'
LOGFORMAT = '[%(asctime)s %(levelname)s %(name)s %(message)s]'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.INFO)
formatter = logging.Formatter(LOGFORMAT)
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
fileHandler = logging.FileHandler(LOGFILE)
fileHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter(LOGFORMAT)
fileHandler.setFormatter(formatter)
logger.addHandler(fileHandler)

class TypeChecker(object):
    def __init__(self):
        self.checkers = {
            'int': self.check_int,
            'float': self.check_float,
            'string': self.check_string,
            }

    def __call__(self, method, **kwargs):
        params = method['params']
        for k, v in kwargs.items():
            if k == 'includes': continue

            if k not in params:
                raise ValueError('Unexpected argument: %s=%s' % (k, v))
            
            t = params[k]
            checker = self.checkers.get(t, None) or self.compile(t)
            ok, converted = checker(v)
            if not ok:
                raise ValueError(
                    "Bad value for parameter %s of type '%s' - %s" % (k, t, v))
            kwargs[k] = converted

    def compile(self, t):
        if t.startswith('enum'):
            f = self.compile_enum(t)
        else:
            f = self.always_ok
        self.checkers[t] = f
        return f

    def compile_enum(self, t):
        terms = [x.strip() for x in t[5:-1].split(',')]
        def check_enum(value):
            return (value in terms), value
        return check_enum

    def always_ok(self, value):
        return True, value

    def check_int(self, value):
        return isinstance(value, int), value

    def check_float(self, value):
        if isinstance(value, int):
            return True, value
        return isinstance(value, float), value

    def check_string(self, value):
        return isinstance(value, str), value

class APIMethod(object):
    def __init__(self, api, spec):
        """
        Parameters:
            api          - API object that this method is associated with.
            spec         - dict with the method specification; e.g.:

              {'name': 'createListing', 'uri': '/listings', 'visibility':
              'private', 'http_method': 'POST', 'params': {'description':
              'text', 'tags': 'array(string)', 'price': 'float', 'title':
              'string', 'materials': 'array(string)', 'shipping_template_id':
              'int', 'quantity': 'int', 'shop_section_id': 'int'}, 'defaults':
              {'materials': None, 'shop_section_id': None}, 'type': 'Listing',
              'description': 'Creates a new Listing'} 
        """

        self.api = api
        self.spec = spec
        self.type_checker = self.api.type_checker
        self.__doc__ = self.spec['description']
        self.compiled = False
    
    def __call__(self, *args, **kwargs):
        if not self.compiled:
            self.compile()
        return self.invoke(*args, **kwargs)

    def compile(self):
        uri = self.spec['uri']
        self.positionals = re.findall('{(.*)}', uri)

        for p in self.positionals:
            uri = uri.replace('{%s}' % p, '%%(%s)s' % p)
        self.uri_format = uri

        self.compiled = True

    def invoke(self, *args, **kwargs):
        if args and not self.positionals:
            raise ValueError(
                'Positional argument(s): %s provided, but this method does '
                'not support them.' % (args,))

        if len(args) > len(self.positionals):
            raise ValueError('Too many positional arguments.')

        for k, v in zip(self.positionals, args):
            if k in kwargs:
                raise ValueError(
                    'Positional argument duplicated in kwargs: %s' % k)
            kwargs[k] = v

        ps = {}
        for p in self.positionals:
            if p not in kwargs:
                raise ValueError("Required argument '%s' not provided." % p)
            ps[p] = kwargs[p]
            del kwargs[p]

        self.type_checker(self.spec, **kwargs)
        return self.api._execute(self.spec['http_method'], self.uri_format % ps, **kwargs)

class MethodTableCache(object):
    max_age = 60*60*24

    def __init__(self, api, method_cache):
        self.api = api
        self.filename = self.resolve_file(method_cache)
        self.used_cache = False
        self.wrote_cache = False

    def resolve_file(self, method_cache):
        if method_cache is None:
            return self.default_file()
        return method_cache

    @property
    def etsy_home(self):
        return self.api.etsy_home

    def default_file(self):
        etsy_home = self.etsy_home
        d = etsy_home if os.path.isdir(etsy_home) else tempfile.gettempdir()
        return os.path.join(d, 'methods.%s.json' % self.api.api_version)

    def get(self):
        ms = self.get_cached()
        if not ms:
            ms = self.api.get_method_table()
            self.cache(ms)
        return ms
        
    def get_cached(self):
        if self.filename is None or not os.path.isfile(self.filename):
            logger.debug('Not using cached method table.')
            return None
        if time.time() - os.stat(self.filename).st_mtime > self.max_age:
            logger.debug('Method table too old.')
            return None
        with open(self.filename, 'r') as f:
            self.used_cache = True
            logger.debug('Reading method table cache: %s' % self.filename)
            return json.loads(f.read())

    def cache(self, methods):
        if self.filename is None:
            logger.debug('Method table caching disabled, not writing new cache.')
            return
        with open(self.filename, 'w') as f:
            json.dump(methods, f)
            self.wrote_cache = True
            logger.debug('Wrote method table cache: %s' % self.filename)

class EtsyAPI(object):
    api_version = 'v2'
    def __init__(self, oauth_client, method_cache=None, etsy_env=EtsyEnvSandbox()):
        """
        Creates a new API instance. When called with no arguments, 
        reads the appropriate API key from the default ($HOME/.etsy/keys) 
        file. 

        Parameters:
            api_key      - An explicit API key to use.
            key_file     - A file to read the API keys from. 
            method_cache - A file to save the API method table in for 
                           24 hours. This speeds up the creation of API
                           objects. 

        Only one of api_key and key_file may be passed.

        If method_cache is explicitly set to None, no method table
        caching is performed. If the parameter is not passed, a file in 
        $HOME/.etsy is used if that directory exists. Otherwise, a 
        temp file is used. 
        """
        self.api_url = etsy_env.api_url

        if self.api_url.endswith('/'):
            raise AssertionError('api_url should not end with a slash.')

        self.oauth_client = oauth_client
        self.type_checker = TypeChecker()

        logger.debug('Creating %s Etsy API, base url=%s.' % (self.api_version, self.api_url))
        self._get_methods(method_cache)

    def _get_methods(self, method_cache):
        self.method_cache = MethodTableCache(self, method_cache)
        ms = self.method_cache.get()
        self._methods = dict([(m['name'], m) for m in ms])

        for method in ms:
            setattr(self, method['name'], APIMethod(self, method))

        logger.debug('self._methods = %r' % self._methods)

    @property
    def etsy_home(self):
        return os.path.expanduser('~/.etsy')

    def get_method_table(self):
        return self._execute('GET', '/')

    def _execute(self, http_method, url, **kwargs):
        for item in url.split('/'):
            if item.startswith(':'):
                key = item.lstrip(':')
                if key in kwargs:
                    url = url.replace(item, str(kwargs[key]))
                    del kwargs[key]

        url = f'{self.api_url}{url}'
        logger.debug('http_method = %r, url = %r, data = %r' % (http_method, url, kwargs))
        r = None
        token = self.oauth_client.access_token
        if http_method == 'GET':
            r = requests.get(url, params=kwargs, auth=token)
        elif http_method == 'DELETE':
            r = requests.delete(url, params=kwargs, auth=token)
        elif http_method == 'POST':
            r = requests.post(url, data=kwargs, auth=token)
        elif http_method == 'PUT':
            r = requests.put(url, data=kwargs, auth=token)
        else:
            raise Exception("Unsupport http method %s" % http_method)

        if r:
            try:
                data = r.json()
            except json.JSONDecodeError:
                raise ValueError('Could not decode response from Etsy as JSON: %r' % data)

            data['count']
            return data['results']
        return None

