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
                    'your-tag',
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
        status = db_instance.get('DBInstanceStatus')

        if 'TagList' in db_instance:  # 태그가 존재할 경우 확인
            for tag in db_instance['TagList']:
                if tag['Key'] == 'schedule' and tag['Value'] == 'your-tag':  # schedule 태그의 값 출력
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
                if tag['Key'] == 'schedule' and tag['Value'] == 'your-tag':  # schedule 태그의 값 출력
                    rds_cluster_info.append({
                        'DBClusterIdentifier': db_cluster_id,
                        'Status': status  # 인스턴스 상태
                    })

    return rds_cluster_info
####################################################################################
def stop_ec2_resources(ec2, ec2_info):
    print("Stopping EC2 resources...")
    for info in ec2_info:
        try:
            stop_instances = ec2.stop_instances(InstanceIds=[info['InstanceId']])
            for instance in stop_instances['StoppingInstances']:
                print(f"중지된 InstanceID : {instance['InstanceId']}")
        except Exception as e:
            print(f"Error stopping instance {info['InstanceId']}: {str(e)}")
####################################################################################
def stop_rds_resources(rds, rds_info, rds_clusters):
    print("Stopping RDS resources...")
    for info in rds_info:
        try:
            stop_db_instance = rds.stop_db_instance(DBInstanceIdentifier=info['DBInstanceIdentifier'])
            print(f"중지된 DBInstanceID : {stop_db_instance['DBInstance']['DBInstanceIdentifier']}")
        except Exception as e:
            print(f"Error stopping DBInstance {info['DBInstanceIdentifier']}: {str(e)}")
    
    for cluster in rds_clusters:
        try:
            stop_cluster = rds.stop_db_cluster(DBClusterIdentifier=cluster['DBClusterIdentifier'])
            print(f"중지된 DBClusterID : {stop_cluster['DBCluster']['DBClusterIdentifier']}")
        except Exception as e:
            print(f"Error stopping DBCluster {cluster['DBClusterIdentifier']}: {str(e)}")
####################################################################################
def lambda_handler(event, context):
    # UTC 시간 조회
    utc_now = datetime.utcnow()
    utc_time = utc_now.strftime('%Y.%m.%d %a %H:%M:%S')
    print(f"UTC : {utc_time}")
    
    # EC2 리스트 조회
    ec2 = boto3.client('ec2')
    ec2_info = get_ec2_instance_info(ec2)
    
    print("중지 대상 리스트(EC2)")
    for info in ec2_info:
        print(f"InstanceId: {info['InstanceId']}, PrivateIp: {info['PrivateIp']}, Name: {info['Name']}, State: {info['State']}")

    # RDS 리스트 조회
    rds = boto3.client('rds')
    rds_info = get_rds_instance_info(rds)
    rds_cluster_info = get_rds_cluster_info(rds)
    
    print("중지 대상 리스트(RDS)")
    for info in rds_info:
        print(f"DBInstanceIdentifier: {info['DBInstanceIdentifier']}, Status: {info['Status']}")
    for info in rds_cluster_info:
        print(f"DBClusterIdentifier: {info['DBClusterIdentifier']}, Status: {info['Status']}")
    
    # EC2, RDS 종료
    stop_ec2_resources(ec2, ec2_info)
    stop_rds_resources(rds, rds_info, rds_cluster_info)