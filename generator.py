#-*- coding:utf-8 -*-
import os
import openai
from moviepy.editor import *
from glob import glob
import urllib
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

# CONTENTS
def getVideoContent():
  print('Generating Content and Script')

  contentRequestList = [{
    'role': 'user',
    'content': '쓸데없지만 재밌는 상식 하나와 그 지식을 바탕으로 1분 분량 youtube 영상 script도 부탁해.\n대답은 JSON type으로 주제는 subject, youtube script는 script key에 담아서 보내줘',
  }]
  contentRes = openai.ChatCompletion.create(
      model='gpt-4',
      messages=contentRequestList
  )

  contentResponse = contentRes.choices[0].message.content
  content = json.loads(contentResponse)

  return content


# Clova Voice to TTS naration
def getNarrateFile(content):
  print('Generating TTS Naration')

  clovaConfig = {
    'apiEndpoint': 'https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts',
    'requestTemplate': 'speaker=nkyungtae&speed=-2&alpha=-1&volume=0&pitch=0&format=mp3&text=',
    'clientId': os.getenv('CLOVA_CLIENT_ID'),
    'clientSecret': os.getenv('CLOVA_CLIENT_SECRET'),
  }
  clovaRequestData = clovaConfig['requestTemplate'] + urllib.parse.quote(content['script'])
  ttsRequest = urllib.request.Request(clovaConfig['apiEndpoint'])
  ttsRequest.add_header("X-NCP-APIGW-API-KEY-ID", clovaConfig['clientId'])
  ttsRequest.add_header("X-NCP-APIGW-API-KEY", clovaConfig['clientSecret'])

  ttsResponse = urllib.request.urlopen(ttsRequest, data=clovaRequestData.encode('utf-8'))
  resCode = ttsResponse.getcode()
  if (resCode == 200):
    ttsResponseBody = ttsResponse.read()
    with open('temp/audio/narrator.mp3', 'wb') as f:
      f.write(ttsResponseBody)
  else:
    raise Exception('Clova request error', ttsResponse)


# Dalle image gen
def getImageResources(content):
  print('Generating Image sources')

  for i in range(1, 6):
      res_img = openai.Image.create(
              prompt=content['subject'],
              n=1,
              size='1024x1024'
          )
      imgUrl = res_img['data'][0]['url']
      imgPath = f'temp/image/{str(i).zfill(3)}.png'

      urllib.request.urlretrieve(imgUrl, imgPath)


# Resizing image sources
def resizingImageResources():
  print('Resizing Image sources')

  for i in range(1, 6):
      imgPath = f'temp/image/{str(i).zfill(3)}.png'
      image = Image.open(imgPath)

      resizedImage = image.resize((720, 720))
      resizedImage.save(imgPath)


def generateShortsVideo(content):
  print('Generating video...')

  # Narration audio clip
  print('Get audio sources')
  narartionAudioClip = AudioFileClip('temp/audio/narrator.mp3')
  totalDuration = narartionAudioClip.duration

  # Make Background Image
  print('Get background image source')
  backgourndImage = glob('assets/background_blue.png')
  backgroundImageClip = ImageClip(backgourndImage[0]).set_duration(totalDuration)

  # Make Content Images
  print('Get content image sources')
  contentImages = sorted(glob('temp/image/*.png')) 
  contentImageClipList = [ImageClip(contentImg)
                          .set_duration(totalDuration / len(contentImages))
                          .crossfadein(0.1)
                          .crossfadeout(0.3) for contentImg in contentImages]
  contentImageClip = concatenate_videoclips(contentImageClipList, method="compose").set_position('center')
  w, h = backgroundImageClip.size

  # Make Subtitle Text Clip
  print('Make subtitle text clip')
  textClip = TextClip(content['subject'], color='white', font='assets/font.ttf', fontsize=60)
  textClip = textClip.set_duration(totalDuration).set_position(('center', h / 8))

  # Combine Clips
  print('Combine clips')
  result = CompositeVideoClip([backgroundImageClip, contentImageClip, textClip])
  result = result.set_audio(narartionAudioClip)

  # Write Video File
  print('Write video file')
  result.write_videofile(
      'result.mp4',
      temp_audiofile='temp/audio.m4a',
      remove_temp=True,
      codec='mpeg4',
      audio_codec='aac',
      threads=8,
      fps=24)
  

def run():
  # generate video content and script
  content = getVideoContent()

  # get naraate voice mp3 file
  getNarrateFile(content)

  # image generating and formating
  getImageResources(content)
  resizingImageResources()

  # make video file
  generateShortsVideo(content)

  print('==DONE==')


# RUN
run()