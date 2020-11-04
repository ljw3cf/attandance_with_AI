# AWS AI 서비스를 활용한 출결관리 서비스

## Introduction
AWS의 AI 서비스들을 활용한 얼굴인식 기반 출결관리 서비스 입니다.  
RaspberryPi 혹은 Linux 시스템에서 음성, 이미지, 체온정보를 입력받고 수강생 등록/출석/퇴실 절차를 진행할 수 있습니다.  
>본 서비스는 기본적으로 음성, 이미지로 일련의 절차를 진행합니다.  
체온정보 처리를 위해선 온도센서가 포함된 RaspberyPi가 필요합니다.  
하드웨어에 대한 세부정보는 Getting Started 항목의 Prerequisites에서 확인하실 수 있습니다.

## Getting Started
### Prerequisites

Linux 환경에서 출결관리를 위한 환경은 다음과 같습니다.
* HW 
    + 웹캠 / 마이크가 연결된 Laptop 혹은 Desktop   
* SW
    + Devian 혹은 Redhat계열 Linux
    + Python3
    + OpenCV
    + pyaudio
    + boto3 
    + AWS CLI 및 AWS Credential
    + mplayer

RaspberryPi 환경에서 온도측정 및 출결관리를 위한 환경은 다음과 같습니다.
* HW 
    + RaspberryPi4 +
    + RaspberryPi Camera board v2
    + AMG8833 8x8 Infrared Thermal Temperature Sensor
    + Grove Base Hat for RaspberryPi
    + USB를 지원하는 마이크
    + AUX를 지원하는 스피커   
* SW
    + Devian 혹은 Redhat계열 Linux
    + Python3
    + OpenCV
    + pyaudio
    + boto3 
    + AWS CLI 및 AWS Credential
    + mplayer

### Requirements installation

1. AWS CLI을 설치합니다. 라즈베리파이의 경우 ARM 설치과정을 따릅니다.
<pre>
<code>
# Linux x86(64-bit) 설치과정
$ curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
$ unzip awscliv2.zip
$ sudo ./aws/install

# Linux ARM 설치과정
$ curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
$ unzip awscliv2.zip
$ sudo ./aws/install
</code>
</pre>

2. AWS 콘솔에서 IAM 서비스에 접속합니다. 좌측 엑세스 관리탭을 클릭하고 해당하는 사용자를 클릭합니다.

3. 보안 자격 증명 메뉴를 클릭하고 엑세스 키 항목에서 엑세스 키 만들기 버튼을 클릭합니다.

4. 해당 사용자의 Access Key와 Secret Access Key가 표시됩니다. 해당 부분을 메모하거나 csv형태로 저장합니다.

5. AWS 계정의 Credential을 시스템에 등록합니다.
<pre>
<code>
$ aws configure
AWS Access Key ID []: <메모한 Access_key 입력>
AWS Secret Access Key []: <메모한 Secret Access Key 입력>
Default region name []: <사용할 region>
Default output format []: # <엔터>

</code>
</pre>

6. Credential은 기본적으로 ~/. aws디렉토리에 config와 credentials 상태로 저장됩니다.
<pre>
<code>
$ ls ~/.aws
config  credentials
</code>
</pre>

7. boto3를 설치합니다.
<pre>
<code>
$ pip3 install boto3
</code>
</pre>

8. 기타 필요한 라이브러리를 설치합니다.
<pre>
<code>
# opencv 설치
$ apt install -y python3-opencv

# pyaudio 설치
$ apt install -y python3-pyaudio
</code>
</pre>

9. 음성을 재생시켜 줄 플레이어를 설치합니다.
<pre>
<code>
$ apt install -y mplayer
</code>
</pre>

10. 서비스를 위한 코드를 다운로드 합니다.
<pre>
<code>
$ git clone https://github.com/ljw3cf/attandance_with_AI.git
</code>
</pre>

## Service setup

