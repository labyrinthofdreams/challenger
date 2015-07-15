import ConfigParser
import datetime
import re
import bs4
import jinja2
import requests

session = requests.Session()

config = ConfigParser.RawConfigParser()
config.read('config.ini')

USERNAME = config.get('forum', 'username')
PASSWORD = config.get('forum', 'password')
THREADID = config.getint('forum', 'threadid')
LASTPAGE = config.getint('script', 'lastpage')
LASTPOST = config.getint('script', 'lastpost')

def get_page_count(thread_id):
    """Returns the number of pages in a thread as an integer"""
    url = 'http://s15.zetaboards.com/iCheckMovies/topic/{0}/1?x=25'.format(thread_id)
    response = session.get(url)
    html = bs4.BeautifulSoup(response.text, 'html.parser')
    pages = html.find('ul', class_='cat-pages')
    if not pages:
        return 1
    # Get last <li> element
    li = pages.find_all('li')[-1]
    return int(li.string)
    
def get_posts(thread_id, page):
    """Returns all the posts in a given thread_id on a given page"""
    url = 'http://s15.zetaboards.com/iCheckMovies/topic/{0}/{1}?x=25'.format(thread_id, page)
    response = session.get(url)
    html = bs4.BeautifulSoup(response.text, 'html.parser')
    table = html.find('table', {'id':'topic_viewer'})
    if not table:
        raise Exception('Could not find table')
    posts = []
    rows = table.find_all('tr', id=re.compile('post-[0-9]{7}'))
    for row in rows:
        post = {}
        post['id'] = row.get('id')
        post['text'] = table.find('tr', id=post['id']).next_sibling.string
        posts.append(post)
    return posts

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
        num_pages = get_page_count(THREADID)
        # Iterate all new pages since last visit
        for page in range(LASTPAGE, num_pages + 1):
            # Get all posts from the page  
            posts = get_posts(THREADID, page)          
    except Exception, e:
        import traceback
        traceback.format_exc()
        print str(e)