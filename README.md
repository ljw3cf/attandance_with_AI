# AWS AI 서비스를 활용한 출결관리 서비스

## Introduction
AWS의 AI 서비스들을 활용한 얼굴인식 기반 출결관리 서비스 입니다.

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

## Requirements installation

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

2 AWS 콘솔에서 IAM 서비스에 접속합니다. 좌측 엑세스 관리탭을 클릭하고 해당하는 사용자를 클릭합니다.

3 보안 자격 증명 메뉴를 클릭하고 엑세스 키 항목에서 엑세스 키 만들기 버튼을 클릭합니다.

4 해당 사용자의 Access Key와 Secret Access Key가 표시됩니다. 해당 부분을 메모하거나 csv형태로 저장합니다.

5 AWS 계정의 Credential을 시스템에 등록합니다.
<pre>
<code>
$ aws configure
AWS Access Key ID []: <메모한 Access_key 입력>
AWS Secret Access Key []: <메모한 Secret Access Key 입력>
Default region name []: <사용할 region>
Default output format []: # <엔터>

</code>
</pre>

6 Credential은 기본적으로 ~/. aws디렉토리에 config와 credentials 상태로 저장됩니다.
<pre>
<code>
$ ls ~/.aws
config  credentials
</code>
</pre>

7 boto3를 설치합니다.
<pre>
<code>
$ pip3 install boto3
</code>
</pre>

8 기타 필요한 라이브러리를 설치합니다.
<pre>
<code>
# opencv 설치
$ apt install -y python3-opencv

# pyaudio 설치
$ apt install -y python3-pyaudio
</code>
</pre>

9 음성을 재생시켜 줄 플레이어를 설치합니다.
<pre>
<code>
$ apt install -y mplayer
</code>
</pre>

10 서비스를 위한 코드를 다운로드 합니다.
<pre>
<code>
$ git clone https://github.com/ljw3cf/attandance_with_AI.git
</code>
</pre>

## Service setup
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

* STT: sound-bucket에 업로드된 음성을 transcribe를 이용하여 텍스트로 변환합니다.
* Check-in-out: image-bucket에 업로드된 이미지를 rekognition을 이용하여 분석합니다.   
그리고 필요한 정보를 Database에 입력하고 수강생에게 들려줄 메세지를 polly를 이용하여 TTS합니다.

각 Lambda function을 생성하는 방법은 다음과 같습니다.  
* STT
1. AWS 콘솔에서 AWS Lambda를 선택합니다.
2. 좌측 메뉴에서 함수를 클릭하고 함수 생성버튼을 클릭합니다.
3. 새로 작성 탭을 클릭하고 함수 이름을 지정합니다. 런타임은 Python 3.8을 선택합니다. 