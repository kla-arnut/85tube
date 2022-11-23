import os
import requests
from bs4 import BeautifulSoup as bs
from os import path
import log21
import configparser
from collections import defaultdict
import json

log21.basicConfig(level=log21.DEBUG)

config = configparser.ConfigParser()
config.read('config.ini')
siteUrl = config['DEFAULT']['siteUrl']
siteUrlLastedUpdate = config['DEFAULT']['siteUrlLastedUpdate']
allPageCount = config['DEFAULT']['allPageCount']
videosPath = os.path.join(os.getcwd(), r'videos')
videoProp = defaultdict(dict)
apiUrl = config['DEFAULT']['apiUrl']
apiGetServerList = config['DEFAULT']['apiGetServerList']
apiVideoUpdate =  config['DEFAULT']['apiVideoUpdate']
apiGetCategory = config['DEFAULT']['apiGetCategory']
apiCategoriesIDDefault = config['DEFAULT']['apiCategoriesIDDefault']
serverCode = 'h_fc1'

try:
    response = requests.post(apiUrl+'/'+apiGetServerList)
except requests.exceptions.RequestException as e:
    log21.error(e)
    log21.debug('request to url error: ',apiUrl+'/'+apiGetServerList)
if response.status_code != 200:
    log21.error('site',apiUrl+'/'+apiGetServerList,' is not available')
    log21.debug('request to url error: ',response.status_code)
log21.debug('site',apiUrl,'/',apiGetServerList,' is 200OK')
response = response.json()
if 'success' in response and response['success'] == True:
    serverCode = response['result'][0]['serverCode']
    log21.info('api response servercode is:',serverCode)