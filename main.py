"""
Copyright (c) 2015 https://github.com/labyrinthofdreams
For license information see LICENSE.txt

Automatic updater for film challenges
"""
import ConfigParser
import datetime
import json
import os.path
import re
import sched
import time
import bs4
import jinja2
import requests

class ChallengerException(Exception):
    """Custom exception class for generic exceptions"""
    pass

session = requests.Session()

scheduler = sched.scheduler(time.time, time.sleep)

jinja = jinja2.Environment(loader=jinja2.FileSystemLoader(u'template'))

config = ConfigParser.RawConfigParser()
config.read('config.ini')

FORUMURL = config.get('forum', 'url')
USERNAME = config.get('forum', 'username')
PASSWORD = config.get('forum', 'password')
LONGDELAY = config.getint('script', 'longdelay')
SHORTDELAY = config.getint('script', 'shortdelay')
DEBUG = config.get('script', 'debug')

def find_posts(html):
    """Finds all posts in the given bs4 html object
    
    Returns empty list if finds none, otherwise a list of all found posts"""
    table = html.find('table', {'id': 'topic_viewer'})
    posts = []
    if not table:
        return posts
    rows = table.find_all('tr', id=re.compile('post-[0-9]{7}'))
    for row in rows:
        post = {}
        post['id'] = row.get('id')
        post['text'] = table.find('tr', id=row.get('id')).find_next_sibling().\
                                                find('td', class_='c_post')
        post['username'] = row.find('a', class_='member').string
        posts.append(post)
    return posts

def get_page_count(thread_id):
    """Returns the number of pages in a thread as an integer"""
    url = os.path.join(FORUMURL, 'topic/{0}/1?x=25'.format(thread_id))
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
    url = os.path.join(FORUMURL, 'topic/{0}/{1}?x=25'.format(thread_id, page))
    response = session.get(url)
    html = bs4.BeautifulSoup(response.text, 'html.parser')
    return find_posts(html)

def login(username, password):
    """Log in using username and password"""
    if username is None or password is None:
        raise Exception(u'Username and password must be set')
    args = {u'uname': username,
            u'pw': password,
            u'cookie_on': u'1',
            u'tm': datetime.datetime.today().strftime(u'4/4/2014 3:%M:%S PM')}
    headers = {u'content-type': u'application/x-www-form-urlencoded'}
    url = os.path.join(FORUMURL, u'login/log_in/')
    resp = session.post(url, data=args, headers=headers, allow_redirects=False)
    if resp.status_code != requests.codes.ok:
        pass
        # raise resp.raise_for_status()
    elif len(resp.cookies) == 0:
        if resp.text.find('You are logged in already') > -1:
            print 'You\'re already logged in!'
        else:
            raise Exception(u'Login failed. Invalid username and/or password')
        
def get_index(iterable, fun):
    """Return index as an integer when the function fun returns True
    
    Returns -1 if fun is never True, otherwise the index"""
    for i in range(0, len(iterable)):
        if fun(iterable[i]):
            return i
    return -1      
    
def submit_post(text, forum_id, thread_id, post_id):
    """Edit forum post"""
    url = os.path.join(FORUMURL, 'post/?mode=3&type=1&f={0}&t={1}&p={2}&pg=1'.\
                                    format(forum_id, thread_id, post_id))
    response = session.get(url)
    if response.text.find('<td>You do not have permission to edit this post.<br />') > -1:
        raise Exception('You do not have permission to edit this post')
    html = bs4.BeautifulSoup(response.text, 'html.parser')
    params = {'mode': html.find('input', attrs={'name': 'mode'})['value'],
              'type': html.find('input', attrs={'name': 'type'})['value'],
              'ast': html.find('input', attrs={'name': 'ast'})['value'],
              'f': html.find('input', attrs={'name': 'f'})['value'],
              'xc': html.find('input', attrs={'name': 'xc'})['value'],
              't': html.find('input', attrs={'name': 't'})['value'],
              'qhash': html.find('input', attrs={'name': 'qhash'})['value'],
              'p': html.find('input', attrs={'name': 'p'})['value'],
              'pg': html.find('input', attrs={'name': 'pg'})['value'],
              'x': html.find('input', attrs={'name': 'x'})['value'],
              'sd': html.find('input', attrs={'name': 'sd'})['value'],
              'title': html.find('input', attrs={'name': 'title'})['value'],
              'description': html.find('input', attrs={'name': 'description'})['value'],
              'tags': html.find('input', attrs={'name': 'tags'})['value'],
              'sig': html.find('input', attrs={'name': 'sig'})['value'],
              'emo': html.find('input', attrs={'name': 'emo'})['value'],
              'post': text}
    headers = {u'content-type': u'application/x-www-form-urlencoded'}  
    try:
        posturl = os.path.join(FORUMURL, 'post/')
        response = session.post(posturl, data=params, headers=headers, 
                                cookies=session.cookies)
        if response.status_code != requests.codes.ok:
            raise response.raise_for_status()
        elif len(response.cookies) == 0:
            pass
            # raise Exception(u'Post failed. Not logged in!')
    except:
        raise
        
