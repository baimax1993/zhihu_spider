# -*- coding:utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding( "utf-8" )
DEFAULT_AGENT = "Mozilla/5.0 (Windows NT 6.1; rv:51.0) Gecko/20100101 Firefox/51.0"
DEFAULT_DELAY = 0
DEFAULT_RETRIES = 1

import urllib
from datetime import datetime, timedelta
import time
import requests
import cookielib
import random
import urlparse

class Downloader():
    def __init__(self, user_agent=DEFAULT_AGENT, proxies=None, num_retries=DEFAULT_RETRIES, delay=DEFAULT_DELAY):
        self.user_agent = user_agent
        self.proxies = proxies
        self.num_retries = num_retries
        self.throttle = Throttle(delay)
        self.session = requests.session()
        self.session.cookies = cookielib.LWPCookieJar(filename='localcookies')
        try:
            self.session.cookies.load(ignore_discard=True)
        except:
            print("Cookie 未能加载")

    def __call__(self, url, req_type, data=None, headers=None):
        #add proxies
        self.throttle.wait(url)
        prox = random.choice(self.proxies) if self.proxies else None
        if headers:
            headers['User-Agent'] = self.user_agent
        result = self.download(url,req_type,self.num_retries,data,headers)
        return result['html']

    def download(self, url,req_type, num_retries, data=None, headers=None):
        print 'Downloading:',url
        try:
            if req_type == 'post':
                response = self.session.post(url, data=data, headers=headers)
            elif req_type == 'get':
                response = self.session.get(url, data=data, headers=headers)
            html = response.text
            #print dir(response)
            code = response.status_code
            self.session.cookies.save()
        except Exception as e:
            print 'Download err:',str(e)
            html = ''
            code = None
            if hasattr(e,'code'):
                code = e.code
                if self.num_retries > 0 and 500 <= code < 600:
                    return self.download(url, req_type, num_retries-1,data, headers)
                else:
                    code = None
        return {'html':html,'code':code}



#防止过快访问同一域名被封IP
class Throttle():
    def __init__(self, delay):
        self.delay = delay
        self.domain = {}

    def wait(self,url):
        domain = urlparse.urlsplit(url).netloc
        last_access = self.domain.get(domain)
        if self.delay > 0 and last_access is not None:
            sleep_sec = self.delay - (datetime.now() - last_access).seconds
            if sleep_sec > 0:
                time.sleep(sleep_sec)
        self.domain[domain] = datetime.now()

def get_xsrf():
    index_url = 'https://www.zhihu.com'
    index_page = session.get(index_url, headers=headers)
    html = index_page.text
    pattern = r'name="_xsrf" value="(.*?)"'
    _xsrf = re.findall(pattern, html)
    return _xsrf[0]

import re
import HTMLParser
import json
def login(D,headers):
    print 'try to login zhihu ......'
    index_url = 'https://www.zhihu.com'
    html = D(index_url, 'get',headers=headers)
    pattern = r'name="_xsrf" value="(.*?)"'
    _xsrf = re.findall(pattern, html)

    login_url = 'https://www.zhihu.com/login/phone_num'
    data = {
        '_xsrf': _xsrf[0],
        'password': '405938055',
        'remember_me': 'true',
        'phone_num': '13349901882',
    }
    html = D(login_url, 'post',data=data,headers=headers)

    #add capcha


def save_msg(msg):
    file = open('userinfo.txt','a')
    line = ''
    for key in msg.keys():
        tmp = ('{}:[{}],').format(str(key),str(msg[key]))
        line += tmp

    print line
    file.write(line)
    file.write('\n')
    file.close()

import pymongo
class Mongodb():
    def __init__(self):
        connection = pymongo.MongoClient()
        self.db = connection.zhihu_user
        self.tb = self.db.user_info

    def save(self,record):
        self.tb.insert(record)

    def clear(self):
        self.db.user_info.drop()


import redis


class RedisQueue():
    def __init__(self, quename, setname):
        self.__db = redis.Redis(host='localhost', port=6379, db=1)
        self.craw_queue = quename
        self.craw_set = setname

    def qsize(self):
        return self.__db.llen(self.craw_queue)

    def empty(self):
        return self.qsize()==0

    def append_to_queue(self, url):
        if not self.__db.sismember(self.craw_set, url):
            self.__db.sadd(self.craw_set, url)
            self.__db.rpush(self.craw_queue, url)
        else:
            pass

    def pop(self):
        return self.__db.lpop(self.craw_queue)





import lxml.html
def parse_html(html,user_id,db):
    try:
        jsdata = re.search('data-state=\"(.*)\"\sdata-config', html).group(1)
    except:
        return []
    html_parser = HTMLParser.HTMLParser()
    new_cont = html_parser.unescape(jsdata)
    js = json.loads(new_cont)
    #print js

    outmsg = {}
    outmsg['name'] = js['entities']['users'][user_id]['name']
    outmsg['gender'] = js['entities']['users'][user_id]['gender']
    if 'locations' in js['entities']['users'][user_id] and js['entities']['users'][user_id]['locations']:
        outmsg['locations'] = js['entities']['users'][user_id]['locations'][0]['name']
    if 'business' in js['entities']['users'][user_id]:
        outmsg['business'] = js['entities']['users'][user_id]['business']['name']
    if 'educations' in js['entities']['users'][user_id]:
        if 'major' in js['entities']['users'][user_id]['educations'] and js['entities']['users'][user_id]['educations']['major']:
            outmsg['major'] = js['entities']['users'][user_id]['educations'][0]['major']['name']
        if  'school' in js['entities']['users'][user_id]['educations'] and js['entities']['users'][user_id]['educations']['school']:
            outmsg['school'] = js['entities']['users'][user_id]['educations'][0]['school']['name']
    outmsg['be_approve'] = js['entities']['users'][user_id]['voteupCount']#被赞数
    outmsg['followingCount'] = js['entities']['users'][user_id]['followingCount']#关注数
    outmsg['followerCount'] = js['entities']['users'][user_id]['followerCount']#被关注数
    outmsg['answerCount'] = js['entities']['users'][user_id]['answerCount']
    outmsg['questionCount'] = js['entities']['users'][user_id]['questionCount']

    #for key in outmsg:
        #print key,outmsg[key]
    #save_msg(outmsg) 保存到文件接口
    try:
        print outmsg
        db.save(outmsg)
    except:
        print 'Save to db fail:',outmsg

    links = []
    tree = lxml.html.fromstring(html)
    for link in tree.xpath("//a[@class='UserLink-link']/@href"):
        l = ('https://www.zhihu.com{}/following').format(link)
        links.append(l)
    return links

def start(seed_url,D,headers):
    db = Mongodb()
    que = RedisQueue('queue','set')
    que.append_to_queue(seed_url)
    while not que.empty():
        url = que.pop()
        html = D(url, 'get', headers=headers)
        if not html:
            print 'DownloadFail:',url
            continue
        user_id = re.search('/(people|org)/(.*)/following',url).group(2)
        links = parse_html(html,user_id,db)
        for link in links:
            que.append_to_queue(link)

if __name__ == '__main__':
    D = Downloader()
    headers = {"Host": "www.zhihu.com", "Referer": "https://www.zhihu.com/"}
    login(D, headers)

    seed_url = 'https://www.zhihu.com/people/Danchenko/following'
    start(seed_url, D, headers)


