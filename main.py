#from inspect import isframe
import os
#from xmlrpc.client import FastMarshaller
import requests
from bs4 import BeautifulSoup as bs
from os import path
import log21
import shutil
import configparser
from collections import defaultdict
import re
import random
from pathlib import Path
import json

# set log level
log21.basicConfig(level=log21.DEBUG)
# log21.basicConfig(level=log21.INFO)
# log level example
# log21.debug('debug')
# log21.info('info')
# log21.warning('warning')
# log21.error('error')
# log21.critical('critical')

# set configuration
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
serverCode = 'global'

def startProcess():
    
    # check lock file if this script is running
    checkLockFile()

    # create lock file
    createLockFile()
    
    # create path
    createVideoPath()

    # check website is available
    siteIsAvailable()
    
    # get content from latest-update page
    getAllLinkPropertiesOnLatestPage()

    # check video component
    checkVideoComponent()

    # check video exists
    checkVideoIsExists()

    # download video 
    downloadVideo()

    # download video preview
    downloadVideoPreview()

    # download cover image
    downloadCoverImage()

    # get server code()
    getServerCode()

    # map categories
    mappingCategories()

    # api call register
    apiCall()

    # clear lock file
    removeLockFile()

    log21.info('all completed..')

    exit()

def mappingCategories():
    log21.debug('mapping categories')
    try:
        response = requests.post(apiUrl+'/'+apiGetCategory)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        log21.debug('request to url error: ',apiUrl+'/'+apiGetCategory)
    if response.status_code != 200:
        log21.error('site',apiUrl+'/'+apiGetCategory,' is not available')
        log21.debug('request to url error: ',response.status_code)
    log21.debug('site',apiUrl,'/',apiGetCategory,' is 200OK')
    response = response.json()
    if response['success'] == True:
        listCat = response['result']
        log21.info('list all categories get from api service is:',[category['title'] for category in listCat])
    for key in videoProp.keys():
        videoProp[key]['categoriesid'] = apiCategoriesIDDefault # default other
        log21.info('default categories id for',videoProp[key]['id'],'is 其他 (',videoProp[key]['categoriesid'],')')
        breaker = False
        for cat in videoProp[key]['categories']:
            for apiCat in listCat:
                if cat == apiCat['title']:
                    videoProp[key]['categoriesid'] = str(apiCat['id'])
                    log21.info('new match categories id for',videoProp[key]['id'],'is',apiCat['title'],'(',videoProp[key]['categoriesid'],')')
                    breaker = True
                    break
            if breaker == True:
                break
    return True

def getServerCode():
    log21.debug('get server code from api')
    try:
        response = requests.post(apiUrl+'/'+apiGetServerList)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        log21.debug('request to url error: ',apiUrl+'/'+apiGetServerList)
        return True
    if response.status_code != 200:
        log21.error('site',apiUrl+'/'+apiGetServerList,' is not available')
        log21.debug('request to url error: ',response.status_code)
        return True
    log21.debug('site',apiUrl,'/',apiGetServerList,' is 200OK')
    response = response.json()
    if response['success'] == True:
        serverCode = response['result'][0]['serverCode']
        log21.info('api response servercode is:',serverCode)
    return True

def apiCall():
    log21.debug('api call for register new videos')
    for key in videoProp.keys():
        videoUpdate = { 'id': str(videoProp[key]['id']), 
                        'title': str(videoProp[key]['title']), 
                        'imgUrl': str(videoProp[key]['videoimagepath'].split('85tube/')[1]), 
                        'videoUrl': str(videoProp[key]['videofilepathsendapi'].split('85tube/')[1]), 
                        'demoUrl': str(videoProp[key]['videofilepreviewpath'].split('85tube/')[1]), 
                        'serverCode': str(serverCode), 
                        'videoType': str(2), # 2 is mp4, 1 is m3u8
                        'categoryId': str(videoProp[key]['categoriesid']), 
                        'tagIds': str(videoProp[key]['tags']), 
                        'playTime': str(videoProp[key]['duration'])}
        try:
            response = requests.post(apiUrl+'/'+apiVideoUpdate,data=json.dumps(videoUpdate), headers={'Content-Type': 'application/json;charset-UTF-8'})
        except requests.exceptions.RequestException as e:
            log21.error(e)
            continue
        if response.status_code != 200:
            log21.info('request to url error code: ',response.status_code,int(key+1),'/',len(videoProp.keys()))
            log21.debug(response.json())
            continue
        log21.info(response.json())
    return True