def get_highest_number(html):
    """Given a bs4 object will get the largest number followed by a period"""
    if not html:
        raise Exception('text parameter must not be None')    
    # Find lines starting with a number and pick the largest number
    text = unicode(html).strip().replace('<br/>', '\n')
    # Matches: 123. film title
    single_rx = re.compile('^([0-9]+)\\.\\s+')
    # Matches: 12-13. film title & 12.-13. film title
    multi_rx = re.compile('^[0-9]+\\.?\\-([0-9]+)\\.\\s+')
    highest = 0
    lines = [line.strip() for line in text.split('\n')]
    for line in lines:        
        result = single_rx.match(line)
        if not result:
            result = multi_rx.match(line)
        if result:
            match = int(result.group(1))
            if match > highest:
                highest = match
    return highest          
    
def parse_overwrite(html):
    """Parses the value following the !overwrite command.
        
    The command must be at the start of a line.    
    
    Returns the value as an integer or None if it can't find it.
    """
    text = unicode(html).replace('<br/>', '\n')
    lines = text.split('\n')
    rex = re.compile('!overwrite ([0-9]+)')
    for line in lines:    
        result = rex.search(line)
        if result:
            return int(result.group(1))
    return None
    
def fetch_new_posts(thread_id, first_page, last_page, start_from):
    """Fetches all new posts between first_page and last_page
    
    Returns a list of all posts, or an empty list if there's no posts"""
    all_posts = []
    # Iterate all new pages since last visit and get all new posts
    for page in range(first_page, last_page):
        print 'Querying page {0} of {1}'.format(page, last_page - 1)
        # Get all posts from the page  
        posts = get_posts(thread_id, page)
        if not posts:
            # This may occur for instance if an admin has removed posts
            # So we print the error, break from the loop (since there's
            # no sense checking the later pages), and then process the
            # posts we already found
            print 'Could not find any posts'
            break 
        # Does this page have the last processed post?
        idx = get_index(posts, lambda x: x['id'] == start_from)
        if idx == -1:
            # If not, extend all posts
            all_posts.extend(posts)   
        else:
            # Otherwise, skip processed posts
            all_posts.extend(posts[idx + 1:])
    return all_posts
    
def load_stats(filename):
    """Loads previous data about users and seen films from filename
    
    Returns a list of all user data or an empty list if there's no data"""
    stats = {}
    if not os.path.exists(filename):
        return stats
    with open(filename, 'rb') as json_file:
        try:
            stats = json.loads(json_file.readline())
        except Exception, err:
            print 'Error loading JSON:', str(err)
    return stats
    
def save_stats(filename, data):
    """Saves data about users and seen films in filename"""
    with open(filename, 'wb') as out:
        try:
            out.write(json.dumps(data))
        except Exception, err:
            print 'Error saving:', str(err)
    
def get_seen_films(html):
    """Gets a seen films number from a post
    
    Returns the seen films number as an integer or 0 if there's no films"""
    seen_films = parse_overwrite(html)
    if not seen_films:
        seen_films = get_highest_number(html)
    return seen_films
    
