import json

class OAuthToken(object):

    def __init__(self, resource_owner_key=None, resource_owner_secret=None):
        self.resource_owner_key = resource_owner_key
        self.resource_owner_secret = resource_owner_secret

    def to_dict(self):
        d = {}

        if self.resource_owner_key != None:
            d["resource_owner_key"] = self.resource_owner_key
 
        if self.resource_owner_secret != None:
            d["resource_owner_secret"] = self.resource_owner_secret
        return d

    @staticmethod
    def load(path):
        with open(path, 'r') as f:
            tokens = json.load(f)
            return OAuthToken(resource_owner_key=tokens.get('resource_owner_key'),
                              resource_owner_secret=tokens.get('resource_owner_secret'))

    def save(self, path):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)