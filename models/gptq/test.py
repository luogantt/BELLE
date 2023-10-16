#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 16 14:23:58 2023

@author: oem
"""

'''
@author: nl8590687
ASRT语音识别asrserver http协议测试专用客户端
'''
import base64
import json
import time
import requests
from utils.ops import read_wav_bytes



#服务器ip
URL = 'http://192.168.3.9:8081'

#wav_bytes, sample_rate, channels, sample_width = read_wav_bytes('out.wav')
data = {
    'status': ' 如何理解黑格尔的 量变引起质变规律和否定之否定规律',

}


t0=time.time()
r = requests.post(URL,  data=data)
t1=time.time()
r.encoding='utf-8'

result = json.loads(r.text)
print(result)
print('time:', t1-t0, 's')