def check_posts(sch, delay, threads, index):
    """Check for new posts in threads"""
    try:
        # We must wait SHORTDELAY seconds between each request when processing a queue
        # But we'll wait LONGDELAY between when a queue has finished
        # and before it starts again
        if len(threads) == index + 1:
            delay = LONGDELAY
        else:
            delay = SHORTDELAY
        # Get all thread data including users and their seen films
        threads = load_stats('data.json')
        # Get new threads to monitor
        for section in config.sections():
            # We need to remove all sections because when we read() the config.ini file again
            # the old sections will remain, that is, the read() only adds new sections
            # so IF we remove a section it wouldn't be removed until the program is restarted
            config.remove_section(section)
        config.read('config.ini')
        sections = config.sections()
        for section in sections:
            if section.startswith('thread'):
                thread_id = config.get(section, 'threadid')
                forum_id = config.get(section, 'forumid')
                if DEBUG == 'on' or thread_id not in threads:
                    thread = {}
                    thread['forum_id'] = forum_id
                    thread['section'] = section
                    threads[thread_id] = thread
        # Delete thread if it's removed from config file
        for key, value in threads.items():
            if value['section'] not in sections:
                del threads[key]
        print threads.keys()
        if index >= len(threads):
            index = 0
        if len(threads) == 0:
            if DEBUG == 'off':
                # Only save data when not in debug mode
                save_stats('data.json', threads)
            raise ChallengerException('Could not find any threads')
        # Process current thread
        thread_id, thread = threads.items()[index]
        index = index + 1
        if 'last_page' not in thread:
            thread['last_page'] = 1
        if 'last_post_id' not in thread:
            thread['last_post_id'] = ''
        response = session.get(os.path.join(FORUMURL, \
                                        'topic/{0}/1/?x=25'.format(thread_id)))
        html = bs4.BeautifulSoup(response.text, 'html.parser')
        if 'title' not in thread:
            thread['title'] = html.title.string
        if 'first_post_id' not in thread:
            thread['first_post_id'] = find_posts(html)[0]['id']
            thread['first_post'] = thread['first_post_id'][5:] 
        title = '{0} - {1} of {2} - {3}'.\
            format(datetime.datetime.today().strftime(u'%H:%M:%S'),
                   index, len(threads), thread['title']) 
        print '=' * len(title) 
        print title
        print '=' * len(title)
        num_pages = get_page_count(thread_id)
        all_posts = fetch_new_posts(thread_id, thread['last_page'], 
                                    num_pages + 1, thread['last_post_id'])
        if len(all_posts) == 0:
            if DEBUG == 'off':
                # Only save data when not in debug mode
                save_stats('data.json', threads)
            raise ChallengerException('No new posts\n')
        # Now that we have all the new posts, we can find the updates
        has_new_updates = False
        for post in all_posts:
            # Check for the overwrite command
            # It overwrites all other values in the post
            seen_films = get_seen_films(post['text'])
            if seen_films == 0:
                # Could not find a seen films number so go to next post
                continue       
            has_new_updates = True    
            # Get seen films for the user. Since this will go through
            # all new posts, the latest update by the user will be 
            # assigned without a problem
            # If user has posted before, update existing data
            # Otherwise add the new user and seen films
            if 'users' not in thread:
                thread['users'] = []
            idx = get_index(thread['users'], 
                            lambda x: x['username'] == post['username'])
            if idx > -1:
                thread['users'][idx]['seen'] = seen_films
            else:
                user = {}
                user['username'] = post['username']
                user['seen'] = seen_films
                thread['users'].append(user)
        if not has_new_updates:
            print 'No new updates\n'
        # Save the last post and page we processed
        thread['last_page'] = num_pages
        thread['last_post_id'] = all_posts[-1]['id']
        # Next we will render the template
        if has_new_updates:
            # Only update first post if there's new updates
            tpl = jinja.get_template(u'{0}.html'.format(thread['section']))
            render = tpl.render(entries=thread['users'])
            if DEBUG == 'off':
                submit_post(render, thread['forum_id'], 
                            thread_id, thread['first_post'])
                print 'Updated first post\n'
            else:
                print render
        if DEBUG == 'off':
            # Only save data when not in debug mode
            save_stats('data.json', threads)
    except ChallengerException, err:
        print str(err)
    except jinja2.TemplateNotFound, err:
        print 'jinja2 template not found:', str(err)
    except Exception, err:
        import traceback
        print traceback.format_exc()
        print 'Error:', str(err)         
    sch.enter(delay, 1, check_posts, (sch, delay, threads, index))

if __name__ == '__main__':
    try:
        login(USERNAME, PASSWORD)
        scheduler.enter(0, 1, check_posts, (scheduler, LONGDELAY, {}, 0))
        scheduler.run()
    except Exception, err:
        import traceback
        traceback.format_exc()
        print str(err)
        