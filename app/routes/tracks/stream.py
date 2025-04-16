from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.extensions.extension import db
from app.models.track import Track, TrackStatus
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import boto3
import os
from botocore.exceptions import ClientError
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User, UserRole
from flask_jwt_extended import jwt_required

stream_bp = Blueprint('stream', __name__, url_prefix='/api/stream')

@stream_bp.route('/<uuid:track_id>', methods=['GET'])
@jwt_required()
@handle_errors
def stream_track(track_id):
    """Stream a track's audio file"""
    track = Track.query.get_or_404(track_id)
    
    # Check if the track is approved or if the user is the artist or admin
    current_user = User.query.get(get_jwt_identity())
    
    is_artist = str(track.artist_id) == str(current_user.id)
    is_admin = current_user.role == UserRole.admin
    
    # If track is not approved and the user is not the artist or admin, return 404
    if not (track.approved and track.status == TrackStatus.active) and not (is_artist or is_admin):
        return jsonify({'message': 'Track not found or not available for streaming'}), HTTPStatus.NOT_FOUND
    
    # Increment stream count
    track.stream_count += 1
    db.session.commit()
    
    # Extract the file extension from the S3 URL
    file_extension = os.path.splitext(track.s3_url)[1] if track.s3_url else '.mp3'
    file_key = f"{track_id}/audio{file_extension}"
    
    # Extract the bucket name and key from the S3 URL
    s3_url_parts = track.s3_url.split('/')
    bucket_name = s3_url_parts[2].split('.')[0]
    
    # Generate a pre-signed URL with a short expiration time (5 minutes)
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'eu-north-1')
    )
    
    try:
        # Get file metadata from S3
        file_metadata = s3_client.head_object(
            Bucket=bucket_name,
            Key=file_key
        )
        
        # Extract file size in bytes and convert to MB
        file_size_bytes = file_metadata.get('ContentLength', 0)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
        
        # Get content type and extract format
        content_type = file_metadata.get('ContentType', 'audio/mpeg')
        file_format = 'MP3/320kbps'  # Default assumption
        
        # Check if we have more specific format info in metadata
        if 'Metadata' in file_metadata and 'format' in file_metadata['Metadata']:
            file_format = file_metadata['Metadata']['format']
        
        # Generate a pre-signed URL for the S3 object
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': file_key},
            ExpiresIn=300  # URL expires in 5 minutes
        )
        
        # Return the pre-signed URL to the client
        return jsonify({
            'stream_url': presigned_url,
            'track_id': str(track_id),
            'duration': track.duration,
            'file_format': file_format,
            'file_size_mb': file_size_mb,
            'content_type': content_type
        }), HTTPStatus.OK
        
    except ClientError as e:
        return jsonify({'message': f'Error generating streaming URL: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@stream_bp.route('/<uuid:track_id>/progress', methods=['POST'])
@handle_errors
def track_progress():
    """Record user's listening progress for analytics"""
    track_id = request.json.get('track_id')
    progress_seconds = request.json.get('progress')
    
    # Here you could implement logic to track user listening habits
    # For example, storing how much of each track users listen to
    
    return jsonify({'success': True}), HTTPStatus.OK 