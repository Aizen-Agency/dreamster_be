import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os

class S3Service:
    def __init__(self, bucket_name):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'eu-north-1')
        )
        self.bucket_name = 'dreamster-tracks'

    def upload_file(self, file, track_id, is_artwork):
        try:
            file_extension = os.path.splitext(file.filename)[1]
            file_key = f"{track_id}/{track_id}{'-art' if is_artwork else ''}{file_extension}"
            self.s3.upload_fileobj(file, self.bucket_name, file_key)
            return f"https://s3.eu-north-1.amazonaws.com/{self.bucket_name}.s3.amazonaws.com/{track_id}"
        except (NoCredentialsError, ClientError) as e:
            raise Exception(f"Failed to upload file: {str(e)}")

    def get_file_url(self, track_id, is_artwork):
        file_key = f"{track_id}/{track_id}{'-art' if is_artwork else ''}"
        return f"https://s3.eu-north-1.amazonaws.com/{self.bucket_name}.s3.amazonaws.com/{file_key}"

    def delete_file(self, track_id, is_artwork):
        try:
            file_key = f"{track_id}/{track_id}{'-art' if is_artwork else ''}"
            self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
        except ClientError as e:
            raise Exception(f"Failed to delete file: {str(e)}") 