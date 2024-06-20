#-*- coding:utf-8 -*-
import os
import openai
from moviepy.editor import *
from glob import glob
import json
import suno
import math
import numpy
from PIL import Image, ImageDraw, ImageFont
import datetime as dt
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

# region Datas
regionDatas = {
  'seoul': {
    'x': 308,
    'y': 409,
    'korean': '서울',
  },
    'incheon': {
    'x': 153,
    'y': 485,
    'korean': '인천',
  },
  'daejeon': {
    'x': 318,
    'y': 909,
    'korean': '대전',
  },
  'daegu': {
    'x': 610,
    'y': 940,
    'korean': '대구',
  },
  'busan': {
    'x': 770,
    'y': 1145,
    'korean': '부산',
  },
  'gwangju': {
    'x': 304,
    'y': 1154,
    'korean': '광주',
  },
}


# CONTENTS
def getVideoContent():
  print('Generating Content and Script')

  for i in range(0, 30):
    try: 
      contentRequestList = [{
        'role': 'user',
        'content': """
          [step 1]
          1. 주어진 링크를 통해서 날씨 데이터를 가져와줘.
            최저, 최고기온은 'Forecast' 항목이고, 강수확률은 'Probability of Precipitation' 항목이야.
            seoul: https://www.timeanddate.com/weather/south-korea/seoul
            incheon: https://www.timeanddate.com/weather/south-korea/incheon
            daegu: https://www.timeanddate.com/weather/south-korea/daegu
            daejun: https://www.timeanddate.com/weather/south-korea/daejeon
            gwangju: https://www.timeanddate.com/weather/south-korea/gwangju
            busan: https://www.timeanddate.com/weather/south-korea/busan
          2. 가져온 자료를 기반으로만 오늘 한국 광역시들의 날씨와 그 데이터를 기반으로 노래 가사를 만들어줘
          3. 최저, 최고 기온과 강수확률, 날씨를 검색해야해
          4. 날씨는 sunny, snowy, rainy, cloudy 중에서만 부탁해

          [step 2]
          1. 가사는 1분 미만의 길이로 부탁하고 날씨 관련 정보는 앞쪽으로 오며 뒤쪽에는 하이라이트가 나오게 해줘.
          2. 가사에 기온은 포함하지말고 날씨 정보만 부탁해, 예를 들어 서울은 맑지만 비가올수있어 같이.

          [Output example]
          '{"weather":{"seoul":{"weather":"cloudy","lowTemperature":25,"highTemperature":31,"precipitationProbability":45},"daejeon":{"weather":"sunny","lowTemperature":25,"highTemperature":31,"precipitationProbability":20},"daegu":{"weather":"rainy","lowTemperature":25,"highTemperature":31,"precipitationProbability":90},"busan":{"weather":"cloudy","lowTemperature":27,"highTemperature":33,"precipitationProbability":50},"incheon":{"weather":"cloudy","lowTemperature":25,"highTemperature":31,"precipitationProbability":45},"gwangju":{"weather":"cloudy","lowTemperature":25,"highTemperature":31,"precipitationProbability":45}},"lyrics":"1분 미만 가사"}'

          output example: 
          잡설없이 데이터만 보내줘 데이터는 항상 코드블럭이 없는 순수한 stringify된 JSON 이여야해.
          """,
      }]
      contentRes = openai.ChatCompletion.create(
          model='gpt-4o',
          messages=contentRequestList
      )

      contentResponse = contentRes.choices[0].message.content

      content = json.loads(contentResponse)

      print(content)

      return content
    except:
      print('JSON parse exception, Re running..')

  raise Exception('ChatGPT something has wrong')

# Generate Suno AI music
def GenerateMusicFile(content):
  print('Generating Music')

  sunoCookie = os.getenv('SUNO_COOKIE')
  sunoClient = suno.Suno(cookie=sunoCookie)

  lyric = content['lyrics']
  print(lyric)

  clips = sunoClient.songs.generate(
    lyric,
    custom=True,
    tags='less-than-1min, Kpop, Fast Tempo, aggressive',
    instrumental=False,
  )

  suno.download(clips[1].id, './temp/audio/')

  return clips[1].id


def generateShortsVideo(content, musicId):
  print('Generating video...')

  # Narration audio clip
  print('Get audio sources')
  musicAudioClip = AudioFileClip('temp/audio/.suno/suno-{}.mp3'.format(musicId))
  totalDuration = musicAudioClip.duration
  if (totalDuration > 60): totalDuration = 59.5

  print('totalDuration', totalDuration)

  # Make Background Image
  print('Get background image source')
  backgourndImage = glob('assets/map.png')
  backgroundImageClip = ImageClip(backgourndImage[0]).set_duration(totalDuration)

  # Make Weather Icons
  print('Get content image sources')
  iconImageClipList = []
  font = ImageFont.truetype(font='./assets/font.ttf', size=30)
  rainyFont = ImageFont.truetype(font='./assets/font.ttf', size=17)
  for region in regionDatas:
    # Merge icon images
    iconFrame = Image.open('assets/icons/icon_frame.png')
    w, h = iconFrame.size
    mergedIcon = Image.new('RGBA', (w, h), color=(0,0,0,0))

    weatherIcon = Image.open('./assets/icons/{}.png'.format(content['weather'][region]['weather']))
    rainyIcon = Image.open('./assets/icons/rainy.png').resize((50, 50))

    mergedIcon.paste(iconFrame, (0, 0), iconFrame)
    mergedIcon.paste(weatherIcon, (5, math.floor(h / 4.5)), weatherIcon)

    # Draw region and temperature
    draw = ImageDraw.Draw(mergedIcon)
    draw.text(xy=(40, math.floor(h / 10)), text=regionDatas[region]['korean'], fill=(255, 255, 255), font=font)
    draw.text(xy=(22, math.floor(h / 1.25)),
              text=str(f'{content['weather'][region]['lowTemperature']} / {content['weather'][region]['highTemperature']}'),
              fill=(255, 255, 255), font=font)
    
    # Draw precipitation probability
    mergedIcon.paste(rainyIcon, (90, 0), rainyIcon)
    draw.text(xy=(98, 10),
              text=str(f'{content['weather'][region]['precipitationProbability']}%'),
              fill=(0, 120, 255), font=rainyFont)

    mergedIcon.save(f'./temp/image/{region}.png')

    # Make Icon Clip
    regionX = regionDatas[region]['x']
    regionY = regionDatas[region]['y']
    iconImageClip = ImageClip(numpy.array(mergedIcon)).set_position((regionX, regionY)).set_duration(totalDuration)
    iconImageClipList.append(iconImageClip)


  # Make Subtitle Text Clip
  print('Make subtitle text clip')
  now = dt.datetime.now()
  todaySubtitle = f'대한민국 {now.month}월 {now.day}일'.encode('utf8')
  textClip = TextClip(todaySubtitle, color='white', font='assets/font.ttf', fontsize=54)
  textClip = textClip.set_duration(totalDuration).set_position((575, 80))

  # Combine Clips
  print('Combine clips')
  result = CompositeVideoClip([backgroundImageClip, textClip] + iconImageClipList)
  result = result.set_audio(musicAudioClip).set_duration(totalDuration).audio_fadeout(5)

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

  # get music mp3 file
  musicId = GenerateMusicFile(content)

  # make video file
  generateShortsVideo(content, musicId)

  print('==DONE==')


# RUN
run()