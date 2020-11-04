import json
import boto3

transcribe = boto3.client('transcribe')

def start_transcription(job_name, job_uri):
    response = transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': job_uri},
                MediaFormat='wav',
                LanguageCode='ko-KR',
                Settings={'VocabularyName': "customvocabulary"}
                )
    return response['TranscriptionJob']['StartTime']

def lambda_handler(event, context):
    object_key = event['Records'][0]['s3']['object']['key']
    job_name = object_key
    bucket = event['Records'][0]['s3']['bucket']['name']
    job_url = "https://%s.s3-ap-northeast-1.amazonaws.com/" % bucket + object_key
    
    start_time = start_transcription(job_name, job_url)
    print("Transcription StartTime: " + str(start_time))
