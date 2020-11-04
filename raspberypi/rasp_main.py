import time
import os
import cv2
import rasp_function
import Seeed_AMG8833
from thermal_cam import thermal_cam
from threading import Thread

#S3 버켓 변수리스트
wav_bucket = "transcriberecord"
image_bucket = "cccr-image"
text_bucket = "cccr-message"

#cv2 변수리스트
cap = cv2.VideoCapture(0)

# Cascades 디렉토리의 haarcascade_frontalface_default.xml 파일을 Classifier로 사용
faceCascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eyeCascade = cv2.CascadeClassifier('haarcascade_eye.xml')

# 등록/출석/퇴실 여부
status = None

##기능구분을 위한 변수리스트
등록 = "등"
출석 = "출"
퇴실 = "퇴"

#온도센서 기능 호출을 위한 변수
sensor = Seeed_AMG8833.AMG8833

#cv2 스트리밍 함수
def streaming():
    time.sleep(2)
    while True:
        success, frame = cap.read()
        ''' 
        cascade에서는 얼굴을 찾기 위해 원본 이미지를 꼭 gray색상으로 변환해야 한다고 한다.
        cv2의 cvtColor모듈을 사용하여 프레임을 gray로 변환한 변수를 지정한다.
        '''
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #gray변수에서 얼굴 데이터를 추출
        faces = faceCascade.detectMultiScale(
            gray,
            scaleFactor = 1.2,
            minNeighbors = 5,
            minSize=(20, 20)
        )
        for (x,y,w,h) in faces:
            # 추출된 데이터에서 Topleft, Bottomright 값을 받아서 사각형을 그리기
            cv2.rectangle(frame,(x,y),(x+w,y+h),(255,0,0),2)
            # 얼굴에 그려진 사각형 안쪽의 범위를 지정
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            # 얼굴에 그려진 사각형 안쪽 범위에서 눈 데이터를 추출
            eyes = eyeCascade.detectMultiScale(roi_color)
            # 추출된 데이터에서 Topleft, Bottomright 값을 받아서 사각형 그리기
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh),
                (0,255,0), 2)
        if success:
            cv2.imshow("Help_Me_Hongs", frame)
            key = cv2.waitKey(1) 
            if key == ord("q"):
                cv2.destroyAllWindows
                break

#cv2 캡쳐 함수
def capture(status, filename):
    sucess, frame = cap.read()
    cv2.imwrite("/tmp/%s-%s.jpg" % (status, filename), frame)

#메인함수
def main_function():
    # 여러 용도로 사용할 시스템타임의 변수 (형식: 년-월-일-시-분-초)
    System_Time = time.strftime("%Y-%m-%d-%H-%M-%S")
    WAVE_OUTPUT_FILENAME = System_Time + ".wav"

    rasp_function.speech("원하는 기능을 말씀해주세요. 5초 동안 녹음이 시작됩니다.") 
    os.system('play -nq -t alsa synth {} sine {}'.format(0.5, 440))

    rasp_function.recording(WAVE_OUTPUT_FILENAME)

    #생성한 wav파일을 S3로 업로드 및 wav파일 삭제
    rasp_function.S3("/tmp/%s" % WAVE_OUTPUT_FILENAME, wav_bucket, WAVE_OUTPUT_FILENAME)
    time.sleep(2)
    os.remove("/tmp/%s" % WAVE_OUTPUT_FILENAME)

    rasp_function.speech("녹음이 종료되었습니다. 음성인식이 완료될 떄 까지 잠시만 기다려주세요.") 

    #transcribejob 생성될 때 까지 대기 후 텍스트 받아오기    
    text = rasp_function.transcribe(WAVE_OUTPUT_FILENAME)
    print("Transcribe 결과 " + "\"" + text + "\"")

    #transcribe 결과에 따른 별도절차 진행
    if text[0:1] == 등록:
        status = "IN"
        rasp_function.speech("등록절차를 진행합니다. 카메라 위치에 얼굴을 맞춰주세요.")
        time.sleep(2)
        print("사진촬영을 시작합니다.")
        capture(status,WAVE_OUTPUT_FILENAME)

        # 이미지를 s3에 업로드
        IMAGE_OUTPUT_FILENAME = "%s-%s.jpg" % (status, WAVE_OUTPUT_FILENAME)
        
        print(IMAGE_OUTPUT_FILENAME)
        rasp_function.S3("/tmp/%s" % IMAGE_OUTPUT_FILENAME, image_bucket, IMAGE_OUTPUT_FILENAME)
        time.sleep(5)

        rasp_function.speech(rasp_function.read_text(text_bucket, IMAGE_OUTPUT_FILENAME))
    elif text[0:1] == 출석:
        status = "CI" 
        rasp_function.speech("출석절차를 진행합니다. 카메라 위치에 얼굴을 맞춰주세요.")
        time.sleep(2)
        print("사진촬영을 시작합니다.")
        capture(status,WAVE_OUTPUT_FILENAME)

        IMAGE_OUTPUT_FILENAME = "%s-%s.jpg" % (status, WAVE_OUTPUT_FILENAME)
        temp = format(sensor.cal_temp(), ".2f")

        # 온도값을 S3에 업로드
        rasp_function.write_text(text_bucket, IMAGE_OUTPUT_FILENAME, temp)

        print(IMAGE_OUTPUT_FILENAME)
        rasp_function.S3("/tmp/%s" % IMAGE_OUTPUT_FILENAME, image_bucket, IMAGE_OUTPUT_FILENAME)
        time.sleep(5)

        rasp_function.speech(rasp_function.read_text(text_bucket, IMAGE_OUTPUT_FILENAME))

    elif text[0:1] == 퇴실:
        status = "CO" 
        time.sleep(2)
        rasp_function.speech("퇴실절차를 진행합니다. 카메라 위치에 얼굴을 맞춰주세요.")
        print("사진촬영을 시작합니다.")
        capture(status,WAVE_OUTPUT_FILENAME)

        IMAGE_OUTPUT_FILENAME = "%s-%s.jpg" % (status, WAVE_OUTPUT_FILENAME)
        temp = format(sensor.cal_temp(), ".2f")
        # 온도값을 S3에 업로드
        rasp_function.write_text(text_bucket, IMAGE_OUTPUT_FILENAME, temp)
        
        print(IMAGE_OUTPUT_FILENAME)
        rasp_function.S3("/tmp/%s" % IMAGE_OUTPUT_FILENAME, image_bucket, IMAGE_OUTPUT_FILENAME)
        time.sleep(5)

        rasp_function.speech(rasp_function.read_text(text_bucket, IMAGE_OUTPUT_FILENAME))
    else:
        rasp_function.speech("음성을 인식하지 못했습니다. 다시 한번 시도해주세요.")

def judge():
    while True:
        success, img = cap.read()
        if success:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor = 1.2,
                minNeighbors = 5,
                minSize=(20, 20)
            )
            for (x,y,w,h) in faces:
                if 250 < w and 250 < h:
                    print("인식 성공")
                    main_function()

if __name__ == "__main__":
    t1 = Thread(target=streaming)
    t2 = Thread(target=thermal_cam)
    t3 = Thread(target=judge)
    t1.start()
    t2.start()
    t3.start()
