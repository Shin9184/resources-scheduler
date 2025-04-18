import json
import boto3
import jwt
import datetime
import time
import os
from boto3.dynamodb.conditions import Key

# JWT 관련 환경 설정
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-default-secret-key')  # JWT 서명에 사용할 비밀키
JWT_ALGORITHM = 'HS256'  # JWT 암호화 알고리즘
JWT_EXPIRATION_HOURS = 1  # JWT 토큰 유효 시간 (1시간)

# DynamoDB 테이블 이름 설정
USER_TABLE = 'your-user-table'  # 사용자 정보 테이블
TOKEN_TABLE = 'your-token-table'  # 토큰 저장 테이블

# DynamoDB 리소스 초기화
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
            KeyConditionExpression=Key('token').eq(token)  # 'token' 기준으로 검색
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

# JWT 토큰 생성 함수
def create_jwt_token(id):
    try:
        current_time = datetime.datetime.utcnow()
        exp_time = current_time + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
        # JWT 페이로드 구성
        payload = {
            'id': id,  # 사용자 ID
            'exp': exp_time,  # 만료 시간
            'iat': current_time  # 발급 시간
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    except Exception as e:
        print(f"토큰 생성 중 에러 발생: {str(e)}")
        raise e

# 생성된 JWT 토큰을 DynamoDB에 저장하는 함수
def save_jwt_token(id, token):
    try:
        table = dynamodb.Table(TOKEN_TABLE)
        
        # 현재 시간과 만료 시간 계산
        current_time = int(datetime.datetime.utcnow().timestamp())
        expires_at = current_time + (JWT_EXPIRATION_HOURS * 3600)  # TTL을 위한 만료 시간
        
        # 토큰 정보를 DynamoDB에 저장
        table.put_item(
            Item={
                'id': id,
                'token': token,
                'created_at': current_time,
                'expires_at': expires_at
            }
        )
        return True
    except Exception as e:
        print(f"토큰 저장 중 에러: {str(e)}")
        return False

# JWT 토큰 삭제 함수 (로그아웃 시 사용)
def delete_jwt_token(token):
    try:
        table = dynamodb.Table(TOKEN_TABLE)
        # 토큰으로 항목 찾기
        response = table.query(
            KeyConditionExpression=Key('token').eq(token)
        )
        
        if response['Items']:
            # 토큰 삭제
            table.delete_item(
                Key={
                    'token': token
                }
            )
            return True
        return False
    except Exception as e:
        print(f"토큰 삭제 중 에러: {str(e)}")
        return False

# Lambda 핸들러 함수
def lambda_handler(event, context):
    print("받은 이벤트:", event)
    
    # CORS 헤더 설정
    headers = {
        'Access-Control-Allow-Origin': 'https://your-domain.com',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        'Access-Control-Allow-Credentials': 'true'
    }
    
    # CORS preflight 요청 처리 (OPTIONS 메서드)
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight response'})
        }

    try:
        current_path = event.get('path', '')
        
        # 로그아웃 요청 처리 (/logout 엔드포인트)
        if current_path == '/logout':
            # 쿠키에서 토큰 추출
            cookies = event.get('headers', {}).get('Cookie', '')
            if not cookies:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'message': '토큰이 없습니다.'})
                }
            
            # 쿠키에서 token 값 찾기
            token = None
            for cookie in cookies.split('; '):
                if cookie.startswith('token='):
                    token = cookie.split('=')[1]
                    break
            
            if not token:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'message': '토큰이 없습니다.'})
                }
            
            # DynamoDB에서 토큰 삭제 및 쿠키 만료 처리
            if delete_jwt_token(token):
                # 쿠키 만료 설정
                headers['Set-Cookie'] = 'token=; Domain=your-domain.com; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0'
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({'message': '로그아웃 성공'})
                }
            else:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'message': '로그아웃 처리 중 오류가 발생했습니다.'})
                }

        # 인증 상태 확인 요청 처리 (/auth 엔드포인트)
        if current_path == '/auth':
            # 쿠키에서 토큰 추출
            cookies = event.get('headers', {}).get('Cookie', '')

            if not cookies:
                print("쿠키가 없습니다.")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'message': '인증되지 않은 요청입니다.'})
                }
            
            # 쿠키에서 'token' 값 추출
            token = None
            for cookie in cookies.split('; '):  # 쿠키는 세미콜론(;)과 공백으로 구분됨
                if cookie.startswith('token='):
                    token = cookie.split('=', 1)[1]  # 'token=' 이후 값만 추출
                    break

            if not token:
                print("토큰이 없습니다.")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'message': '토큰이 누락되었습니다.'})
                }

            print(f"추출된 토큰: {token}")
            
            # 토큰 유효성 검증
            is_valid, result = verify_jwt_token(token)
            if is_valid:
                print(f"토큰 검증 성공: {result}")
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'message': '유효한 토큰입니다.',
                        'user': result['id']
                    })
                }
            else:
                print(f"토큰 검증 실패: {result}")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'message': result})
                }

        # 로그인 요청 처리 (/login 엔드포인트)
        if current_path == '/login':
            # 요청 바디에서 로그인 정보 추출
            body = json.loads(event.get('body', '{}'))
            id = body.get('id')
            password = body.get('password')
            
            # 입력값 검증
            if not id or not password:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'message': '아이디와 비밀번호를 입력해주세요.'})
                }

            # DynamoDB에서 사용자 정보 조회
            table = dynamodb.Table(USER_TABLE)
            response = table.query(
                KeyConditionExpression=Key('id').eq(id)
            )
            
            if not response['Items']:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'message': '아이디 또는 비밀번호가 올바르지 않습니다.'})
                }
            
            # users 테이블에 있는 id, password 의 값
            users_id = response['Items'][0]
            users_password = users_id['password']
            
            if password == users_password: # 패스워드 일치 시 토큰 생성
                token = create_jwt_token(id)
                
                # 생성된 토큰을 DynamoDB에 저장
                if not save_jwt_token(id, token):
                    return {
                        'statusCode': 500,
                        'headers': headers,
                        'body': json.dumps({'message': '토큰 저장 실패'})
                    }
                
                # JWT 토큰만 HttpOnly 쿠키로 설정
                token_cookie = f'token={token}; Domain=your-domain.com; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age={JWT_EXPIRATION_HOURS * 3600}'
                headers['Set-Cookie'] = token_cookie
                
                print("로그인 성공")
                print(f"사용자 : {id}")
                print(f"생성된 쿠키: {token_cookie}")
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'message': '로그인 성공',
                        'id': id,
                        'token': token
                    })
                }
            else:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'message': '비밀번호가 일치하지 않습니다.'})
                }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': str(e)})
        }