# etsy-python
Python access to the Etsy V2 API

By Dan McKinley - dan@etsy.com - [http://mcfunley.com](http://mcfunley.com)
Updated by Chris Lapa for Python 3.6+

## Installation

This version of etsy-python has not been pushed to pypi.org. Instead it can be installed from Github.
pip install git+https://github.com/store-manager/etsy-python.git@0.4.0

## Example with OAuth

Register an app [here](https://www.etsy.com/developers/register).

<pre>
from etsy import EtsyOAuthClient, EtsyAPI, EtsyEnvProduction

app_scope = ["transactions_r", "listings_r"] # Valid values can be viewed [here](https://www.etsy.com/developers/documentation/getting_started/oauth#section_permission_scopes)
user_token_path = 'access_token.json'
oauth_consumer_key = '123456789' # Keystring from your Apps API here](https://www.etsy.com/developers/your-apps)
oauth_consumer_secret = 'abcdef' # Shared secret from your Apps API [here](https://www.etsy.com/developers/your-apps)
env = EtsyEnvProduction
oauth = EtsyOAuthClient.load(user_token_path,
                             oauth_consumer_key,
                             oauth_consumer_secret,
                             etsy_env=env)

if not oauth.authorized:
    signin_url = oauth.get_signin_url(app_scope)
    print('Visit the following url in your browser, authorize the app and paste the signin code:')
    print(signin_url)
    code = input()
    oauth.get_access_token(code)
    oauth.save(user_token_path)

api = EtsyAPI(oauth_client=oauth, etsy_env=env)
print(api.inventory())
</pre>


## Method Table Caching

This module is implemented by metaprogramming against the method table published
by the Etsy API. In other words, API methods are not explicitly declared by the
code in this module. Instead, the list of allowable methods is downloaded and 
the patched into the API objects at runtime.

This has advantages and disadvantages. It allows the module to automatically 
receive new features, but on the other hand, this process is not as fast as 
explicitly declared methods. 

In order to speed things up, the method table json is cached locally by default.
If a $HOME/etsy directory exists, the cache file is created there. Otherwise, it 
is placed in the machine's temp directory. By default, this cache lasts 24 hours.

The cache file can be specified when creating an API object:

<pre>
from etsy import EtsyAPI

api = EtsyAPI(method_cache='myfile.json')
</pre>

Method table caching can also be disabled by passing None as the cache parameter:

<pre>
from etsy import Etsy

# do not cache methods
api = EtsyAPI(method_cache=None)
</pre>


## Version History


### Version 0.4.0
* Major overhaul to work with Python3.6+
* Removes deprecated oauth2 package and replaced with requests & requests-oauthlib
* Made OAuth module work
* Removed support for V1 Etsy API
* Adds support for Etsy V2 API's which uses PUT and DELETE http methods
* Improves logging implementation
* General code cleanup
* Adds support for saving/loading OAuth tokens to disk
* Adds OAuth app scope format checking


### Version 0.3.1
* Allowing Python Longs to be passed for parameters declared as "integers" by the API 
  (thanks to [Marc Abramowitz](http://marc-abramowitz.com)). 


### Version 0.3 
* Support for Etsy API v2 thanks to [Marc Abramowitz](http://marc-abramowitz.com). 
* Removed support for now-dead Etsy API v1. 


### Version 0.2.1 
* Added a cache for the method table json.
* Added a logging facility.


### Version 0.2 - 05-31-2010
* Added local configuration (~/.etsy) to eliminate cutting & pasting of api keys.
* Added client-side type checking for parameters.
* Added support for positional arguments.
* Added a test suite.
* Began differentiation between API versions.
* Added module to PyPI. 

### Version 0.1 - 05-24-2010 
Initial release