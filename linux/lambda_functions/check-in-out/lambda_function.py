# -*- coding: utf-8 -*- 
import pymysql
import json
import boto3
from datetime import datetime, timedelta
import urllib
import sys
import os

def lambda_handler(event, context):
    #rekongnition용 변수지정
    REKOGNITION = boto3.client('rekognition')
    COLLECTION_ID = # Rekognition Collection ID 입력
    THRESHOLD = 90
    IMAGE_BUCKET = # 이미지를 저장할 S3 Bucket name 입력
    TRANSCRIBE = boto3.client('transcribe')

    #mariadb용 변수지정
    ENDPOINT = # RDBMS 엔드포인트 입력
    PORT = 3306 # RDBMS가 3306외 다른 포트번호를 사용할 시 변경할 것
    USR = # RDBMS Username 입력
    DBNAME = # DB 이름 입력
    DBPASS = # DB 패스워드 입력

    # Lambda TZ가 UTC이므로, KST에 해당하는 UTC+9로 맞춰주기
    KST_TIME = datetime.now() + timedelta(hours=9)
    # 시스템타임 형식 지정
    SYSTEM_TIME = datetime.strftime(KST_TIME, "%Y-%m-%d %H:%M:%S")
    # 텍스트를 저장할 S3버켓 정보
    S3 = boto3.client("s3")
    BUCKET_NAME = "cccr-message"
    #기능구분용 변수들
    INDEX = "IN"
    CHECK_IN = "CI"
    CHECK_OUT = "CO"
    
    IMAGE_OBJECT_KEY = event['Records'][0]['s3']['object']['key']

    if IMAGE_OBJECT_KEY[:2] == INDEX:
        CONN = pymysql.connect(host = ENDPOINT, user=USR, passwd=DBPASS, port=PORT, database=DBNAME)
        # 얼굴 인덱싱
        SEARCHING = REKOGNITION.search_faces_by_image(CollectionId=COLLECTION_ID,
                                    Image={'S3Object':{'Bucket':IMAGE_BUCKET,'Name':IMAGE_OBJECT_KEY}},
                                    FaceMatchThreshold=THRESHOLD,
                                    MaxFaces=1)
        if SEARCHING['FaceMatches'] != []:
            RESULTS = "등록기록이 존재하는 학생입니다."
            MESSAGE = {
                "Text": RESULTS
            }
            # 인덱싱 결과를 JSON으로 기록 후 s3 업로드
            JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
            with open(JSON_PATH, "w") as jsonfile:
                json.dump(MESSAGE, jsonfile, ensure_ascii = False )
            S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:]) 
            print(RESULTS)
            sys.exit()          

        INDEXING = REKOGNITION.index_faces(CollectionId=COLLECTION_ID,
                                    Image={'S3Object':{'Bucket':IMAGE_BUCKET,'Name':IMAGE_OBJECT_KEY}},
                                    MaxFaces=1,
                                    QualityFilter="AUTO",
                                    DetectionAttributes=['ALL'])
        for FACERECORD in INDEXING['FaceRecords']:
            FACEID = FACERECORD['Face']['FaceId']
        print('Indexed FaceID : ' + FACEID)

        job_name = IMAGE_OBJECT_KEY[3:-7]
        text= TRANSCRIBE.get_transcription_job(TranscriptionJobName=job_name)
        open_json = urllib.request.urlopen(text['TranscriptionJob']['Transcript']['TranscriptFileUri'])
        data = json.loads(open_json.read())
        text = data['results']['transcripts'][0]['transcript']
        print(text)

        #SQL INSERT 진행
        index_cur = CONN.cursor()
        CONN.ping(reconnect=True)
        print('학생정보 DB Insert 시작')
        add_student = ("INSERT INTO student "
                       "(Name, FaceID, Class) "
                       "VALUES (%(Name)s,%(FaceID)s,%(Class)s)")

        CLASS = text[3:5]
        STUDENT_NAME = text[6:]

        data_student = {
            "FaceID": FACEID,
            "Name": STUDENT_NAME,
            "Class": CLASS
        }

        index_cur.execute(add_student, data_student)
        CONN.commit()

        # 인덱싱 결과를 JSON으로 기록 후 s3 업로드
        RESULTS = "%s 님의 학생정보 등록이 완료되었습니다." % STUDENT_NAME
        MESSAGE = {
            "Text": RESULTS
        }
        JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
        with open(JSON_PATH, "w") as jsonfile:
            json.dump(MESSAGE, jsonfile, ensure_ascii = False )
        S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:]) 
        print(RESULTS)
        CONN.close()
    elif IMAGE_OBJECT_KEY[:2] == CHECK_IN:
        CONN = pymysql.connect(host = ENDPOINT, user=USR, passwd=DBPASS, port=PORT, database=DBNAME)
        SEARCHING = REKOGNITION.search_faces_by_image(CollectionId=COLLECTION_ID,
                                    Image={'S3Object':{'Bucket':IMAGE_BUCKET,'Name':IMAGE_OBJECT_KEY}},
                                    FaceMatchThreshold=THRESHOLD,
                                    MaxFaces=1)
        if SEARCHING['FaceMatches'] == []:
            print('등록되지 않은 사용자입니다.')
            sys.exit()                                 
        print ('Matching faces')
        for match in SEARCHING['FaceMatches']:
            face_id = match['Face']['FaceId']
            print ('당신의 FaceId: %s' % face_id)
            print ('원본 사진과 유사도: ' + "{:.2f}".format(match['Similarity']) + "%")

        # SQL SELECT(DB에서 해당하는 학생정보 변수처리)
        ci_cur = CONN.cursor()
        CONN.ping(reconnect=True)
        select_student = ("SELECT id,Name,Class from student where FaceID='%s'" % face_id) 
        ci_cur.execute(select_student)
        student_table = ci_cur.fetchall()     
        for student_data in student_table:
            Student_Id = student_data[0]
            Student_Name = student_data[1]
            Student_Class = student_data[2]
            print("학생명은 " + Student_Name)

        # 오늘 출석기록이 이미 존재하는가 확인
        select_check_in = ("SELECT * FROM check_in_out WHERE studentID=%s " 
                     "AND check_in_time LIKE '%s%%'" %(Student_Id, SYSTEM_TIME[:10]))
        check_in_result = ci_cur.execute(select_check_in)
        # 출석기록 없을 떄 insert 처리
        if check_in_result == 0:
            add_check = ("INSERT INTO check_in_out  "
                           "(check_in_time, studentID) "
                           "VALUES ('%s', '%s')" %(SYSTEM_TIME, Student_Id))
            ci_cur.execute(add_check)
            CONN.commit()

            RESULTS = "%s 님, 출석 완료되었습니다." % Student_Name
            MESSAGE = {
                "Text": RESULTS
            }
            JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
            with open(JSON_PATH, "w") as jsonfile:
                json.dump(MESSAGE, jsonfile, ensure_ascii = False )
            S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:])             
            print(RESULTS)
        else:
            RESULTS = "출석기록이 이미 존재합니다."
            MESSAGE = {
                "Text": RESULTS
            }
            # 인덱싱 결과를 JSON으로 기록 후 s3 업로드
            JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
            with open(JSON_PATH, "w") as jsonfile:
                json.dump(MESSAGE, jsonfile, ensure_ascii = False )
            S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:])             
            print(RESULTS)
        CONN.close()

    elif IMAGE_OBJECT_KEY[:2] == CHECK_OUT:
        CONN = pymysql.connect(host = ENDPOINT, user=USR, passwd=DBPASS, port=PORT, database=DBNAME)
        SEARCHING = REKOGNITION.search_faces_by_image(CollectionId=COLLECTION_ID,
                                    Image={'S3Object':{'Bucket':IMAGE_BUCKET,'Name':IMAGE_OBJECT_KEY}},
                                    FaceMatchThreshold=THRESHOLD,
                                    MaxFaces=1)
        if SEARCHING['FaceMatches'] == []:
            print('등록되지 않은 사용자입니다.')
            sys.exit()                            
        print ('Matching faces')
        for match in SEARCHING['FaceMatches']:
                face_id = match['Face']['FaceId']
                print ('당신의 FaceId: %s' % face_id)
                print ('원본 사진과 유사도: ' + "{:.2f}".format(match['Similarity']) + "%")

        # SQL SELECT(DB에서 해당하는 학생정보 변수처리)
        co_cur = CONN.cursor()
        CONN.ping(reconnect=True)
        select_student = ("SELECT id,Name,Class from student where FaceID='%s'" % face_id) 
        co_cur.execute(select_student)
        student_table = co_cur.fetchall()     
        for student_data in student_table:
            Student_Id = student_data[0]
            Student_Name = student_data[1]
            Student_Class = student_data[2]
            print("학생명은 " + Student_Name)

        # 오늘 출석기록이 이미 존재하는가 확인
        select_check_in = ("SELECT * FROM check_in_out WHERE studentID='%s' "
                     "AND check_in_time LIKE '%s%%'" % (Student_Id, SYSTEM_TIME[:10]))
        check_in_result = co_cur.execute(select_check_in)
        # 출석기록이 없는 경우
        if check_in_result == 0:
            RESULTS = "출석기록이 존재하지 않습니다. 출석 먼저 진행해주세요."
            MESSAGE = {
                "Text": RESULTS
            }
            # 인덱싱 결과를 JSON으로 기록 후 s3 업로드
            JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
            with open(JSON_PATH, "w") as jsonfile:
                json.dump(MESSAGE, jsonfile, ensure_ascii = False )
            S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:])             
            print(RESULTS)

        # 출석기록이 존재하는 경우
        else:
            select_check_out = ("SELECT id FROM check_in_out WHERE studentID='%s' "
                                "AND check_in_time LIKE '%s%%'"
                                "AND check_out_time IS NULL" % (Student_Id, SYSTEM_TIME[:10]))
            check_out_result = co_cur.execute(select_check_out)
            # 출퇴기록이 존재하는 경우
            if check_out_result == 0:
                RESULTS = "퇴실기록이 이미 존재합니다."
                MESSAGE = {
                    "Text": RESULTS
                }
                # 인덱싱 결과를 JSON으로 기록 후 s3 업로드
                JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
                with open(JSON_PATH, "w") as jsonfile:
                    json.dump(MESSAGE, jsonfile, ensure_ascii = False )
                S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:])                 
                print(RESULTS)

            # 출석기록 존재하나, 퇴실기록 없는 경우
            else:
                select_id = co_cur.fetchall()
                Check_Id = select_id[-1][0]
                update_check = ("UPDATE check_in_out "
                                "SET check_out_time = '%s',"
                                "WHERE id = '%d'" % (SYSTEM_TIME, Check_Id))
                co_cur.execute(update_check)
                CONN.commit()

                print("퇴실기록 등록이 완료되었습니다.")
                RESULTS = "%s 님, 퇴실 완료되었습니다." % Student_Name
                MESSAGE = {
                    "Text": RESULTS
                }
                JSON_PATH = "/tmp/%s.json" % IMAGE_OBJECT_KEY
                with open(JSON_PATH, "w") as jsonfile:
                    json.dump(MESSAGE, jsonfile, ensure_ascii = False )
                S3.upload_file(JSON_PATH, BUCKET_NAME, JSON_PATH[5:])                 
                print(RESULTS)
        CONN.close()
