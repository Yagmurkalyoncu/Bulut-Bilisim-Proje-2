"""
aws_setup.py
-------------
AWS kaynaklarını otomatik oluşturur:
  1. Kinesis Data Stream  (iot-sensor-stream)
  2. DynamoDB tablosu     (IoTSensorData)
  3. Lambda IAM rolü      (iot-lambda-role)

KULLANIM:
  python aws_setup.py          # Kaynakları oluştur
  python aws_setup.py --delete # Kaynakları sil (ücret oluşmasın)
"""

import boto3
import json
import time
import logging
import argparse
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REGION      = os.getenv("AWS_REGION", "eu-west-1")
STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "iot-sensor-stream")
TABLE_NAME  = os.getenv("DYNAMODB_TABLE_NAME", "IoTSensorData")
ROLE_NAME   = "iot-lambda-kinesis-role"

session  = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=REGION
)
kinesis  = session.client("kinesis")
dynamodb = session.client("dynamodb")
iam      = session.client("iam")


def create_kinesis_stream():
    """1 shard'lık Kinesis Data Stream oluştur."""
    logger.info(f"Kinesis stream oluşturuluyor: {STREAM_NAME}")
    try:
        kinesis.create_stream(StreamName=STREAM_NAME, ShardCount=1)
        waiter = kinesis.get_waiter("stream_exists")
        waiter.wait(StreamName=STREAM_NAME)
        logger.info(f"✓ Kinesis stream hazır: {STREAM_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            logger.info(f"Stream zaten mevcut: {STREAM_NAME}")
        else:
            raise


def create_dynamodb_table():
    """DynamoDB tablosu oluştur."""
    logger.info(f"DynamoDB tablosu oluşturuluyor: {TABLE_NAME}")
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "device_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp",  "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "device_id", "AttributeType": "S"},
                {"AttributeName": "timestamp",  "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[{"Key": "Project", "Value": "IoTCloudProject"}]
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        logger.info(f"✓ DynamoDB tablosu hazır: {TABLE_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            logger.info(f"Tablo zaten mevcut: {TABLE_NAME}")
        else:
            raise


def create_lambda_role():
    """Lambda IAM rolü oluştur."""
    logger.info(f"IAM rolü oluşturuluyor: {ROLE_NAME}")
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    try:
        response = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IoT Lambda - Kinesis okuma + DynamoDB yazma"
        )
        role_arn = response["Role"]["Arn"]
        policies = [
            "arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
            "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
        ]
        for policy_arn in policies:
            iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy_arn)
            logger.info(f"  Policy eklendi: {policy_arn.split('/')[-1]}")
        time.sleep(10)
        logger.info(f"✓ IAM rolü hazır: {role_arn}")
        return role_arn
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            role = iam.get_role(RoleName=ROLE_NAME)
            logger.info(f"Rol zaten mevcut: {role['Role']['Arn']}")
            return role["Role"]["Arn"]
        else:
            raise


def setup_all():
    logger.info("=" * 50)
    logger.info("AWS Kaynak Kurulumu Başlıyor")
    logger.info(f"Bölge: {REGION}")
    logger.info("=" * 50)
    create_kinesis_stream()
    create_dynamodb_table()
    role_arn = create_lambda_role()
    logger.info("Kurulum tamamlandı!")
    logger.info(f"  Kinesis Stream : {STREAM_NAME}")
    logger.info(f"  DynamoDB Tablo : {TABLE_NAME}")
    logger.info(f"  Lambda IAM Rol : {role_arn}")


def delete_all():
    logger.warning("Tüm kaynaklar siliniyor...")
    try:
        kinesis.delete_stream(StreamName=STREAM_NAME)
        logger.info(f"✓ Kinesis stream silindi")
    except ClientError:
        pass
    try:
        dynamodb.delete_table(TableName=TABLE_NAME)
        logger.info(f"✓ DynamoDB tablosu silindi")
    except ClientError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWS IoT kaynak yönetimi")
    parser.add_argument("--delete", action="store_true", help="Kaynakları sil")
    args = parser.parse_args()
    if args.delete:
        delete_all()
    else:
        setup_all()