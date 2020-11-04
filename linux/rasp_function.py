import boto3
import pyaudio
import wave
import time
import json
import os
import sys
import subprocess
import urllib
from botocore.exceptions import BotoCoreError, ClientError
from tempfile import gettempdir
from contextlib import closing

def speech(pollytext):
    os.environ['SDL_AUDIODRIVER'] = 'alsa'
    polly = boto3.client("polly")
    try:
        response = polly.synthesize_speech(Text=pollytext, OutputFormat="mp3", VoiceId="Seoyeon")
    except (BotoCoreError, ClientError) as error:
       print(error)
       sys.exit(-1)
    if "AudioStream" in response:
        with closing(response["AudioStream"]) as stream:
            #mp3 파일 저장위치 지정
            output = os.path.join(gettempdir(), "speech.mp3")
            try:
                with open(output, "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                print(error)
                sys.exit(-1)
    else:
        print("응답에 오디오 데이터가 포함되지않아 오디오를 스트리밍 할 수 없습니다.")
        sys.exit(-1)
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    os.system("mplayer '/tmp/speech.mp3'")

def recording(wave_output_filename):
    #녹음에 필요한 변수들
    CHUNK = 48000
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5

    #pyaudio 라이브러리로 녹음데이터를 frames에 떄려박는 함수들
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    frames = []
    
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

    #저장된 프레임을 기반으로 wav파일 생성
    wf = wave.open("/tmp/%s" % wave_output_filename, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def S3(file_direction, bucket_name, file_name):
    S3 = boto3.client("s3")
    S3.upload_file(file_direction, bucket_name, file_name)
    return print("S3 업로드 완료")

def transcribe(job_name):
    transcribe = boto3.client('transcribe')
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("STT 진행 중... 끄지 마숑..")
        time.sleep(5)
    open_json = urllib.request.urlopen(status['TranscriptionJob']['Transcript']['TranscriptFileUri'])
    data = json.loads(open_json.read())
    text = data['results']['transcripts'][0]['transcript']
    return text

def read_text(bucket_name, file_name):
    S3 = boto3.client("s3")
    json_data = S3.get_object(Bucket=bucket_name, Key="%s.json" % file_name)
    json_text = json.loads(json_data['Body'].read())
    result = json_text["Text"]
    return result

def write_text(bucket_name, file_name, text):
    message = {
        "Temp": text
    }
    json_name = "TEMP-%s.json" % file_name    
    json_path = "/tmp/%s" % json_name
    with open(json_path, "w") as jsonfile:
        json.dump(message, jsonfile, ensure_ascii = False)
    S3(json_path, bucket_name, json_name)
    time.sleep(2)
