import json
import boto3
import botocore
import datetime
from dateutil.tz import tzlocal

# AWS 역할 기반 세션 생성 함수
def assumed_role_session(role_arn: str, base_session: botocore.session.Session = None):
    print(f"Role: {role_arn}")
    base_session = base_session or boto3.session.Session()._session
    # 역할 기반 자격 증명 가져오기
    fetcher = botocore.credentials.AssumeRoleCredentialFetcher(
        client_creator = base_session.create_client,
        source_credentials = base_session.get_credentials(),
        role_arn = role_arn,
        extra_args = {}
    )
    # 자격 증명 갱신 설정
    creds = botocore.credentials.DeferredRefreshableCredentials(
        method = 'assume-role',
        refresh_using = fetcher.fetch_credentials,
        time_fetcher = lambda: datetime.datetime.now(tzlocal())
    )
    # 새로운 boto3 세션 생성 및 반환
    botocore_session = botocore.session.Session()
    botocore_session._credentials = creds
    return boto3.Session(botocore_session = botocore_session)
####################################################################################
# 환경별 AWS 세션 클라이언트 생성 함수
def get_session_client(env):
    # 환경에 따른 AWS 계정 ID 설정
    if env == 'aws1':
        account_id = '00000000001'
    elif env == 'aws2':
        account_id = '00000000002'
    else:
        raise ValueError(f"Invalid environment: {env}") # 잘못된 환경 설정 시 예외 발생
    
    # 역할 ARN 생성 및 세션 반환
    role_name = 'your-role-name'
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    session = assumed_role_session(role_arn)
    return session
####################################################################################
# 추가 AWS 세션 클라이언트 생성 함수 (추가 계정용)
def get_additional_session_client():
    account_id = '00000000003'  # 추가적인 계정
    role_name = 'your-role-name'
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    session = assumed_role_session(role_arn)
    return session
####################################################################################
# 스케줄러 중지 함수
def stop_scheduler(env, tag, time):
    try:
        # 세션 생성 및 EventBridge 클라이언트 초기화
        session = get_session_client(env)
        events = session.client('events')
        list_rules = events.list_rules()
        matched = False
        
        # 규칙 검색 및 업데이트
        for rule in list_rules['Rules']:
            if 'stopscheduler' in rule['Name'] and tag in rule['Name']:
                if rule['State'] == 'ENABLED':
                    print(f"Updating rule: {rule['Name']} with new time: {time}")
                    # 규칙의 실행 시간 업데이트
                    events.put_rule(
                        Name=rule['Name'],
                        ScheduleExpression=f"cron(0 {time} ? * MON-FRI *)",
                    )
                    matched = True
                    return f"Successfully updated stop scheduler for {tag} at {time}"
                else:
                    return f"Rule for {tag} is disabled"
        
        if not matched:
            raise Exception(f"No rule found for tag '{tag}'")
            
    except Exception as e:
        raise Exception(f"Failed to stop scheduler: {str(e)}")
####################################################################################
# EC2 인스턴스 정보 조회 함수
def get_ec2_instance_info(ec2, tag):
    # 태그 기준으로 EC2 인스턴스 조회
    describe_instances = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:schedule',
                'Values': [tag],  # 파라미터로 받은 tag 값 사용
            },
        ],
    )

    ec2_info = []

    # 인스턴스 정보 수집
    for reservation in describe_instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            private_ip = instance.get('PrivateIpAddress')
            name_tag = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), None)
            state = instance['State']['Name']

            ec2_info.append({
                'InstanceId': instance_id,
                'PrivateIp': private_ip,
                'Name': name_tag,
                'State': state
            })
            
    return ec2_info
####################################################################################
# RDS 인스턴스 정보 조회 함수
def get_rds_instance_info(rds, tag):
    describe_db_instances = rds.describe_db_instances()
    
    rds_info = []

    # 태그 기준으로 RDS 인스턴스 정보 수집
    for db_instance in describe_db_instances['DBInstances']:
        db_instance_id = db_instance['DBInstanceIdentifier']
        status = db_instance.get('DBInstanceStatus')

        if 'TagList' in db_instance:
            # schedule 태그가 일치하는 인스턴스만 선택
            if any(t['Key'] == 'schedule' and t['Value'] == tag for t in db_instance['TagList']):
                rds_info.append({
                    'DBInstanceIdentifier': db_instance_id,
                    'Status': status
                })

    return rds_info
####################################################################################
# RDS 클러스터 정보 조회 함수
def get_rds_cluster_info(rds, tag):
    describe_db_clusters = rds.describe_db_clusters()
    
    rds_cluster_info = []

    # 태그 기준으로 RDS 클러스터 정보 수집
    for db_cluster in describe_db_clusters['DBClusters']:
        db_cluster_id = db_cluster['DBClusterIdentifier']
        status = db_cluster.get('Status')

        if 'TagList' in db_cluster:
            # schedule 태그가 일치하는 클러스터만 선택
            if any(t['Key'] == 'schedule' and t['Value'] == tag for t in db_cluster['TagList']):
                rds_cluster_info.append({
                    'DBClusterIdentifier': db_cluster_id,
                    'Status': status
                })

    return rds_cluster_info
