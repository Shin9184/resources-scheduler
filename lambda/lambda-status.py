import json
import boto3
import botocore
import datetime
from dateutil.tz import tzlocal

# JWT 관련 환경 설정
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-default-secret-key')
JWT_ALGORITHM = 'HS256'
TOKEN_TABLE = 'your-token-table'

# DynamoDB 테이블 이름 설정
dynamodb = boto3.resource('dynamodb')

# JWT 토큰 검증 함수
def verify_jwt_token(token):
    try:
        # JWT 토큰 디코딩 및 검증
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        print(f"토큰 디코딩 결과: {payload}")
        
        # 토큰 만료 시간 확인
        exp_timestamp = payload.get('exp')
        if not exp_timestamp:
            return False, "토큰에 만료 시간이 없습니다."
            
        # 현재 시간과 비교하여 만료 여부 확인
        current_time = datetime.datetime.utcnow().timestamp()
        if current_time > exp_timestamp:
            return False, "토큰이 만료되었습니다."
            
        # DynamoDB에서 토큰 존재 여부 확인
        table = dynamodb.Table(TOKEN_TABLE)
        response = table.query(
            KeyConditionExpression=Key('token').eq(token)
        )
        
        if not response['Items']:
            return False, "저장된 토큰을 찾을 수 없습니다."
            
        stored_token = response['Items'][0]['token']
        if token != stored_token:
            return False, "토큰이 일치하지 않습니다."
            
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "토큰이 만료되었습니다."
    except jwt.InvalidTokenError:
        return False, "유효하지 않은 토큰입니다."
    except Exception as e:
        return False, f"토큰 검증 중 오류 발생: {str(e)}"

# 인증 검증 함수
def authenticate_request(event):
    # 쿠키에서 토큰 추출
    cookies = event.get('headers', {}).get('Cookie', '')
    
    if not cookies:
        return False, "쿠키가 없습니다."
    
    # 쿠키에서 'token' 값 추출
    token = None
    for cookie in cookies.split('; '):
        if cookie.startswith('token='):
            token = cookie.split('=', 1)[1]
            break

    if not token:
        return False, "토큰이 누락되었습니다."

    # 토큰 유효성 검증
    is_valid, result = verify_jwt_token(token)
    if is_valid:
        return True, result
    else:
        return False, result

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
        # 인증 검증
        is_authenticated, auth_result = authenticate_request(event)
        if not is_authenticated:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'message': f'Authentication failed: {auth_result}'})
            }

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