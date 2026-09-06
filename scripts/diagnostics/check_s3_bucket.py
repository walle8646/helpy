#!/usr/bin/env python3
"""Test se il bucket S3 è accessibile"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "eu-south-1")

print(f"🔍 Testing S3 bucket access...")
print(f"   - Bucket: {AWS_S3_BUCKET_NAME}")
print(f"   - Region: {AWS_S3_REGION}")
print(f"   - Access Key: {AWS_ACCESS_KEY_ID[:10]}...")

try:
    s3_client = boto3.client(
        's3',
        region_name=AWS_S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Prova a listar i bucket
    response = s3_client.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    
    print(f"\n✅ Connected to AWS S3!")
    print(f"   Available buckets: {buckets}")
    
    if AWS_S3_BUCKET_NAME in buckets:
        print(f"\n✅ Bucket '{AWS_S3_BUCKET_NAME}' exists!")
        
        # Prova a listar oggetti
        try:
            objects = s3_client.list_objects_v2(Bucket=AWS_S3_BUCKET_NAME, MaxKeys=5)
            count = objects.get('KeyCount', 0)
            print(f"   - Objects in bucket: {count}")
        except Exception as e:
            print(f"   - Error listing objects: {e}")
    else:
        print(f"\n❌ Bucket '{AWS_S3_BUCKET_NAME}' NOT found!")
        print(f"   Available: {buckets}")
        
except Exception as e:
    print(f"\n❌ Error connecting to S3: {e}")
    import traceback
    traceback.print_exc()
