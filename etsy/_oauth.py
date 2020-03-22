import requests
from requests_oauthlib import OAuth1
from urllib.parse import parse_qs, unquote
from ._etsy_env import EtsyEnvSandbox, EtsyEnvProduction
from ._token import OAuthToken
import os


class EtsyOAuthClient(object):
    def __init__(self, oauth_consumer_key, oauth_consumer_secret, token=None, etsy_env=EtsyEnvSandbox()):
        self.__oauth_consumer_key = oauth_consumer_key
        self.__oauth_consumer_secret = oauth_consumer_secret
        self.__oauth = OAuth1(oauth_consumer_key, client_secret=oauth_consumer_secret)
        self.__request_token_url = etsy_env.request_token_url
        self.__access_token_url = etsy_env.access_token_url
        self.__signin_url = etsy_env.signin_url
        self.__resource_owner_key = None
        self.__resource_owner_secret = None
        if token:
            self.__resource_owner_key = token.resource_owner_key
            self.__resource_owner_secret = token.resource_owner_secret
            self.__access_token = OAuth1(self.__oauth_consumer_key,
                                         client_secret=self.__oauth_consumer_secret,
                                         resource_owner_key=token.resource_owner_key,
                                         resource_owner_secret=token.resource_owner_secret,
                                         signature_method='PLAINTEXT',
                                         signature_type='auth_header')
        else:
            self.__resource_owner_key = None
            self.__resource_owner_secret = None
            self.__access_token = None

    def get_signin_url(self, scope):
        if not isinstance(scope, (list, tuple)):
            raise Exception('Scope should be a tuple or list')
        scope = ' '.join(scope)

        r = requests.post(url=self.__request_token_url, params={'scope': scope}, auth=self.__oauth)
        credentials = parse_qs(r.text)
        self.__resource_owner_key = credentials.get('oauth_token')[0]
        self.__resource_owner_secret = credentials.get('oauth_token_secret')[0]
        return unquote(r.text).lstrip('login_url=')

    def get_access_token(self, code):
        self.__oauth = OAuth1(self.__oauth_consumer_key,
                              client_secret=self.__oauth_consumer_secret,
                              resource_owner_key=self.__resource_owner_key,
                              resource_owner_secret=self.__resource_owner_secret,
                              verifier=code)
        r = requests.post(url=self.__access_token_url, auth=self.__oauth)
        credentials = parse_qs(r.text)
        self.__resource_owner_key = credentials.get('oauth_token')[0]
        self.__resource_owner_secret = credentials.get('oauth_token_secret')[0]
        self.__access_token = OAuth1(self.__oauth_consumer_key,
                                     client_secret=self.__oauth_consumer_secret,
                                     resource_owner_key=self.__resource_owner_key,
                                     resource_owner_secret=self.__resource_owner_secret,
                                     signature_method='PLAINTEXT',
                                     signature_type='auth_header')
        return self.__access_token

    @property
    def authorized(self):
        return self.access_token != None

    @property
    def access_token(self):
        return self.__access_token

    @staticmethod
    def load(path, oauth_consumer_key, oauth_consumer_secret, etsy_env=EtsyEnvSandbox()):
        token = None
        if os.path.exists(path):
            token = OAuthToken.load(path)
        return EtsyOAuthClient(oauth_consumer_key, oauth_consumer_secret, token=token, etsy_env=etsy_env)

    def save(self, path):
        if self.access_token:
            OAuthToken(self.__resource_owner_key, self.__resource_owner_secret).save(path)
            return True
        return False
