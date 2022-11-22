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
import ffmpeg

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
    getAllLinkPropertiesOnRandomPage()

    # check video component
    checkVideoComponent()

    # check video exists
    checkVideoIsExists()

    # get server code()
    getServerCode()

    # downloadvideo, videopreview, imagecover, mappingcategories, apiregistercall
    operationWorker()

    # remove categories get from api server
    removeCategoriesFile()

    # clear lock file
    removeLockFile()

    log21.info('all completed..')

    exit()

def operationWorker():
    log21.debug('all operation worker')
    for index in videoProp.keys():
        downloadVideo(index)
        convertTom3u8(index,videoProp[index]['videofilepathsendapi'],'videoFull')
        downloadVideoPreview(index)
        convertTom3u8(index,videoProp[index]['videofilepreviewpath'],'videoPreview')
        downloadCoverImage(index)
        mappingCategories(index)
        apiCall(index)

def convertTom3u8(index,videoPath,videoType):
    log21.debug('convert to m3u8',videoPath)
    if not os.path.exists(videoPath): 
        log21.warning('not found file',videoPath)
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
        return True
    videoName = os.path.basename(os.path.splitext(videoPath)[0])
    m3u8File = os.path.join(videoProp[index]['sourcepath'],videoName+'.m3u8')
    log21.debug('original video MP4 file:',videoPath)
    log21.debug('original video name:',videoName)
    log21.info('M3U8 output file:',m3u8File)
    inputFile = ffmpeg.input(videoPath, f='mp4')
    outputFile = ffmpeg.output(inputFile, m3u8File, format='hls', start_number=0, hls_time=5, hls_list_size=0)
    ffmpeg.run(outputFile)

    if videoType == 'videoFull':
        videoProp[index]['videopathm3u8sendapi'] = m3u8File
    else:
        videoProp[index]['videopreviewpathm3u8sendapi'] = m3u8File

    return True

def removeCategoriesFile():
    log21.debug('remove categories file get from api server')
    if os.path.exists(os.path.join(os.getcwd(), r'categoriesFromServerAPI.json')): 
        Path(os.path.join(os.getcwd(), r'categoriesFromServerAPI.json')).unlink()
    return True

def mappingCategories(index):
    log21.debug('mapping categories')
    
    videoProp[index]['categoriesid'] = apiCategoriesIDDefault # default other
    log21.info('default categories id for',videoProp[index]['id'],'is 其他 (',videoProp[index]['categoriesid'],')')

    # first time, it call api for get all categories form server , and write to file
    if not os.path.exists(os.path.join(os.getcwd(), r'categoriesFromServerAPI.json')): 
        try:
            listCatFromAPI = requests.post(apiUrl+'/'+apiGetCategory)
        except requests.exceptions.RequestException as e:
            log21.error(e)
            log21.debug('request to url error: ',apiUrl+'/'+apiGetCategory)
        if listCatFromAPI.status_code != 200:
            log21.error('site',apiUrl+'/'+apiGetCategory,' is not available')
            log21.debug('request to url error: ',listCatFromAPI.status_code)
        try:
            listCatFromAPI = listCatFromAPI.json()
        except ValueError:  # includes simplejson.decoder.JSONDecodeError
            log21.warning('Decoding JSON from',apiUrl+'/'+apiGetCategory,'has failed')
        if 'success' in listCatFromAPI and listCatFromAPI['success'] == True:
            with open(os.path.join(os.getcwd(), r'categoriesFromServerAPI.json'), "w") as outFile:
                jsonObject = json.dumps(listCatFromAPI, indent=4)
                outFile.write(jsonObject)
                log21.debug('write file:',os.path.join(os.getcwd(), r'categoriesFromServerAPI.json'))

    # second time, it read content form json file
    if os.path.exists(os.path.join(os.getcwd(), r'categoriesFromServerAPI.json')):
        with open(os.path.join(os.getcwd(), r'categoriesFromServerAPI.json'), 'r') as openFile:
            listCatFromAPI = json.load(openFile)
        if 'result' in listCatFromAPI:
            listCat = listCatFromAPI['result']
            log21.info('list all categories get from api service is:',[category['title'] for category in listCat])
            breaker = False
            for cat in videoProp[index]['categories']:
                for apiCat in listCat:
                    if cat == apiCat['title']:
                        videoProp[index]['categoriesid'] = str(apiCat['id'])
                        log21.info('new match categories id for',videoProp[index]['id'],'is',apiCat['title'],'(',videoProp[index]['categoriesid'],')')
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