####################################################################################
# EC2 리소스 시작 함수
def start_ec2_resources(ec2, ec2_info):
    print("Starting EC2 resources...")
    
    # 기본 계정의 EC2 인스턴스 시작
    for info in ec2_info:
        try:
            if info['State'] != 'running':
                start_instances = ec2.start_instances(InstanceIds=[info['InstanceId']])
                for instance in start_instances['StartingInstances']:
                    print(f"시작된 InstanceID : {instance['InstanceId']}")
            else:
                print(f"인스턴스 이미 실행 중: {info['InstanceId']}, 건너뜀")
        except Exception as e:
            print(f"Error starting instance {info['InstanceId']}: {str(e)}")
    
    # 추가 계정의 EC2 인스턴스 시작
    try:
        additional_session = get_additional_session_client()
        additional_ec2 = additional_session.client('ec2')
        
        # 추가 계정의 EC2 정보 조회 (태그 기준)
        additional_ec2_info = get_ec2_instance_info(additional_ec2, "your-tag")  # 원하는 태그 값 지정

        for info in additional_ec2_info:
            try:
                if info['State'] != 'running':
                    start_instances = additional_ec2.start_instances(InstanceIds=[info['InstanceId']])
                    for instance in start_instances['StartingInstances']:
                        print(f"추가 계정 시작된 InstanceID : {instance['InstanceId']}")
                else:
                    print(f"추가 계정 인스턴스 이미 실행 중: {info['InstanceId']}, 건너뜀")
            except Exception as e:
                print(f"Error starting additional account instance {info['InstanceId']}: {str(e)}")

    except Exception as e:
        print(f"Error accessing additional account: {str(e)}")
####################################################################################
# RDS 리소스 시작 함수
def start_rds_resources(rds, rds_info, rds_clusters):
    print("Starting RDS resources...")

    # RDS 인스턴스 시작
    for info in rds_info:
        try:
            if info['DBInstanceStatus'] != 'available':
                start_db_instance = rds.start_db_instance(DBInstanceIdentifier=info['DBInstanceIdentifier'])
                print(f"시작된 DBInstanceID : {start_db_instance['DBInstance']['DBInstanceIdentifier']}")
            else:
                print(f"RDS 인스턴스 이미 실행 중: {info['DBInstanceIdentifier']}, 건너뜀")
        except Exception as e:
            print(f"Error starting DBInstance {info['DBInstanceIdentifier']}: {str(e)}")
    
    # RDS 클러스터 시작
    for cluster in rds_clusters:
        try:
            if cluster['Status'] != 'available':
                start_cluster = rds.start_db_cluster(DBClusterIdentifier=cluster['DBClusterIdentifier'])
                print(f"시작된 DBClusterID : {start_cluster['DBCluster']['DBClusterIdentifier']}")
            else:
                print(f"RDS 클러스터 이미 실행 중: {cluster['DBClusterIdentifier']}, 건너뜀")
        except Exception as e:
            print(f"Error starting DBCluster {cluster['DBClusterIdentifier']}: {str(e)}")
####################################################################################
# 스케줄러 시작 함수
def start_scheduler(env, tag):
    try:
        # 세션 및 클라이언트 초기화
        session = get_session_client(env)
        ec2 = session.client('ec2')
        ec2_info = get_ec2_instance_info(ec2, tag)
        rds = session.client('rds')
        rds_info = get_rds_instance_info(rds, tag)
        rds_cluster_info = get_rds_cluster_info(rds, tag)

        # 시작된 리소스 정보 수집
        started_resources = []

        # RDS 리소스 시작 정보 출력
        print("시작 대상 리스트(RDS)")
        for info in rds_info:
            print(f"DBInstanceIdentifier: {info['DBInstanceIdentifier']}, Status: {info['Status']}")
            started_resources.append(f"RDS Instance: {info['DBInstanceIdentifier']}")
        for info in rds_cluster_info:
            print(f"DBClusterIdentifier: {info['DBClusterIdentifier']}, Status: {info['Status']}")
            started_resources.append(f"RDS Cluster: {info['DBClusterIdentifier']}")

        # RDS 리소스 시작
        start_rds_resources(rds, rds_info, rds_cluster_info)

        # EC2 리소스 시작 정보 출력
        print("시작 대상 리스트(EC2)")
        for info in ec2_info:
            print(f"InstanceId: {info['InstanceId']}, Name: {info['Name']}, State: {info['State']}")
            started_resources.append(f"EC2: {info['Name']} ({info['InstanceId']})")

        # EC2 리소스 시작
        start_ec2_resources(ec2, ec2_info)

        # 시작된 리소스 목록 반환
        return f"Successfully started resources for tag '{tag}':\n" + "\n".join(started_resources)
            
    except Exception as e:
        raise Exception(f"Failed to start scheduler: {str(e)}")
####################################################################################
# Lambda 핸들러 함수
def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    # CORS 헤더 설정
    headers = {
        'Access-Control-Allow-Origin': 'https://your-domain.com',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST'
    }
    
    # CORS preflight 요청 처리
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight response'})
        }

    try:
        body = event.get('body', '{}')
        body_json = json.loads(body)
        
        if not body_json:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'message': 'No data received'})
            }
        
        result = []
        errors = []
        
        for item in body_json:
            env = item.get('env', 'N/A')
            tag = item.get('tag', 'N/A')
            time = item.get('time', 'N/A')
            action = item.get('action', 'N/A')
            print(f"Processing item - Env: {env}, Tag: {tag}, Time: {time}, Action: {action}")
            
            try:
                if action == 'stop':
                    response = stop_scheduler(env, tag, time)
                    result.append(response)
                elif action == 'start':
                    response = start_scheduler(env, tag)
                    result.append(response)
                else:
                    errors.append(f"Invalid action '{action}' for tag '{tag}'")
            except Exception as e:
                errors.append(f"Error processing {tag}: {str(e)}")
        
        if errors:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'errors': errors})
            }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': '\n'.join(result)})
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': str(e)})
        }