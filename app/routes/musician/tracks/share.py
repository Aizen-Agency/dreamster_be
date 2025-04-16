from flask import Blueprint, jsonify, request
from app.extensions.extension import db
from app.models.track import Track, TrackStatus
from app.models.user import User
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import boto3
import os
from botocore.exceptions import ClientError
from app.services.s3_service import S3Service

share_bp = Blueprint('share', __name__, url_prefix='/api/tracks/share')

# Initialize the service
s3_service = S3Service(bucket_name=os.environ.get('AWS_S3_BUCKET', 'dreamster-tracks'))

@share_bp.route('/<uuid:track_id>', methods=['GET'])
@handle_errors
def get_shared_track(track_id):
    """Get track details for a shared track (accessible without authentication)"""
    track = Track.query.get_or_404(track_id)
    
    # Only approved and active tracks can be shared publicly
    if not (track.approved and track.status == TrackStatus.active):
        return jsonify({'message': 'Track not found or not available'}), HTTPStatus.NOT_FOUND
    
    # Get artist information
    artist = User.query.get(track.artist_id)
    
    # Increment share count
    track.shares += 1
    db.session.commit()
    
    # Generate artwork URL safely
    artwork_url = s3_service.get_file_url(track.id, is_artwork=True) if track.s3_url else None
    
    return jsonify({
        'id': str(track.id),
        'title': track.title,
        'description': track.description,
        'genre': track.genre.name if track.genre else None,
        'tags': track.tags,
        'starting_price': float(track.starting_price) if track.starting_price else 0,
        'duration': track.duration,
        'stream_count': track.stream_count,
        'likes': track.likes,
        'shares': track.shares,
        'created_at': track.created_at.isoformat(),
        'artwork_url': artwork_url,
        'exclusive': track.exclusive,
        'artist': {
            'id': str(artist.id),
            'name': artist.username,
            'username': artist.username
        }
    }), HTTPStatus.OK

@share_bp.route('/<uuid:track_id>/stream', methods=['GET'])
@handle_errors
def stream_shared_track(track_id):
    """Stream a shared track's audio file (accessible without authentication)"""
    track = Track.query.get_or_404(track_id)
    
    # Only approved and active tracks can be streamed publicly
    if not (track.approved and track.status == TrackStatus.active):
        return jsonify({'message': 'Track not found or not available for streaming'}), HTTPStatus.NOT_FOUND
    
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

@share_bp.route('/<uuid:track_id>/record-share', methods=['POST'])
@handle_errors
def record_share(track_id):
    """Record when a track is shared on social media or via link"""
    track = Track.query.get_or_404(track_id)
    
    # Only approved and active tracks can be shared
    if not (track.approved and track.status == TrackStatus.active):
        return jsonify({'message': 'Track not found or not available'}), HTTPStatus.NOT_FOUND
    
    # Get share platform if provided
    platform = request.json.get('platform', 'link')  # Default to 'link' if not specified
    
    # Increment share count
    track.shares += 1
    db.session.commit()
    
    return jsonify({
        'message': f'Track share on {platform} recorded successfully',
        'shares': track.shares
    }), HTTPStatus.OK