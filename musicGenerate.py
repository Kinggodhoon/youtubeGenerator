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

  contentRequestList = [{
    'role': 'user',
    'content': "오늘 한국 광역시들의 날씨 찾아서 노래 가사로 만들어줘.\n 가사는 1분 미만의 Verse1-hook1으로 부탁하고 날씨 관련 정보는 모두 Verse1에 넣어줘.\n 가사중 기온은 한자 음 표기로 표기해줘 예를들어 25라면 이십오도 처럼.\n 날씨는 sunny, snowy, rainy, cloudy 중에서만 부탁해.\n output example: \"{\"weather\":{\"seoul\":{\"weather\":\"cloudy\",\"temperature\":25},\"daejeon\":{\"weather\":\"sunny\",\"temperature\":25},\"daegu\":{\"weather\":\"rainy\",\"temperature\":25},\"busan\":{\"weather\":\"cloudy\",\"temperature\":25},\"incheon\":{\"weather\":\"cloudy\",\"temperature\":25},\"gwangju\":{\"weather\":\"cloudy\",\"temperature\":25}},\"lyrics\":\"가사 가사\"}\" \n 결과를 보내기 전에 기온과 데이터 형식이 확실한지 확인해줘 데이터는 항상 stringify된 JSON 이여야해.",
  }]
  contentRes = openai.ChatCompletion.create(
      model='gpt-4o',
      messages=contentRequestList
  )

  contentResponse = contentRes.choices[0].message.content

  print(contentResponse)
  content = json.loads(contentResponse)

  return content

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
  for region in regionDatas:
    # Merge icon images
    iconFrame = Image.open('assets/icons/icon_frame.png')
    w, h = iconFrame.size
    mergedIcon = Image.new('RGBA', (w, h), color=(0,0,0,0))

    weatherIcon = Image.open('./assets/icons/{}.png'.format(content['weather'][region]['weather']))

    mergedIcon.paste(iconFrame, (0, 0), iconFrame)
    mergedIcon.paste(weatherIcon, (5, math.floor(h / 4.5)), weatherIcon)

    # Draw region and temperature
    draw = ImageDraw.Draw(mergedIcon)
    draw.text(xy=(40, math.floor(h / 10)), text=regionDatas[region]['korean'], fill=(255, 255, 255), font=font)
    draw.text(xy=(50, math.floor(h / 1.25)), text=str(content['weather'][region]['temperature']), fill=(255, 255, 255), font=font)

    # Make Icon Clip
    regionX = regionDatas[region]['x']
    regionY = regionDatas[region]['y']
    iconImageClip = ImageClip(numpy.array(mergedIcon)).set_position((regionX, regionY)).set_duration(totalDuration)
    iconImageClipList.append(iconImageClip)

  # Make Subtitle Text Clip
  print('Make subtitle text clip')
  now = dt.datetime.now()
  textClip = TextClip(f'대한민국 {now.month}월 {now.day}일', color='white', font='assets/font.ttf', fontsize=54)
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