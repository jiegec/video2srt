import argparse
import os
import base64
from re import S
from time import sleep

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.asr.v20190614 import asr_client, models

parser = argparse.ArgumentParser(
    description='Recognize audio from video and generate srt')
parser.add_argument('videos', metavar='VIDEO', type=str, nargs='+',
                    help='path to video files')
parser.add_argument('--secret-id', type=str,
                    help='secret id')
parser.add_argument('--secret-key', type=str,
                    help='secret key')

args = parser.parse_args()
videos = args.videos
for video in videos:
    print('Processing {}'.format(video))
    base, ext = os.path.splitext(video)
    aac = '{}.aac'.format(base)
    srt = '{}.srt'.format(base)
    json = '{}.json'.format(base)

    # Step 1: convert to aac
    print('Convert to aac')
    os.system('ffmpeg -y -i "{}" -vn -ar 16000 "{}"'.format(video, aac))

    # Step 2: upload to tencent cloud
    print('Upload to tencent cloud')
    cred = credential.Credential(args.secret_id, args.secret_key)
    client = asr_client.AsrClient(cred, "ap-shanghai")

    data = open(aac, 'rb').read()

    req = models.CreateRecTaskRequest()
    req.EngineModelType = "16k_zh"
    req.ChannelNum = 1
    req.ResTextFormat = 2
    req.SourceType = 1
    req.ConvertNumMode = 3
    req.FilterModal = 1
    req.Data = base64.b64encode(data).decode('utf-8')
    resp = client.CreateRecTask(req)

    task_id = resp.Data.TaskId

    # Step 3: retrieve result
    while True:
        print('Waiting for result')
        req = models.DescribeTaskStatusRequest()
        req.TaskId = task_id
        resp = client.DescribeTaskStatus(req)
        if resp.Data.StatusStr == "success":
            open(json, 'w').write(resp.to_json_string())
            print('Saving json result')
            break
        sleep(5)

    # Step 3: save to srt
    print('Saving subtitle')
    result = resp.Data.Result
    counter = 1
    with open(srt, 'w') as f:
        for line in result.split('\n'):
            if len(line) == 0:
                break
            parts = line.split(']')
            times = parts[0].split(',')
            time_from = times[0][1:]
            time_to = times[1][:-1]

            print(counter, file=f)
            print('0:{} --> 0:{}'.format(time_from, time_to), file=f)
            print(']'.join(parts[1:]).strip(), file=f)
            print('', file=f)

            counter += 1
