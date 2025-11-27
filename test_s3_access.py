#!/usr/bin/env python3
"""
Test se il bucket S3 è accessibile con le credenziali nel .env
"""
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "eu-south-1")

print(f"Testing S3 bucket access...")
print(f"  - Bucket: {AWS_S3_BUCKET_NAME}")
print(f"  - Region: {AWS_S3_REGION}")
print(f"  - Access Key: {AWS_ACCESS_KEY_ID[:20]}...")

try:
    s3_client = boto3.client(
        's3',
        region_name=AWS_S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Test 1: List buckets
    print("\n✓ Test 1: Listing all S3 buckets...")
    response = s3_client.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    print(f"  Found {len(buckets)} buckets: {buckets[:5]}...")
    
    if AWS_S3_BUCKET_NAME in buckets:
        print(f"  ✅ Bucket '{AWS_S3_BUCKET_NAME}' EXISTS!")
    else:
        print(f"  ❌ Bucket '{AWS_S3_BUCKET_NAME}' NOT FOUND!")
        print(f"  Available buckets: {buckets}")
    
    # Test 2: Try to upload a test file
    print("\n✓ Test 2: Attempting to put a test object...")
    test_key = "test/hello.txt"
    s3_client.put_object(
        Bucket=AWS_S3_BUCKET_NAME,
        Key=test_key,
        Body=b"Hello from Helpy test!"
    )
    print(f"  ✅ Successfully uploaded test object: {test_key}")
    
    # Test 3: List objects in bucket
    print("\n✓ Test 3: Listing objects in bucket...")
    response = s3_client.list_objects_v2(
        Bucket=AWS_S3_BUCKET_NAME,
        MaxKeys=5
    )
    
    if 'Contents' in response:
        print(f"  Found {response['KeyCount']} objects:")
        for obj in response['Contents']:
            print(f"    - {obj['Key']}")
    else:
        print(f"  Bucket is empty or no objects found")
    
    print("\n✅ All S3 tests passed! Bucket is accessible.")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
