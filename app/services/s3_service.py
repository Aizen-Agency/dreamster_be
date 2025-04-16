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
            if not is_artwork:
                # For audio files, we can keep the .mp3 assumption
                file_key = f"{track_id}/audio.mp3"
                self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
            else:
                # For artwork, try common image extensions
                extensions = ['.jpg', '.jpeg', '.png', '.gif']
                deleted = False
                
                # Try to list objects first to find the exact file
                try:
                    response = self.s3.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=f"{track_id}/artwork"
                    )
                    
                    if 'Contents' in response:
                        for obj in response.get('Contents', []):
                            if obj['Key'].startswith(f"{track_id}/artwork"):
                                self.s3.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                                deleted = True
                                break
                except Exception:
                    pass
                
                # If listing didn't work, try common extensions
                if not deleted:
                    for ext in extensions:
                        try:
                            file_key = f"{track_id}/artwork{ext}"
                            self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
                        except ClientError:
                            continue
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

    def upload_perk_file(self, file, track_id, perk_id, is_audio=False, file_index=None, is_stem_category=None):
        try:
            # Reset file position to beginning
            file.seek(0)
            
            file_extension = os.path.splitext(file.filename)[1]
            
            content_type = mimetypes.guess_type(file.filename)[0]
            if content_type is None:
                content_type = 'audio/mpeg' if is_audio else 'application/octet-stream'
            
            # Check if we need to determine the stem category from the database
            if is_stem_category is None and perk_id:
                # Import here to avoid circular imports
                from app.models.trackperk import TrackPerk, Category
                perk = TrackPerk.query.get(perk_id)
                is_stem_category = perk and perk.category == Category.stem
            
            # Determine the file path based on category and file type
            if is_stem_category:
                # For stem files (always audio)
                if file_index is None:
                    file_key = f"{track_id}/stems/{perk_id}{file_extension}"
                else:
                    file_key = f"{track_id}/stems/{perk_id}/audio{file_index}{file_extension}"
            else:
                # For all other perk files (including custom audio)
                if file_index is None:
                    file_key = f"{track_id}/perks/{perk_id}{file_extension}"
                else:
                    # Use appropriate prefix based on file type
                    prefix = "audio" if is_audio else "file"
                    file_key = f"{track_id}/perks/{perk_id}/{prefix}{file_index}{file_extension}"
            
            print(f"S3 file key: {file_key}")
            print(f"Content type: {content_type}")
            
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
            print(f"S3 upload error: {str(e)}")
            raise Exception(f"Failed to upload perk file: {str(e)}")
        except Exception as e:
            print(f"Unexpected error in upload_perk_file: {str(e)}")
            raise Exception(f"Unexpected error uploading file: {str(e)}")

    def delete_perk_file(self, track_id, perk_id, is_audio=False, file_index=None):
        try:
            # Try common file extensions
            extensions = ['.mp3', '.wav'] if is_audio else ['.zip', '.pdf', '.jpg', '.png', '.doc', '.docx']
            
            # If we know there are multiple files, try to delete the specific file
            if file_index is not None:
                for ext in extensions:
                    try:
                        if is_audio:
                            file_key = f"{track_id}/stems/{perk_id}/audio{file_index}{ext}"
                        else:
                            file_key = f"{track_id}/perks/{perk_id}/file{file_index}{ext}"
                        
                        self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
                    except ClientError:
                        # Continue trying other extensions if this one fails
                        continue
            else:
                # Try both the direct file and the directory structure
                for ext in extensions:
                    try:
                        # Try direct file first
                        if is_audio:
                            file_key = f"{track_id}/stems/{perk_id}{ext}"
                        else:
                            file_key = f"{track_id}/perks/{perk_id}{ext}"
                        
                        self.s3.delete_object(Bucket=self.bucket_name, Key=file_key)
                    except ClientError:
                        # Continue trying other extensions if this one fails
                        continue
                
                # Also try to delete any files in subdirectories
                try:
                    # List all objects with the prefix
                    if is_audio:
                        prefix = f"{track_id}/stems/{perk_id}/"
                    else:
                        prefix = f"{track_id}/perks/{perk_id}/"
                    
                    response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            self.s3.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                except ClientError:
                    pass
        except ClientError as e:
            raise Exception(f"Failed to delete perk file: {str(e)}") 