def apiCall(index):
    log21.debug('api call for register new videos')
    if videoProp[index]['isregister'] == False:
        log21.info('video component id',videoProp[index]['id'],'is not valid. do not register',response.status_code,int(index+1),'/',len(videoProp.keys()))
        return True
    videoUpdate = { 'id': str(videoProp[index]['id']), 
                    'title': str(videoProp[index]['title']), 
                    'imgUrl': str(videoProp[index]['videoimagepath'].split('85tube/')[1]), 
                    'videoUrl': str(videoProp[index]['videopathm3u8sendapi'].split('85tube/')[1]), 
                    'demoUrl': str(videoProp[index]['videopreviewpathm3u8sendapi'].split('85tube/')[1]), 
                    'serverCode': str(serverCode), 
                    'videoType': str(1), # 2 is mp4, 1 is m3u8
                    'categoryId': str(videoProp[index]['categoriesid']), 
                    'tagIds': str(videoProp[index]['tags']), 
                    'playTime': str(videoProp[index]['duration'])}
    log21.debug('data request to update video',videoUpdate)
    try:
        response = requests.post(apiUrl+'/'+apiVideoUpdate,data=json.dumps(videoUpdate), headers={'Content-Type': 'application/json;charset-UTF-8'}, timeout=15)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
        return True
    if response.status_code != 200:
        log21.info('request to url error code: ',response.status_code,int(index+1),'/',len(videoProp.keys()))
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
        return True
    
    try:
        log21.info(response.json())
    except ValueError:  # includes simplejson.decoder.JSONDecodeError
        log21.info('Decoding JSON has failed')
    
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