**Database**  
서비스 구축에 앞서 수강생 정보 및 출결기록을 저장할 데이터베이스가 필요합니다.  
Mysql 혹은 MariaDB를 사용하여 데이터베이스를 구축할 필요가 있습니다. 서비스를 위해 구축해야 할 데이터베이스의 테이블명과 스키마는 다음과 같습니다.
<pre>
<code>
1. student(수강생 정보)
+--------+--------------+------+-----+---------+----------------+
| Field  | Type         | Null | Key | Default | Extra          |
+--------+--------------+------+-----+---------+----------------+
| ID     | int(20)      | NO   | PRI | NULL    | auto_increment |
| Name   | varchar(100) | YES  |     | NULL    |                |
| FaceID | varchar(100) | YES  |     | NULL    |                |
| Class  | varchar(100) | YES  |     | NULL    |                |
+--------+--------------+------+-----+---------+----------------+

2. Check_in_out(출결정보)
+----------------+--------------+------+-----+---------+----------------+
| Field          | Type         | Null | Key | Default | Extra          |
+----------------+--------------+------+-----+---------+----------------+
| ID             | int(20)      | NO   | PRI | NULL    | auto_increment |
| check_in_time  | datetime     | YES  |     | NULL    |                |
| check_in_temp  | decimal(4,2) | YES  |     | NULL    |                |
| check_out_time | datetime     | YES  |     | NULL    |                |
| check_out_temp | decimal(4,2) | YES  |     | NULL    |                |
| studentID      | int(11)      | NO   |     | NULL    |                |
+----------------+--------------+------+-----+---------+----------------+
</code>
</pre>

데이터베이스 구축을 마치고 Python 라이브러리를 이용하여 데이터베이스 접근하기 위해 다음과 같은 정보를 메모해둡니다.
<pre>
<code>
1. Database 엔드포인트(URL 혹은 IP Address)
2. Database Port번호
3. Database 유저 ID 및 PW
4. 생성한 Database 이름
</code>
</pre>

**Rekognition**  
AWS Rekognition 사용을 위해 Faceid 저장소인 Collection 생성이 필요합니다.  
AWS CLI를 통해 Collection을 생성합니다. 생성 시 지정한 collection id는 메모해둡니다.
<pre>
<code>
$ aws rekognition create-collection --collection-id <생성할 collection id>
</code>
</pre>

**S3**  
Lambda 트리깅과 TTS를 위해 사용할 S3 버켓을 생성합니다. 필요한 S3 버켓의 종류와 용도는 다음과 같습니다.

* sound-bucket: STT 사용을 위해 음성 파일을 저장합니다.
* image-bucket: Rekognition 사용을 위해 수강생 이미지를 저장합니다.
* message-bucket: TTS 기능을 위해 텍스트 파일을 저장합니다.

AWS CLI를 통해 S3 버켓을 생성하는 방법은 다음과 같습니다.  
생성할 버켓명은 고유해야 하며, 버켓은 기본적으로 AWS CLI Configure로 설정했던 리전에 생성됩니다.
<pre>
<code>
$ aws s3 mb s3://<생성할 버켓명>
</code>
</pre>

**Lambda**  
서비스에 필요한 Lambda function을 생성합니다. 필요한 Lambda function의 종류와 용도는 다음과 같습니다.
<pre>
<code>
STT: sound-bucket에 업로드된 음성을 transcribe를 이용하여 텍스트로 변환합니다.

Check-in-out: image-bucket에 업로드된 이미지를 rekognition을 이용하여 분석합니다.  그리고 필요한 정보를 Database에 입력하고 수강생에게 들려줄 메세지를 polly를 이용하여 TTS합니다.
</code>
</pre>

기능별 Lambda function을 생성하는 방법은 다음과 같습니다.  

