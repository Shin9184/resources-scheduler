import json
import boto3
import time
from datetime import datetime, timedelta
import ipaddress

def get_ec2_instance_info(ec2):
    describe_instances = ec2.describe_instances(
        Filters=[ # schedule 태그로 필터링
            {
                'Name': 'tag:schedule',
                'Values': [
                    'your-tag1',
                    'your-tag2'
                    ...
                ],
            },
        ],
    )

    ec2_info = []

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
                'State': state  # 인스턴스 상태
            })
            
    return ec2_info
####################################################################################
def get_rds_instance_info(rds):
    describe_db_instances = rds.describe_db_instances()
    
    rds_info = []

    for db_instance in describe_db_instances['DBInstances']:
        db_instance_id = db_instance['DBInstanceIdentifier']
        status = db_instance.get('DBInstanceStatus')  # 수정된 부분: 'DBInstanceStatus'로 키 변경

        if 'TagList' in db_instance:  # 태그가 존재할 경우 확인
            for tag in db_instance['TagList']:
                if tag['Key'] == 'schedule' and tag['Value'] in ['your-tag1', 'your-tag2']: # schedule 태그의 값 출력
                    rds_info.append({
                        'DBInstanceIdentifier': db_instance_id,
                        'Status': status  # 인스턴스 상태
                    })

    return rds_info
####################################################################################
def get_rds_cluster_info(rds):
    describe_db_clusters = rds.describe_db_clusters()
    
    rds_cluster_info = []

    for db_cluster in describe_db_clusters['DBClusters']:
        db_cluster_id = db_cluster['DBClusterIdentifier']
        status = db_cluster.get('Status')  # 클러스터의 상태 키 확인 ('Status'로 수정)

        if 'TagList' in db_cluster:  # 태그가 존재할 경우 확인
            for tag in db_cluster['TagList']:
                if tag['Key'] == 'schedule' and tag['Value'] in ['your-tag1', 'your-tag2']: # schedule 태그의 값 출력
                    rds_cluster_info.append({
                        'DBClusterIdentifier': db_cluster_id,
                        'Status': status  # 인스턴스 상태
                    })

    return rds_cluster_info
####################################################################################
def start_ec2_resources(ec2, ec2_info):
    print("Starting EC2 resources...")
    for info in ec2_info:
        try:
            start_instances = ec2.start_instances(InstanceIds=[info['InstanceId']])
            for instance in start_instances['StartingInstances']:
                print(f"시작된 InstanceID : {instance['InstanceId']}")
        except Exception as e:
            print(f"Error starting instance {info['InstanceId']}: {str(e)}")
####################################################################################
def start_rds_resources(rds, rds_info, rds_clusters):
    print("Starting RDS resources...")
    for info in rds_info:
        try:
            start_db_instance = rds.start_db_instance(DBInstanceIdentifier=info['DBInstanceIdentifier'])
            print(f"시작된 DBInstanceID : {start_db_instance['DBInstance']['DBInstanceIdentifier']}")
        except Exception as e:
            print(f"Error starting DBInstance {info['DBInstanceIdentifier']}: {str(e)}")
    
    for cluster in rds_clusters:
        try:
            start_cluster = rds.start_db_cluster(DBClusterIdentifier=cluster['DBClusterIdentifier'])
            print(f"시작된 DBClusterID : {start_cluster['DBCluster']['DBClusterIdentifier']}")
        except Exception as e:
            print(f"Error starting DBCluster {cluster['DBClusterIdentifier']}: {str(e)}")
####################################################################################
def lambda_handler(event, context):
    # UTC 시간 조회
    utc_now = datetime.utcnow()
    utc_time = utc_now.strftime('%Y.%m.%d %a %H:%M:%S')
    print(f"UTC : {utc_time}")
    
    if (utc_now.hour == 22 and utc_now.minute == 50): # KST 오전 07:50분
        # RDS
        rds = boto3.client('rds')
        rds_info = get_rds_instance_info(rds)
        rds_cluster_info = get_rds_cluster_info(rds)

        print("시작 대상 리스트(RDS)")
        for info in rds_info:
            print(f"DBInstanceIdentifier: {info['DBInstanceIdentifier']}, Status: {info['Status']}")
        for info in rds_cluster_info:
            print(f"DBClusterIdentifier: {info['DBClusterIdentifier']}, Status: {info['Status']}")

        start_rds_resources(rds, rds_info, rds_cluster_info)
    
    if (utc_now.hour == 23 and utc_now.minute == 0): # KST 오전 08:00분
        # EC2
        ec2 = boto3.client('ec2')
        ec2_info = get_ec2_instance_info(ec2)
        
        print("시작 대상 리스트(EC2)")
        for info in ec2_info:
            print(f"InstanceId: {info['InstanceId']}, PrivateIp: {info['PrivateIp']}, Name: {info['Name']}, State: {info['State']}")
        start_ec2_resources(ec2, ec2_info)