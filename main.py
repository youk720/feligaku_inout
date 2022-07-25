from itertools import count
import nfc
import time
import requests
import RPi.GPIO as GPIO


# IFTTTのキー指定
key = ''
ifttt_project = ''
service_code = 0x200b #システムコード初期状態(FE00)時:0x1a8b
gakuban = ""

# gpioピン指定
led_r = 16
led_g = 20
led_b = 21
atuden = 26
atuden_hz = 800
gaku_error = 0
# 各種GPIOセット
GPIO.setmode(GPIO.BCM)
GPIO.setup(led_b, GPIO.OUT)
GPIO.setup(led_g, GPIO.OUT)
GPIO.setup(led_r, GPIO.OUT)
GPIO.setup(atuden, GPIO.OUT)
GPIO.output(led_b, 0)
GPIO.output(led_g, 0)
GPIO.output(led_r, 0)
atsu_DEN = GPIO.PWM(atuden, 1)
# atsu_DEN.start(1)

# 学生, 学番, 入退ステータス

gakulist_1 = [["name", "gakuban", 0], ["name", "gakuban", 0], ["name", "gakuban", 0]]

def send_ifttt(gakuban, name, mode, count):
  # 送信文字列 生成
  payload = {"value1":gakuban+"/"+name, "value2":mode, "value3":count}
  # url生成
  url = "https://maker.ifttt.com/trigger/"+ ifttt_project +"/with/key/"+key
  # IFTTTへ送信!
  requests.post(url, json=payload)

def connected(tag):
  # 内容を16進数で出力する
  # print("dump felica.")
  # print('  ' + '\n  '.join(tag.dump()))
  #システムコード指定
  idm, pmm = tag.polling(system_code=0x809E)
  tag.idm, tag.pmm, tag.sys = idm, pmm, 0x809E
  global gakuban, gaku_error

  if isinstance(tag, nfc.tag.tt3.Type3Tag):
    try:
      # 学籍番号出力
      sc = nfc.tag.tt3.ServiceCode(service_code >> 6, service_code & 0x3f)
      bc = nfc.tag.tt3.BlockCode(0,service=0)
      feli_data = tag.read_without_encryption([sc],[bc]) #学番出力
      print(feli_data[0:8])
      gakuban = feli_data[0:8].decode()
      gaku_error = 1 #エラー処理用フラグ
      # print("gakuban:" + gakuban)
    except Exception as e:
      felica_error()
      print("error: %s" % e)
  else:
    felica_error()
    print("error: tag isn't Type3Tag")

# 入室者数カウント
def memb_count():
  count_d = 0
  for x in range(len(gakulist_1)):
    if gakulist_1[x][2] == 1:
      count_d = count_d + 1
  return count_d

# 入室処理
def in_room(gakuban):
  print(gakulist_1[gakuban][1]+ "/" + gakulist_1[gakuban][0] + " here.")
  # 入退フラグ
  gakulist_1[gakuban][2] = 1
  # sp/LED動作
  atsu_DEN.start(0.5)
  atsu_DEN.ChangeFrequency(500)
  GPIO.output(led_g, 1)
  print("led&atdn: on")
  # IFTTT発信
  send_ifttt(gakulist_1[gakuban][1], gakulist_1[gakuban][0], "in", memb_count())
  # time.sleep(0.5) #sp 0.5鳴らし
  atsu_DEN.stop()
  time.sleep(2.5) # LED 0.5 + 2.5 = 3.0sec光らせ
  GPIO.output(led_g, 0)
  print("led&atdn: off")

# 退室処理
def out_room(gakuban):
  print(gakulist_1[gakuban][1]+ "/" + gakulist_1[gakuban][0] + " out.")
  # 入退フラグ
  gakulist_1[gakuban][2] = 0
  # sp/LED動作
  atsu_DEN.start(0.5)
  atsu_DEN.ChangeFrequency(1000)
  print("led&atdn: on")
  GPIO.output(led_b, 1)
  # IFTTT発信
  send_ifttt(gakulist_1[gakuban][1], gakulist_1[gakuban][0], "out", memb_count())
  # time.sleep(0.5)
  atsu_DEN.stop()
  time.sleep(2.5)
  GPIO.output(led_b, 0)
  print("led&atdn: off")

def felica_error():
  # global gaku_error
  # sp/LED動作
  atsu_DEN.start(3)
  atsu_DEN.ChangeFrequency(1500)
  GPIO.output(led_r, 1)
  time.sleep(3)
  atsu_DEN.stop()
  GPIO.output(led_r, 0)
  # gaku_error = 0


with nfc.ContactlessFrontend('usb') as m:
  while True:
    try: 
      tag = m.connect(rdwr={'on-connect': connected})
      # 対象者の名前と学版出力
      for x in range(len(gakulist_1)):

        # 特定の人がタッチ
        if gakuban == gakulist_1[x][1]:
          # 学生証タッチエラーフラグ解除
          gaku_error = 0
          # 入室対応
          if gakulist_1[x][2] == 0:
            in_room(x)
          # 退室対応
          else:
            out_room(x)
          # 終了
          break
        # 特定外のタッチ
        elif x == 5 and gaku_error == 1:
          gaku_error = 0
          print("another gakusyo")
          felica_error()
          
      print("main gakunow: "+ gakuban + "gakuer:"+str(gaku_error))
      time.sleep(1)
    except KeyboardInterrupt: #ctrl + Cでプログラム止める
      m.close()
      print("shutdown program.")
      break
    # time.sleep(1)pass
  
atsu_DEN.stop()
GPIO.cleanup()
