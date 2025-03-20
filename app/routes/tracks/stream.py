from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.extensions.extension import db
from app.models.track import Track
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import boto3
import os
from botocore.exceptions import ClientError

stream_bp = Blueprint('stream', __name__, url_prefix='/api/stream')

@stream_bp.route('/<uuid:track_id>', methods=['GET'])
@handle_errors
def stream_track(track_id):
    """Stream a track's audio file"""
    track = Track.query.get_or_404(track_id)
    
    # Increment stream count
    track.stream_count += 1
    db.session.commit()
    
    # Extract the bucket name and key from the S3 URL
    s3_url_parts = track.s3_url.split('/')
    bucket_name = s3_url_parts[2].split('.')[0]
    file_key = f"{track_id}/audio.mp3"  # Assuming mp3 format
    
    # Generate a pre-signed URL with a short expiration time (5 minutes)
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'eu-north-1')
    )
    
    try:
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
            'duration': track.duration
        }), HTTPStatus.OK
        
    except ClientError as e:
        return jsonify({'message': f"Error generating stream URL: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@stream_bp.route('/<uuid:track_id>/progress', methods=['POST'])
@handle_errors
def track_progress():
    """Record user's listening progress for analytics"""
    track_id = request.json.get('track_id')
    progress_seconds = request.json.get('progress')
    
    # Here you could implement logic to track user listening habits
    # For example, storing how much of each track users listen to
    
    return jsonify({'success': True}), HTTPStatus.OK 