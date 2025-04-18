import json
import boto3
import botocore
import datetime
from dateutil.tz import tzlocal

# assume role session 생성 함수
def assumed_role_session(role_arn: str, base_session: botocore.session.Session = None):
    # print(f"Role: {role_arn}")
    base_session = base_session or boto3.session.Session()._session
    fetcher = botocore.credentials.AssumeRoleCredentialFetcher(
        client_creator=base_session.create_client,
        source_credentials=base_session.get_credentials(),
        role_arn=role_arn,
        extra_args={}
    )
    creds = botocore.credentials.DeferredRefreshableCredentials(
        method='assume-role',
        refresh_using=fetcher.fetch_credentials,
        time_fetcher=lambda: datetime.datetime.now(tzlocal())
    )
    botocore_session = botocore.session.Session()
    botocore_session._credentials = creds
    return boto3.Session(botocore_session=botocore_session)

# EventBridge 규칙 리스트를 조회하는 함수
def event_list():
    result = {}

    # assume_role.json 파일을 열어서 assume_role_list 정보를 불러옴
    with open('./assume_role.json') as f:
        data = json.load(f)

    # assume_role_list에 있는 각 역할과 환경명을 조회
    for item in data.get('assume_role_list', []):
        env = item.get('env')
        role_arn = item.get('assume_role')
        if not role_arn or not env:
            continue  # 둘 중 하나라도 없으면 건너뜀

        try:
            session = assumed_role_session(role_arn)
            events = session.client('events')
            rules = events.list_rules()
            
            # 규칙들을 넣기 위한 리스트
            matched_rules = []

            print(f"환경 : {env}")
            print(f"역할 : {role_arn}")

            for rule in rules.get('Rules', []):
                rule_name = rule.get('Name', '')
                rule_state = rule.get('State', '')

                # 상태가 ENABLED이고 이름에 "stopscheduler" 또는 "startscheduler"가 포함된 규칙만 대상
                if rule_state == 'ENABLED' and (
                    'stopscheduler' in rule_name.lower() or 'startscheduler' in rule_name.lower()
                ):
                    try:
                        # 규칙 상세 정보 조회
                        rule_detail = events.describe_rule(Name=rule_name)
                        print(f"Name : {rule_name} Schedule : {rule_detail.get('ScheduleExpression', 'None')}")
                        matched_rules.append({
                            'name': rule_name,
                            'schedule': rule_detail.get('ScheduleExpression', 'None')
                        })
                    except Exception as e:
                        # 규칙 상세 조회 실패 시 로그 출력 및 'X'로 표시
                        print(f"describe_rule 실패: {rule_name}, 오류: {e}")
                        matched_rules.append({
                            'name': rule_name,
                            'schedule': 'X'
                        })

            # env의 결과를 결과 딕셔너리에 저장
            result[env] = matched_rules

        except Exception as e:
            # assume role이나 API 호출 실패 시 에러 저장
            print(f"ERROR : {role_arn} 예외 발생: {e}")
            result[env] = f"Error: {str(e)}"

    # 최종 결과 반환
    return result

# Lambda 핸들러 함수
def lambda_handler(event, context):
    print("받은 이벤트:", event)

    headers = {
        'Access-Control-Allow-Origin': 'https://your-domain.com',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,GET',
        'Access-Control-Allow-Credentials': 'true'
    }

    # CORS preflight 요청 처리
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight response'})
        }

    try:
        current_path = event.get('path', '')

        # 상태 확인 요청 처리
        if current_path == '/status':
            result = event_list()
            # print(result)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'rules': result}, indent=2, ensure_ascii=False)
            }

        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'message': '지원하지 않는 경로입니다.'})
        }

    except Exception as e:
        print(f"서버 에러: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': '서버 에러가 발생했습니다.'})
        }