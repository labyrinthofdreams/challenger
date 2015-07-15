import ConfigParser
import datetime
import pickle
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
LASTPOST = config.get('script', 'lastpost')

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
        post['username'] = row.find('a', class_='member').string
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
        
def get_index(iterable, fun):
    for i in range(0, len(iterable)):
            if fun(iterable[i]):
                    return i
    return -1        
        
if __name__ == '__main__':
    try:
        login(USERNAME, PASSWORD)
        num_pages = get_page_count(THREADID)
        all_posts = []
        # Iterate all new pages since last visit and get all new posts
        for page in range(LASTPAGE, num_pages + 1):
            # Get all posts from the page  
            posts = get_posts(THREADID, page)
            if not posts:
                # This may occur for instance if an admin has removed posts
                # So we print the error, break from the loop (since there's
                # no sense checking the later pages), and then process the
                # posts we already found
                print 'Could not find any posts'
                break 
            # Does this page have the last processed post?
            idx = get_index(posts, lambda x: x['id'] == LASTPOST)
            if idx == -1:
                # If not, extend all posts
                all_posts.extend(posts)   
            else:
                # Otherwise, skip processed posts
                all_posts.extend(posts[idx + 1:])
        # Now that we have all the new posts, we can find the updates
        # Get previous users and their seen film numbers
        pickle_file = open('data.pkl', 'rb')
        stats = pickle.load(pickle_file)
        pickle_file.close()
        rx = re.compile('\\[spoiler=".*([0-9]+)"\\]', re.IGNORECASE) 
        for post in all_posts:
            result = rx.search(post['text'])
            # Don't do anything to posts without the spoiler tag
            if result:
                # Get seen films for the user. Since this will go through
                # all new posts, the latest update by the user will be 
                # assigned without a problem
                # If user has posted before, update existing data
                # Otherwise add the new user and seen films
                idx = get_index(stats, lambda x: x['username'] == post['username'])
                if idx > -1:
                    stats[idx]['seen'] = result.group(1)
                else: 
                    post['seen'] = result.group(1)
                    stats.append(post)
        # Save the last post and page we processed
        config.set('script', 'lastpost', all_posts[-1]['id'])
        config.set('script', 'lastpage', num_pages)
        # Save the user data
        out = open('data.pkl', 'wb')
        pickle.dump(stats, out)
        out.close()
    except Exception, e:
        import traceback
        traceback.format_exc()
        print str(e)