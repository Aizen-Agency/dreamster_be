import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import mimetypes

class S3Service:
    def __init__(self, bucket_name):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'eu-north-1')
        )
        self.bucket_name = 'dreamster-tracks'
        self.region = os.environ.get('AWS_REGION', 'eu-north-1')

    def upload_file(self, file, track_id, is_artwork):
        try:
            file_extension = os.path.splitext(file.filename)[1]
            
            content_type = mimetypes.guess_type(file.filename)[0]
            if content_type is None:
                content_type = 'image/jpeg' if is_artwork else 'audio/mpeg'
            
            if is_artwork:
                file_key = f"{track_id}/artwork{file_extension}"
            else:
                file_key = f"{track_id}/audio{file_extension}"
            
            extra_args = {
                'ContentType': content_type
            }
            
            self.s3.upload_fileobj(
                file, 
                self.bucket_name, 
                file_key,
                ExtraArgs=extra_args
            )
            
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
        except (NoCredentialsError, ClientError) as e:
            raise Exception(f"Failed to upload file: {str(e)}")

    def get_file_url(self, track_id, is_artwork):
        extension = '.jpg' if is_artwork else '.mp3'
        file_key = f"{track_id}/{'artwork' if is_artwork else 'audio'}{extension}"
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"

    def delete_file(self, track_id, is_artwork):
        try:
            extension = '.jpg' if is_artwork else '.mp3'
            file_key = f"{track_id}/{'artwork' if is_artwork else 'audio'}{extension}"
            self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
        except ClientError as e:
            raise Exception(f"Failed to delete file: {str(e)}") 