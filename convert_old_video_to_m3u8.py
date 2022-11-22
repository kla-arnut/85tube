import ffmpeg
from os import path
import os
import requests

videosPath = os.path.join(os.getcwd(), r'videos')
print('video path root:',videosPath)
allDir = [ f.path for f in os.scandir(videosPath) if f.is_dir() ]
print('all video path:',"\n","\n".join(allDir))
print()

count = 1
for dir in allDir:
    print()
    videoID = os.path.basename(os.path.normpath(dir))
    videoFile = None
    videoPreview = None
    # get video name
    if os.path.exists(os.path.join(dir,videoID+'_720p.mp4')):
        videoFile = os.path.join(dir,videoID+'_720p.mp4')
    elif os.path.exists(os.path.join(dir,videoID+'.mp4')):
        videoFile = os.path.join(dir,videoID+'.mp4')
    else:
        print('not found video for',dir)
    # get video preview
    if os.path.exists(os.path.join(dir,videoID+'_preview.mp4')):
        videoPreview = os.path.join(dir,videoID+'_preview.mp4')

    # convert video from mp4 to m3u8
    videoPathRegis = 'videos'
    if videoFile != None:
        videoName = os.path.basename(os.path.splitext(videoFile)[0])
        m3u8File = os.path.join(dir,videoName+'.m3u8')
        print('video file/input file:',videoFile)
        print('video name:',videoName)
        print('output file:',m3u8File)
        inputFile = ffmpeg.input(videoFile, f='mp4')
        outputFile = ffmpeg.output(inputFile, m3u8File, format='hls', start_number=0, hls_time=5, hls_list_size=0)
        ffmpeg.run(outputFile)

    if videoPreview != None:
        videoPreviewName = os.path.basename(os.path.splitext(videoPreview)[0])
        m3u8PreviewFile = os.path.join(dir,videoPreviewName+'.m3u8')
        print('video preview file/input file:',videoPreview)
        print('video preview name:',videoPreviewName)
        print('output file:',m3u8PreviewFile)
        inputFile = ffmpeg.input(videoPreview, f='mp4')
        outputFile = ffmpeg.output(inputFile, m3u8PreviewFile, format='hls', start_number=0, hls_time=5, hls_list_size=0)
        ffmpeg.run(outputFile)
    
    print('successful',count,'of',len(allDir))
    count = count+1