def checkLockFile():
    log21.debug('check lock file')
    if os.path.exists(os.path.join(os.getcwd(), r'inprogress.lock')):
        log21.error('this script is running, can run again after this task is finished')
        exit()

def createLockFile():
    log21.debug('create lock file')
    if not os.path.exists(os.path.join(os.getcwd(), r'inprogress.lock')):
        Path(os.path.join(os.getcwd(), r'inprogress.lock')).touch()
    return True

def removeLockFile():
    log21.debug('remove lock file')
    if os.path.exists(os.path.join(os.getcwd(), r'inprogress.lock')):
        Path(os.path.join(os.getcwd(), r'inprogress.lock')).unlink()
    return True

def downloadCoverImage():
    log21.debug('download cover image')
    for key in videoProp.keys():
        videoProp[key]['videoimagepath'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'_image.jpg')
        log21.info('do download video cover image for ',videoProp[key]['id'],videoProp[key]['image'])
        try:
            with requests.get(videoProp[key]['image'], stream=True) as r:
                with open(videoProp[key]['videoimagepath'], 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
        except requests.exceptions.RequestException as e:
            log21.error(e)
        log21.debug('download cover image success: ',int(key+1),'/',len(videoProp.keys()))

    return True

def downloadVideoPreview():
    log21.debug('download video preview')
    for key in videoProp.keys():
        videoProp[key]['videofilepreviewpath'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'_preview.mp4')
        log21.info('do download video priview for ',videoProp[key]['id'],videoProp[key]['videopreview'])
        try:
            with requests.get(videoProp[key]['videopreview'], stream=True) as r:
                with open(videoProp[key]['videofilepreviewpath'], 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
        except requests.exceptions.RequestException as e:
            log21.error(e)
        log21.debug('download video preview success: ',int(key+1),'/',len(videoProp.keys()))
                
    return True

def checkVideoIsExists():
    log21.debug('check video is exists')
    for key in list(videoProp.keys()):
        if os.path.exists(os.path.join(videosPath, videoProp[key]['id'])) and os.path.exists(os.path.join(videosPath, videoProp[key]['id'],videoProp[key]['id'] + '.mp4')):
            log21.info('video is exists: ' + videosPath + '/' +videoProp[key]['id'] + '/' + videoProp[key]['id'] + '.mp4')
            videoProp.pop(key, None)
    if len(videoProp) == 0:
        log21.info('no video files to download')
        removeLockFile()
        exit()

    return True

def checkVideoComponent():
    log21.debug('check video component')
    for key in list(videoProp.keys()):
        if videoProp[key]['id'] == None or videoProp[key]['href'] == None or videoProp[key]['title'] == None or videoProp[key]['image'] == None:
            videoProp.pop(key, None)
            log21.warning('video' + key + 'incomplete components')
        # # debug test for fast 3 videos download
        # if int(key) > int(2):
        #     videoProp.pop(key, None)
        # # end debug
    if len(videoProp) == 0:
        log21.info('no video files to download')
        removeLockFile()
        exit()
        
    return True

def createVideoPath():
    log21.debug('create video path')
    if not os.path.exists(videosPath):
        os.makedirs(videosPath)
        log21.debug('create directory',videosPath)

    return True

def downloadVideo():
    log21.debug('download video')
    for key in videoProp.keys():
        # print(videoProp[key]['id'])
        # print(videoProp[key]['href'])
        # print(videoProp[key]['title'])
        # print(videoProp[key]['image'])
        # print(videoProp[key]['videopreview'])
        # print(videoProp[key]['hd'])
        downloadPath = os.path.join(videosPath, videoProp[key]['id'])
        videoProp[key]['sourcepath'] = downloadPath
        if not os.path.exists(downloadPath):
            os.makedirs(downloadPath)
            log21.debug('make dir',downloadPath)

        try:
            response = requests.get(videoProp[key]['href'])
        except requests.exceptions.RequestException as e:
            log21.error(e)
            log21.debug('request to url error: ',int(key+1),'/',len(videoProp.keys()))
            continue
        if response.status_code != 200:
            log21.error('site',videoProp[key]['href'],' is not available')
            log21.debug('request to url error: ',response.status_code,int(key+1),'/',len(videoProp.keys()))
            continue
        log21.debug('site '+videoProp[key]['href']+' is 200OK')
        
        soup = bs(response.text, 'html.parser')

        # get video tag
        tags = soup.find("meta", attrs={'name': 'keywords'})
        videoProp[key]['tags'] = ''
        if tags['content']:
            videoProp[key]['tags'] = tags['content'].replace(" ", "")
        log21.debug('video tags:',videoProp[key]['tags'])

        # get video categories
        videoProp[key]['categories'] = ['其他'] #อื่นๆ
        match = re.compile(r"video_categories:\s*'(.*?)',")
        for script in soup.find_all("script", {"src":False}):
            if script:            
                cat = match.search(script.string)
                if cat != None:
                    category = cat.group(1)
                    videoProp[key]['categories'] = category.replace(" ", "").split(",")
                    break
        log21.debug('video categories:',videoProp[key]['tags'])
        
        # download 720p and 1080p
        if videoProp[key]['hd'] == True:
            log21.info('check video HD for',videoProp[key]['id'])
            
            # 720p
            p720 = re.compile(r"video_alt_url:\s*'((http|https)://85tube.com/get_file/[a-z0-9\/\_\.\?]+=[0-9]+)',")
            for script in soup.find_all("script", {"src":False}):
                if script:            
                    m720 = p720.search(script.string)
                    if m720 != None:
                        videoProp[key]['downloadurl720'] = m720.group(1)
                        videoProp[key]['videofilepath720'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'_720p.mp4')
                        videoProp[key]['videofilepathsendapi'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'_720p.mp4')
                        break
            if 'downloadurl720' in videoProp[key] and videoProp[key]['downloadurl720']:
                log21.debug('video src for 720:',videoProp[key]['downloadurl720'])
                log21.info('do download video for',videoProp[key]['id'],videoProp[key]['downloadurl720'])
                try:
                    with requests.get(videoProp[key]['downloadurl720'], stream=True) as r:
                        with open(videoProp[key]['videofilepath720'], 'wb') as f:
                            shutil.copyfileobj(r.raw, f)
                except requests.exceptions.RequestException as e:
                    log21.error(e)
            else:
                log21.info('no video files in 720p resolution for',videoProp[key]['id'])

            # # 1080p
            # p1080 = re.compile(r"video_alt_url2:\s*'((http|https)://85tube.com/get_file/[a-z0-9\/\_\.\?]+=[0-9]+)',")      
            # for script in soup.find_all("script", {"src":False}):
            #     if script:            
            #         m1080 = p1080.search(script.string)
            #         if m1080 != None:
            #             videoProp[key]['downloadurl1080'] = m1080.group(1)
            #             videoProp[key]['videofilepath1080'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'_1080p.mp4')
            #             break
            # if 'downloadurl1080' in videoProp[key] and videoProp[key]['downloadurl1080']:
            #     log21.debug('video src for 1080:',videoProp[key]['downloadurl1080'])
            #     log21.info('do download video for ',videoProp[key]['id'],videoProp[key]['downloadurl1080'])
            #     try:
            #         with requests.get(videoProp[key]['downloadurl1080'], stream=True) as r:
            #             with open(videoProp[key]['videofilepath1080'], 'wb') as f:
            #                 shutil.copyfileobj(r.raw, f)
            #     except requests.exceptions.RequestException as e:
            #         log21.error(e)
            # else:
            #     log21.info('no video files in 1080p resolution for',videoProp[key]['id'])
        # else download 480p default
        else:
            log21.info('no video files HD resolution for',videoProp[key]['id'])
            # download 480p default
            p480 = re.compile(r"video_url:\s*'((http|https)://85tube.com/get_file/[a-z0-9\/\_\.\?]+=[0-9]+)',")
            for script in soup.find_all("script", {"src":False}):
                if script:            
                    m480 = p480.search(script.string)
                    if m480 != None:
                        videoProp[key]['downloadurl480'] = m480.group(1)
                        videoProp[key]['videofilepath480'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'.mp4')
                        videoProp[key]['videofilepathsendapi'] = os.path.join(videoProp[key]['sourcepath'],videoProp[key]['id']+'.mp4')
                        break
            log21.debug('video src for 480p',videoProp[key]['downloadurl480'])
            if videoProp[key]['downloadurl480'] == None:
                log21.warning('cannot get video source for',videoProp[key]['href'])
                log21.debug('cannot get video source: ',int(key+1),'/',len(videoProp.keys()))
                continue   
            log21.info('do download video for ',videoProp[key]['id'],videoProp[key]['downloadurl480'])
            try:
                with requests.get(videoProp[key]['downloadurl480'], stream=True) as r:
                    with open(videoProp[key]['videofilepath480'], 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
            except requests.exceptions.RequestException as e:
                log21.error(e)
                log21.debug('request to url error: ',int(key+1),'/',len(videoProp.keys()))
                continue

        log21.debug('download videos success: ',int(key+1),'/',len(videoProp.keys()))

    return True

def getAllLinkPropertiesOnLatestPage():
    log21.debug('get all link on latest-update page')
    pageRandom = random.randint(1,int(allPageCount))
    log21.debug('page random for get video:',pageRandom)
    urlReg = siteUrl+'/'+siteUrlLastedUpdate+'/'+str(pageRandom)+'/'
    log21.info('get all video on random page',urlReg)
    try:
        response = requests.get(urlReg)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        raise SystemExit(e)
    if response.status_code != 200:
        log21.error('site '+urlReg+' is not available')
        removeLockFile()
        exit()
    log21.debug('site '+urlReg+' is 200OK')
    
    soup = bs(response.text, 'html.parser')
    divs = soup.find_all("div",{"class":"item"})
    for index,div in enumerate(divs):
        soup = bs(str(div), 'html.parser')
        a = soup.find("a")
        img = soup.find("img")
        duration = soup.find("div",{"class":"duration"})
        hd = soup.find("span",{"class":"is-hd"})
        id = soup.find("span",{"class":"ico-fav-0"})
        videoProp[index]['id'] = id['data-fav-video-id']
        videoProp[index]['href'] = a['href']
        videoProp[index]['title'] = a['title']
        videoProp[index]['image'] = img['data-original']
        videoProp[index]['videopreview'] = img['data-preview']
        videoProp[index]['hd'] = True if hd else False
        videoProp[index]['duration'] = duration.string
        log21.debug(
            "id:",videoProp[index]['id'],"\n"
            "href:",videoProp[index]['href'],"\n"
            "title:",videoProp[index]['title'],"\n"
            "image:",videoProp[index]['image'],"\n"
            "videopreview:",videoProp[index]['videopreview'],"\n"
            "hd:",videoProp[index]['hd'],"\n"
            "duration:",videoProp[index]['duration']
        )
    log21.debug('number of video(s):',len(videoProp.keys()),)
    return videoProp

def siteIsAvailable():
    log21.debug('check site is available ' + siteUrl)
    try:
        response = requests.get(siteUrl)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        raise SystemExit(e)
    if response.status_code != 200:
        log21.error('site '+siteUrl+' is not available')
        removeLockFile()
        exit()
    log21.debug('site '+siteUrl+' is 200OK')

    return True
    
if __name__ == "__main__":
    startProcess()