* STT
1. AWS 콘솔에서 AWS Lambda를 선택합니다.
2. 좌측 메뉴에서 함수를 클릭하고 함수 생성버튼을 클릭합니다.
3. 새로 작성 탭을 클릭하고 함수 이름을 지정합니다. 런타임은 Python 3.8을 선택합니다. 
4. 권한 탭에서 "기본 Lambda 권한을 가진 새 역할 생성"을 선택합니다. 화면에 표기되는 IAM 역할 이름을 기록해둡니다.
5. 우측 하단의 "함수 생성" 버튼을 클릭합니다.
6. 생성된 IAM 역할에 더 많은 정책을 연결하기 위해 IAM 서비스에 접속합니다.
7. 좌측의 정책 탭을 클릭하고 Lambda와 연결된 역할을 클릭합니다.
8. 권한 탭에서 "인라인 정책 추가" 버튼을 클릭합니다.
9. JSON 탭을 클릭합니다. 그리고 하기의 JSON코드를 입력하고 "정책 검토" 버튼을 클릭합니다.
<pre>
<code>
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::*transcribe*"
            ]
        }
    ]
}
</code>
</pre>

10. 임의의 정책 이름을 입력하고 정책 생성버튼을 클릭합니다.
11. 다시 Lambda 서비스로 접속하여 생성된 Lambda function을 선택합니다.
12. 디자이너 항목에서 "트리거 추가" 버튼을 클릭합니다.
13. "트리거 선택"을 클릭하고 S3를 선택합니다.
14. 버킷 항목에서 이전에 생성한 **Voice 전용 버킷**을 선택합니다.
15. 다른 부분은 공란으로 둡니다.
16. 하단에 재귀 호출과 관련된 경고창이 존재하며, 해당 내용을 인지하고 있음을 체크합니다.
17. "추가" 버튼을 클릭합니다.
18. 트리거가 추가되면 function 화면으로 전환되며, 스크롤을 아래로 움직여 "function code" 항목으로 이동합니다.
19. 우측 상단의 "작업"버튼을 클릭하고 ".zip파일 업로드"를 선택합니다.
20. "업로드" 버튼을 클릭하고 .student_attandance/linux(혹은 raspberrypi)/lambda_functions/stt/lambda_function.zip 을 선택합니다. 그리고 "저장" 버튼을 클릭합니다.
21. 코드가 업데이트된 모습을 확인할 수 있습니다. 

* Check-in_out

1. AWS 콘솔에서 AWS Lambda를 선택합니다.
2. 좌측 메뉴에서 함수를 클릭하고 함수 생성버튼을 클릭합니다.
3. 새로 작성 탭을 클릭하고 함수 이름을 지정합니다. 런타임은 Python 3.8을 선택합니다. 
4. 권한 탭에서 "기본 Lambda 권한을 가진 새 역할 생성"을 선택합니다. 화면에 표기되는 IAM 역할 이름을 기록해둡니다.
5. 우측 하단의 "함수 생성" 버튼을 클릭합니다.
6. 생성된 IAM 역할에 더 많은 정책을 연결하기 위해 IAM 서비스에 접속합니다.
7. 좌측의 정책 탭을 클릭하고 Lambda와 연결된 역할을 클릭합니다.
8. 권한 탭에서 "인라인 정책 추가" 버튼을 클릭합니다.
9. JSON 탭을 클릭합니다. 그리고 하기의 JSON코드를 입력하고 "정책 검토" 버튼을 클릭합니다.
<pre>
<code>
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "rekognition:SearchFacesByImage",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::*transcribe*"
            ]
        }        
    ]
}
</code>
</pre>
10. 임의의 정책 이름을 입력하고 정책 생성버튼을 클릭합니다.

11. 다시 Lambda 서비스로 접속하여 생성된 Lambda function을 선택합니다.

12. 디자이너 항목에서 "트리거 추가" 버튼을 클릭합니다.

13. "트리거 선택"을 클릭하고 S3를 선택합니다.

14. 버킷 항목에서 이전에 생성한 **Image 전용 버킷**을 선택합니다.

15. 다른 부분은 공란으로 둡니다.

16. 하단에 재귀 호출과 관련된 경고창이 존재하며, 해당 내용을 인지하고 있음을 체크합니다.

17. "추가" 버튼을 클릭합니다.

18. 트리거가 추가되면 function 화면으로 전환되며, 스크롤을 아래로 움직여 "function code" 항목으로 이동합니다.

19. 우측 상단의 "작업"버튼을 클릭하고 ".zip파일 업로드"를 선택합니다.