def downloadCoverImage(index):
    log21.debug('download cover image')
    videoProp[index]['videoimagepath'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_image.jpg')
    log21.info('do download video cover image for ',videoProp[index]['id'],videoProp[index]['image'])
    try:
        with requests.get(videoProp[index]['image'], stream=True) as r:
            with open(videoProp[index]['videoimagepath'], 'wb') as f:
                shutil.copyfileobj(r.raw, f)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
    log21.debug('download cover image success: ',int(index+1),'/',len(videoProp.keys()))

    return True

def downloadVideoPreview(index):
    log21.debug('download video preview')
    videoProp[index]['videofilepreviewpath'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_preview.mp4')
    log21.info('do download video priview for ',videoProp[index]['id'],videoProp[index]['videopreview'])
    try:
        with requests.get(videoProp[index]['videopreview'], stream=True) as r:
            with open(videoProp[index]['videofilepreviewpath'], 'wb') as f:
                shutil.copyfileobj(r.raw, f)
    except requests.exceptions.RequestException as e:
        log21.error(e)
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
    log21.debug('download video preview success: ',int(index+1),'/',len(videoProp.keys()))
                
    return True

def checkVideoIsExists():
    log21.debug('check video is exists')
    for key in list(videoProp.keys()):
        if os.path.exists(os.path.join(videosPath, videoProp[key]['id'])) and (os.path.exists(os.path.join(videosPath, videoProp[key]['id'],videoProp[key]['id'] + '_720p.mp4')) or os.path.exists(os.path.join(videosPath, videoProp[key]['id'],videoProp[key]['id'] + '_480p.mp4'))):
            log21.info('video is exists: ' + videosPath + '/' +videoProp[key]['id'] + '/' + videoProp[key]['id'])
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

def downloadVideo(index):
    log21.debug('download video')
    # print(videoProp[index]['id'])
    # print(videoProp[index]['href'])
    # print(videoProp[index]['title'])
    # print(videoProp[index]['image'])
    # print(videoProp[index]['videopreview'])
    # print(videoProp[index]['hd'])
    downloadPath = os.path.join(videosPath, videoProp[index]['id'])
    videoProp[index]['sourcepath'] = downloadPath
    if not os.path.exists(downloadPath):
        os.makedirs(downloadPath)
        log21.debug('make dir',downloadPath)

    try:
        response = requests.get(videoProp[index]['href'])
    except requests.exceptions.RequestException as e:
        log21.error(e)
        log21.debug('request to url error: ',int(index+1),'/',len(videoProp.keys()))
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
        return True
    if response.status_code != 200:
        log21.error('site',videoProp[index]['href'],' is not available')
        log21.debug('request to url error: ',response.status_code,int(index+1),'/',len(videoProp.keys()))
        shutil.rmtree(videoProp[index]['sourcepath'])
        log21.debug('removed path:',videoProp[index]['sourcepath'])
        videoProp[index]['isregister'] = False
        log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
        return True
    log21.debug('site '+videoProp[index]['href']+' is 200OK')
    
    soup = bs(response.text, 'html.parser')

    # get video tag
    tags = soup.find("meta", attrs={'name': 'keywords'})
    videoProp[index]['tags'] = ''
    if tags['content']:
        videoProp[index]['tags'] = tags['content'].replace(" ", "")
    log21.debug('video tags:',videoProp[index]['tags'])

    # get video categories
    videoProp[index]['categories'] = ['其他'] #อื่นๆ
    match = re.compile(r"video_categories:\s*'(.*?)',")
    for script in soup.find_all("script", {"src":False}):
        if script:            
            cat = match.search(script.string)
            if cat != None:
                category = cat.group(1)
                videoProp[index]['categories'] = category.replace(" ", "").split(",")
                break
    log21.debug('video categories:',videoProp[index]['tags'])
    
    # download 720p and 1080p
    if videoProp[index]['hd'] == True:
        log21.info('check video HD for',videoProp[index]['id'])
        
        # 720p
        p720 = re.compile(r"video_alt_url:\s*'((http|https)://85tube.com/get_file/[a-z0-9\/\_\.\?]+=[0-9]+)',")
        for script in soup.find_all("script", {"src":False}):
            if script:            
                m720 = p720.search(script.string)
                if m720 != None:
                    videoProp[index]['downloadurl720'] = m720.group(1)
                    videoProp[index]['videofilepath720'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_720p.mp4')
                    videoProp[index]['videofilepathsendapi'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_720p.mp4')
                    break
        if 'downloadurl720' in videoProp[index] and videoProp[index]['downloadurl720']:
            log21.debug('video src for 720:',videoProp[index]['downloadurl720'])
            log21.info('do download video for',videoProp[index]['id'],videoProp[index]['downloadurl720'])
            try:
                with requests.get(videoProp[index]['downloadurl720'], stream=True) as r:
                    with open(videoProp[index]['videofilepath720'], 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
            except requests.exceptions.RequestException as e:
                log21.error(e)
                shutil.rmtree(videoProp[index]['sourcepath'])
                log21.debug('removed path:',videoProp[index]['sourcepath'])
                videoProp[index]['isregister'] = False
                log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
                return True
        else:
            log21.info('no video files in 720p resolution for',videoProp[index]['id'])

            # # 1080p
            # p1080 = re.compile(r"video_alt_url2:\s*'((http|https)://85tube.com/get_file/[a-z0-9\/\_\.\?]+=[0-9]+)',")      
            # for script in soup.find_all("script", {"src":False}):
            #     if script:            
            #         m1080 = p1080.search(script.string)
            #         if m1080 != None:
            #             videoProp[index]['downloadurl1080'] = m1080.group(1)
            #             videoProp[index]['videofilepath1080'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_1080p.mp4')
            #             break
            # if 'downloadurl1080' in videoProp[index] and videoProp[index]['downloadurl1080']:
            #     log21.debug('video src for 1080:',videoProp[index]['downloadurl1080'])
            #     log21.info('do download video for ',videoProp[index]['id'],videoProp[index]['downloadurl1080'])
            #     try:
            #         with requests.get(videoProp[index]['downloadurl1080'], stream=True) as r:
            #             with open(videoProp[index]['videofilepath1080'], 'wb') as f:
            #                 shutil.copyfileobj(r.raw, f)
            #     except requests.exceptions.RequestException as e:
            #         log21.error(e)
            #           shutil.rmtree(videoProp[index]['sourcepath'])
            #           log21.debug('removed path:',videoProp[index]['sourcepath'])
            #           videoProp[index]['isregister'] = False
            #           log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
            # else:
            #     log21.info('no video files in 1080p resolution for',videoProp[index]['id'])
    # else download 480p default
    else:
        log21.info('no video files HD resolution for',videoProp[index]['id'])
        # download 480p default
        p480 = re.compile(r"video_url:\s*'((http|https)://85tube.com/get_file/[a-z0-9\/\_\.\?]+=[0-9]+)',")
        for script in soup.find_all("script", {"src":False}):
            if script:            
                m480 = p480.search(script.string)
                if m480 != None:
                    videoProp[index]['downloadurl480'] = m480.group(1)
                    videoProp[index]['videofilepath480'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_480p.mp4')
                    videoProp[index]['videofilepathsendapi'] = os.path.join(videoProp[index]['sourcepath'],videoProp[index]['id']+'_480p.mp4')
                    break
        log21.debug('video src for 480p',videoProp[index]['downloadurl480'])
        if videoProp[index]['downloadurl480'] == None:
            log21.warning('cannot get video source for',videoProp[index]['href'])
            log21.debug('cannot get video source: ',int(index+1),'/',len(videoProp.keys()))
            return True   
        log21.info('do download video for ',videoProp[index]['id'],videoProp[index]['downloadurl480'])
        try:
            with requests.get(videoProp[index]['downloadurl480'], stream=True) as r:
                with open(videoProp[index]['videofilepath480'], 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
        except requests.exceptions.RequestException as e:
            log21.error(e)
            log21.debug('request to url error: ',int(index+1),'/',len(videoProp.keys()))
            shutil.rmtree(videoProp[index]['sourcepath'])
            log21.debug('removed path:',videoProp[index]['sourcepath'])
            videoProp[index]['isregister'] = False
            log21.debug('removed video id:',index,'(',videoProp[index]['id'],')')
            return True

    log21.debug('download videos success: ',int(index+1),'/',len(videoProp.keys()))

    return True

def getAllLinkPropertiesOnRandomPage():
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
        videoProp[index]['isregister'] = True
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