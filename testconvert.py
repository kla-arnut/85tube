import ffmpeg
from os import path
import os



input_stream = ffmpeg.input(os.path.join(os.getcwd(), r'videos',r'2805',r'2805_720p.mp4'), f='mp4')
output_stream = ffmpeg.output(input_stream, os.path.join(os.getcwd(), r'videos',r'2805',r'2805_720p.m3u8'), format='hls', start_number=0, hls_time=5, hls_list_size=0)
ffmpeg.run(output_stream)