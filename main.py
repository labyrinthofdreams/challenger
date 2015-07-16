import ConfigParser
import datetime
import json
import re
import bs4
import jinja2
import requests

session = requests.Session()

jinja = jinja2.Environment(loader=jinja2.FileSystemLoader(u'template'))

config = ConfigParser.RawConfigParser()
config.read('config.ini')

USERNAME = config.get('forum', 'username')
PASSWORD = config.get('forum', 'password')
FORUMID = config.getint('forum', 'forumid')
THREADID = config.getint('forum', 'threadid')
LASTPAGE = config.getint('script', 'lastpage')
LASTPOST = config.get('script', 'lastpost')

def find_posts(html):
    table = html.find('table', {'id':'topic_viewer'})
    posts = []
    if not table:
        return posts
    rows = table.find_all('tr', id=re.compile('post-[0-9]{7}'))
    for row in rows:
        post = {}
        post['id'] = row.get('id')
        post['text'] = table.find('tr', id=row.get('id')).find_next_sibling().find('td', class_='c_post')
        post['username'] = row.find('a', class_='member').string
        posts.append(post)
    return posts

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
    return find_posts(html)

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
    
def submit_post(text, forum_id, thread_id, post_id):
    url = 'http://s15.zetaboards.com/iCheckMovies/post/?mode=3&type=1&f={0}&t={1}&p={2}&pg=1&x=25'.format(forum_id, thread_id, post_id)
    response = session.get(url)
    html = bs4.BeautifulSoup(response.text, 'html.parser')
    params = {'mode': html.find('input', attrs={'name':'mode'})['value'],
              'type': html.find('input', attrs={'name':'type'})['value'],
              'ast': html.find('input', attrs={'name':'ast'})['value'],
              'f': html.find('input', attrs={'name':'f'})['value'],
              'xc': html.find('input', attrs={'name':'xc'})['value'],
              't': html.find('input', attrs={'name':'t'})['value'],
              'qhash': html.find('input', attrs={'name':'qhash'})['value'],
              'p': html.find('input', attrs={'name':'p'})['value'],
              'pg': html.find('input', attrs={'name':'pg'})['value'],
              'x': html.find('input', attrs={'name':'x'})['value'],
              'sd': html.find('input', attrs={'name':'sd'})['value'],
              'title': html.find('input', attrs={'name':'title'})['value'],
              'description': html.find('input', attrs={'name':'description'})['value'],
              'tags': html.find('input', attrs={'name':'tags'})['value'],
              'meta_time': html.find('input', attrs={'name':'meta_time'})['value'],
              'meta_diff': html.find('input', attrs={'name':'meta_diff'})['value'],
              'meta_tz': html.find('input', attrs={'name':'meta_tz'})['value'],
              'meta_plug': html.find('input', attrs={'name':'meta_plug'})['value'],
              'meta_mime': html.find('input', attrs={'name':'meta_mime'})['value'],
              'meta_x': html.find('input', attrs={'name':'meta_x'})['value'],
              'meta_y': html.find('input', attrs={'name':'meta_y'})['value'], 
              'sig': html.find('input', attrs={'name':'sig'})['value'],
              'emo': html.find('input', attrs={'name':'emo'})['value'],
              'post': text              
              }
    headers = {u'content-type': u'application/x-www-form-urlencoded'}  
    try:
        posturl = 'http://s15.zetaboards.com/iCheckMovies/post/'
        response = session.post(posturl, data=params, headers=headers, cookies=session.cookies)
        if response.status_code != requests.codes.ok:
            raise response.raise_for_status()
        elif len(response.cookies) == 0:
            pass
            #raise Exception(u'Post failed. Not logged in!')
    except:
        raise
        
def get_highest_number(text):
    """Given a bs4 object will get the largest number followed by a period
        inside the last [spoiler][/spoiler] tag"""
    if not text:
        raise Exception('text parameter must not be None')    
    # Check for a line starting with a number inside a spoiler tag
    # Find spoiler tags
    tags = text.find_all('div', class_='spoiler_toggle')    
    if not tags:
        return 0
    # Select the LAST spoiler tag, because sometimes people might put reviews
    # in spoiler tags
    tag = tags[-1]
    spoiler_text_tag = tag.find_next_sibling()
    spoiler_text = unicode(spoiler_text_tag).replace('<br/>', '\n')
    rx2 = re.compile('^([0-9]+)\\.', re.IGNORECASE)
    highest = 0
    lines = spoiler_text.split('\n')
    for line in lines:
        result = rx2.match(line)
        if result:
            match = int(result.group(1))
            if match > highest:
                highest = match
    return highest
    
def rescan_post(thread_id, post_id):
    """Fetches the post with post_id in thread_id
        
    Returns None on failure and a bs4 object on success"""
    url = 'http://s15.zetaboards.com/iCheckMovies/single/?p={0}&t={1}'.format(post_id, thread_id)
    response = session.get(url)
    html = bs4.BeautifulSoup(response.text, 'html.parser')
    posts = find_posts(html) 
    if not posts:
        return None
    return posts[0] 
        
if __name__ == '__main__':
    try:
        login(USERNAME, PASSWORD)
        num_pages = get_page_count(THREADID)
        all_posts = []
        # Iterate all new pages since last visit and get all new posts
        for page in range(LASTPAGE, num_pages + 1):
            print 'Querying page', page
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
        if len(all_posts) == 0:
            raise Exception('No new posts')
        # Now that we have all the new posts, we can find the updates
        # Get previous users and their seen film numbers
        stats = []
        with open('data.json', 'w+') as json_file:
            try:
                stats = json.loads(json_file.readline())
            except Exception, e:
                print 'Error loading JSON:', str(e)
        rescans = []
        rescan_rx = re.compile('!rescan ([0-9]{7})')
        for post in all_posts:
            seen_films = get_highest_number(post['text']) 
            if seen_films == 0:
                # If there's no spoiler tag in this post with seen films
                # then check if it's a rescan command
                match = rescan_rx.search(unicode(post['text']))
                if match:
                    rescans.append(match.group(1))
                continue           
            # Get seen films for the user. Since this will go through
            # all new posts, the latest update by the user will be 
            # assigned without a problem
            # If user has posted before, update existing data
            # Otherwise add the new user and seen films
            idx = get_index(stats, lambda x: x['username'] == post['username'])
            if idx > -1:
                stats[idx]['seen'] = seen_films
            else:
                user = {}
                user['username'] = post['username']
                user['seen'] = seen_films
                stats.append(user)
        # Do the scheduled rescans
        for post_id in rescans:
            post = rescan_post(THREADID, post_id)
            if not post:
                continue
            highest = get_highest_number(post['text'])
            if highest == 0:
                continue
            idx = get_index(stats, lambda x: x['username'] == post['username'])
            if idx > -1:
                stats[idx]['seen'] = highest
        # Save the last post and page we processed
        config.set('script', 'lastpost', all_posts[-1]['id'])
        config.set('script', 'lastpage', num_pages)
        with open('config.ini', 'wb') as out:
            config.write(out)
        # Save the user data
        with open('data.json', 'wb') as out:
            try:
                out.write(json.dumps(stats))
            except Exception, e:
                print 'Error saving:', str(e)
        # Next we will render the template
        tpl = jinja.get_template(u'template.html')
        render = tpl.render(entries=stats)
        #submit_post(render, THREADID, )
        print render
    except Exception, e:
        import traceback
        traceback.format_exc()
        print str(e)