20. 본인의 시스템 환경에 따라하기의 파일을 업로드합니다.  
<pre>
<code>
웹캠과 마이크가 구비된 Linux 시스템  
 student_attandance/linux/lambda_functions/check-in-out/lambda_function.zip  
카메라 모듈, 마이크, 온도센서가 구비된 RaspberryPi  
 student_attandance/raspberrypi/lambda_functions/check-in-out/lambda_function.zip
</code>
</pre>
21. "저장" 버튼을 클릭하면 코드가 업데이트된 모습을 확인할 수 있습니다. 

22. 업데이트된 코드에서 13번~23번 항목을 자신의 환경에 맞게 수정합니다.
<pre>
<code>
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
</code>
</pre>

23. 코드를 수정한 뒤 우측 상단의 "Deploy" 버튼을 클릭하여 배포합니다.

24. Lambda 서비스메뉴 좌측 "Additional resources" 항목의 "계층" 항목을 클릭합니다.

25. 현재 생성된 계층의 리스트가 표시됩니다. 우측 상단의 "계층 생성" 버튼을 클릭합니다.

26. 임의의 계층 이름을 입력합니다.

27. ".zip파일로 업로드"를 선택하고 업로드 버튼을 클릭합니다.

28. 다음 경로의 zip파일을 업로드합니다.  student_attandance/linux(혹은 raspberrypi)/lambda_functions/check-in-out/layer.zip

29. 우측 하단의 "생성" 버튼을 클릭합니다.

30. 새로운 계층이 생성됬음을 확인할 수 있습니다. 다시 check-in-out function으로 돌아갑니다.

31. 디자이너 항목에서 중앙의 "Layers"를 선택하고 [Add a layer] 버튼을 클릭합니다.

32. "사용자 지정 계층"을 클릭하고 이전에 생성한 계층을 선택합니다. 그리고 "추가" 버튼을 클릭합니다.

## How to use service
서비스 이용을 위해서 시스템 환경에 따라 다음의 코드를 실행시킵니다.  
  
**웹캠과 마이크가 구비된 Linux 시스템**
<pre>
<code>
python3 ./student_attandance/linux/rasp_main.py  
</code>
</pre>
**카메라 모듈, 마이크, 온도센서가 구비된 RaspberryPi**  
<pre>
<code> 
python3 ./student_attandance/raspberypi/rasp_main.py
</code>
</pre>
  
해당 코드 실행시 웹캠 혹은 카메라 모듈을 통해 스트리밍 화면이 호출됩니다. 온도센서가 구비된 시스템의 경우 열화상 스트리밍 화면도 호출됩니다.  
  
스트리밍 화면에서 얼굴의 라운딩박스가 인식되면 Polly를 통해 원하는 기능을 말씀해달라는 음성이 재생됩니다. 특정 기능을 호출하기 음성을 녹음하는 방법은 다음과 같습니다.
<pre>
<code>
* 수강생을 등록하는 기능
등록 <분반> <이름>

* 수강생 등록 후 출석하는 기능
출석

* 수강생 등록 후 퇴실하는 기능
퇴실
</code>
</pre>

음성 녹음이 완료된 후 S3 Voice bucket에 해당 음성을 업로드합니다. 해당 행위는 Lambda STT Fucntion의 트리거로 작동하여 서버리스 환경에서 코드가 실행됩니다. **AWS의 Transcribe는 5초 분량의 음성을 STT하는데 약 20~40초 정도의 시간이 소요됩니다.**

STT작업이 끝난 뒤 수강생의 얼굴을 캡쳐합니다. 온도센서가 장착된 시스템의 경우 수강생의 얼굴과 함께 체온도 측정합니다. 해당 작업이 끝나면 캡쳐된 캡쳐된 얼굴의 FaceID를 검색하고 데이터베이스에서 쿼리한 뒤 출결정보를 등록하는 과정이 진행됩니다.  

이후 TTS 기능을 통해 출결정보를 음성으로 출력하며 일련의 절차가 마무리 됩니다. 스트리밍 화면에 사용자의 얼굴이 재감지될 시 출결절차가 다시 시작됩니다.