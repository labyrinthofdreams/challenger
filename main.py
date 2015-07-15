import ConfigParser
import datetime
import bs4
import jinja2
import requests

session = requests.Session()

config = ConfigParser.RawConfigParser()
config.read('config.ini')

USERNAME = config.get('forum', 'username')
PASSWORD = config.get('forum', 'password')
THREADID = config.get('forum', 'threadid')

def login(username, password):
    if username is None or password is None:
        raise Exception(u'Username and password must be set')
    args = {u'uname': username,
            u'pw': password,
            u'cookie_on': u'1',
            u'tm': datetime.datetime.today().strftime(u'4/4/2014 3:%M:%S PM')
            }
    headers = {u'content-type': u'application/x-www-form-urlencoded'}
    url = u'http://s15.zetaboards.com/iCheckMovies/login/log_in/'
    resp = session.post(url, data=args, headers=headers, allow_redirects=False)
    if resp.status_code != requests.codes.ok:
        pass
        #raise resp.raise_for_status()
    elif len(resp.cookies) == 0:
        raise Exception(u'Login failed. Invalid username and/or password')
        
if __name__ == '__main__':
    try:
        login(USERNAME, PASSWORD)
    except Exception, e:
        import traceback
        traceback.format_exc()
        print str(e)