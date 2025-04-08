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
        self.bucket_name = bucket_name
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
                Key=file_key,
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

    def upload_profile_picture(self, file, user_id):
        try:
            file_extension = os.path.splitext(file.filename)[1]
            
            content_type = mimetypes.guess_type(file.filename)[0]
            if content_type is None:
                content_type = 'image/jpeg'
            
            file_key = f"profiles/{user_id}/profile{file_extension}"
            
            extra_args = {
                'ContentType': content_type
            }
            
            self.s3.upload_fileobj(
                file, 
                self.bucket_name, 
                Key=file_key,
                ExtraArgs=extra_args
            )
            
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
        except (NoCredentialsError, ClientError) as e:
            raise Exception(f"Failed to upload profile picture: {str(e)}")

    def upload_perk_file(self, file, track_id, perk_id, is_audio=False):
        try:
            file_extension = os.path.splitext(file.filename)[1]
            
            content_type = mimetypes.guess_type(file.filename)[0]
            if content_type is None:
                content_type = 'audio/mpeg' if is_audio else 'application/octet-stream'
            
            # Determine the file path based on whether it's a stem or other perk file
            if is_audio:
                file_key = f"{track_id}/stems/{perk_id}{file_extension}"
            else:
                file_key = f"{track_id}/perks/{perk_id}{file_extension}"
            
            extra_args = {
                'ContentType': content_type
            }
            
            self.s3.upload_fileobj(
                file, 
                self.bucket_name,
                Key=file_key,
                ExtraArgs=extra_args
            )
            
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
        except (NoCredentialsError, ClientError) as e:
            raise Exception(f"Failed to upload perk file: {str(e)}")

    def delete_perk_file(self, track_id, perk_id, is_audio=False):
        try:
            # Try common file extensions
            extensions = ['.mp3', '.wav', '.zip', '.pdf', '.jpg', '.png'] if is_audio else ['.zip', '.pdf', '.jpg', '.png']
            
            for ext in extensions:
                try:
                    if is_audio:
                        file_key = f"{track_id}/stems/{perk_id}{ext}"
                    else:
                        file_key = f"{track_id}/perks/{perk_id}{ext}"
                    
                    self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
                except ClientError:
                    # Continue trying other extensions if this one fails
                    continue
        except ClientError as e:
            raise Exception(f"Failed to delete perk file: {str(e)}") 