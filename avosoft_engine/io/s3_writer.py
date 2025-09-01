# avosoft_engine/io/s3_writer.py
import boto3
import json
import csv
from io import StringIO
from typing import Iterable, Mapping
from .base import Writer
from ..config import SETTINGS

class S3Writer(Writer):
    def __init__(self):
        # Use IAM roles for Lambda in AWS, or keys for local testing
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=SETTINGS.aws_access_key_id,
            aws_secret_access_key=SETTINGS.aws_secret_access_key,
            region_name=SETTINGS.aws_region
        )
        self.bucket_name = SETTINGS.s3_bucket_name

    def write_jsonl(self, path: str, records: Iterable[Mapping]):
        """Write records as JSONL to a specific S3 path."""
        body = "\n".join([json.dumps(record, ensure_ascii=False) for record in records])
        self._upload_to_s3(path, body)

    def write_csv(self, path: str, rows: Iterable[Mapping], header: list[str]):
        """Write records as CSV to a specific S3 path."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        self._upload_to_s3(path, output.getvalue())

    def _upload_to_s3(self, key: str, body: str):
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body.encode('utf-8')
        )
        print(f"Successfully uploaded to s3://{self.bucket_name}/{key}") 