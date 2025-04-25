from flask import Blueprint, jsonify, request, send_file
from http import HTTPStatus
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions.extension import db
from app.models.user import User
from app.models.user_owned_track import UserOwnedTrack
from app.models.track import Track
from app.models.trackperk import TrackPerk, Category, PerkType
from app.routes.user.user_utils import handle_errors
from app.services.s3_service import S3Service
import os
import requests
from io import BytesIO
import uuid
import boto3

perks_bp = Blueprint('perks', __name__, url_prefix='/api/user/perks')

# Initialize the service
s3_service = S3Service(bucket_name=os.environ.get('AWS_S3_BUCKET', 'dreamster-tracks'))

@perks_bp.route('/', methods=['GET'])
@jwt_required()
@handle_errors
def get_all_perks():
    """Get all perks for tracks owned by the current user"""
    current_user = User.query.get(get_jwt_identity())
    print(current_user.id)
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Get all tracks owned by the user
    owned_tracks = UserOwnedTrack.query.filter_by(user_id=current_user.id).all()
    owned_track_ids = [owned.track_id for owned in owned_tracks]

    if not len(owned_track_ids) > 0:
        return jsonify({
            'perks': [],
            'count': 0
        }), HTTPStatus.OK
    
    # Get all artists whose tracks the user owns
    owned_artists = db.session.query(Track.artist_id).filter(
        Track.id.in_(owned_track_ids)
    ).distinct().all()
    owned_artist_ids = [artist[0] for artist in owned_artists]
    
    # Get all perks for the owned tracks
    perks_data = []
    
    # 1. Direct perks from owned tracks
    direct_perks = TrackPerk.query.filter(
        TrackPerk.track_id.in_(owned_track_ids),
        TrackPerk.active == True
    ).all()
    
    # 2. Exclusive perks from the same artists
    if owned_artist_ids:
        # Get all tracks from these artists
        artist_tracks = Track.query.filter(
            Track.artist_id.in_(owned_artist_ids),
            Track.approved == True
        ).all()
        
        artist_track_ids = [track.id for track in artist_tracks]
        
        # Get exclusive perks from these artists' tracks
        exclusive_perks = TrackPerk.query.filter(
            TrackPerk.track_id.in_(artist_track_ids),
            TrackPerk.category == Category.exclusive,
            TrackPerk.active == True
        ).all()
        
        # Add exclusive perks to the list
        direct_perks.extend(exclusive_perks)
    
    # Format perks data
    for perk in direct_perks:
        track = Track.query.get(perk.track_id)
        artist = User.query.get(track.artist_id)
        
        # Skip if track doesn't exist or isn't approved
        if not track or not track.approved:
            continue
            
        # Check if this is a direct perk or an exclusive perk
        is_direct = perk.track_id in owned_track_ids
        
        perks_data.append({
            'id': str(perk.id),
            'title': perk.title,
            'description': perk.description,
            'category': perk.category.name,
            'perk_type': perk.perk_type.name,
            's3_url': perk.s3_url,
            'track_id': str(perk.track_id),
            'track_title': track.title,
            'artist_id': str(track.artist_id),
            'artist_name': artist.username,
            'is_direct': is_direct,
            'created_at': perk.created_at.isoformat()
        })
    
    return jsonify({
        'perks': perks_data,
        'count': len(perks_data)
    }), HTTPStatus.OK

@perks_bp.route('/category/<category>', methods=['GET'])
@jwt_required()
@handle_errors
def get_perks_by_category(category):
    """Get perks by category for tracks owned by the current user"""
    try:
        category_enum = Category[category]
    except KeyError:
        return jsonify({
            'message': f'Invalid category: {category}. Valid options are: {[c.name for c in Category]}'
        }), HTTPStatus.BAD_REQUEST
    
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Get all tracks owned by the user
    owned_tracks = UserOwnedTrack.query.filter_by(user_id=current_user.id).all()
    owned_track_ids = [owned.track_id for owned in owned_tracks]
    
    if not len(owned_track_ids) > 0:
        return jsonify({
            'perks': [],
            'count': 0
        }), HTTPStatus.OK
    
    # Initialize perks_data list
    perks_data = []
    
    if category_enum == Category.exclusive:
        # For exclusive perks, we need to get all artists whose tracks the user owns
        owned_artists = db.session.query(Track.artist_id).filter(
            Track.id.in_(owned_track_ids)
        ).distinct().all()
        owned_artist_ids = [artist[0] for artist in owned_artists]
        
        if owned_artist_ids:
            # Get all tracks from these artists
            artist_tracks = Track.query.filter(
                Track.artist_id.in_(owned_artist_ids),
                Track.approved == True
            ).all()
            
            artist_track_ids = [track.id for track in artist_tracks]
            
            # Get exclusive perks from these artists' tracks
            perks = TrackPerk.query.filter(
                TrackPerk.track_id.in_(artist_track_ids),
                TrackPerk.category == Category.exclusive,
                TrackPerk.active == True
            ).all()
    else:
        # For other categories (stems, custom, discord), only get perks from owned tracks
        perks = TrackPerk.query.filter(
            TrackPerk.track_id.in_(owned_track_ids),
            TrackPerk.category == category_enum,
            TrackPerk.active == True
        ).all()

    # Format perks data
    for perk in perks:
        track = Track.query.get(perk.track_id)
        if not track or not track.approved:
            # Skip if track doesn't exist or isn't approved
            continue
            
        if s3_service:
            artwork_url = s3_service.get_file_url(track.id, is_artwork=True) if track.s3_url else None
        else:
            artwork_url = None

        artist = User.query.get(track.artist_id)
        
        # Check if this is a direct perk or an exclusive perk
        is_direct = perk.track_id in owned_track_ids
        
        perks_data.append({
            'id': str(perk.id),
            'title': perk.title,
            'description': perk.description,
            'category': perk.category.name,
            'perk_type': perk.perk_type.name,
            's3_url': perk.s3_url,
            'artwork_url': artwork_url if artwork_url else None,
            'track_id': str(perk.track_id),
            'track_title': track.title,
            'artist_id': str(track.artist_id),
            'artist_name': artist.username,
            'is_direct': is_direct,
            'created_at': perk.created_at.isoformat()
        })
    
    return jsonify({
        'perks': perks_data,
        'count': len(perks_data)
    }), HTTPStatus.OK

@perks_bp.route('/track/<uuid:track_id>', methods=['GET'])
@jwt_required()
@handle_errors
def get_perks_for_track(track_id):
    """Get all perks for a specific track owned by the current user"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Check if the user owns this track
    ownership = UserOwnedTrack.query.filter_by(
        user_id=current_user.id,
        track_id=track_id
    ).first()
    
    if not ownership:
        return jsonify({'message': 'You do not own this track'}), HTTPStatus.FORBIDDEN
    
    # Get all perks for this track
    perks = TrackPerk.query.filter_by(
        track_id=track_id,
        active=True
    ).all()
    
    # Format perks data
    perks_data = []
    for perk in perks:
        track = Track.query.get(perk.track_id)
        if s3_service:
            artwork_url = s3_service.get_file_url(track.id, is_artwork=True) if track.s3_url else None
        else:
            artwork_url = None
        artist = User.query.get(track.artist_id)
        
        perks_data.append({
            'id': str(perk.id),
            'title': perk.title,
            'description': perk.description,
            'category': perk.category.name,
            'perk_type': perk.perk_type.name,
            's3_url': perk.s3_url,
            'artwork_url': artwork_url if artwork_url else None,
            'track_id': str(perk.track_id),
            'track_title': track.title,
            'artist_id': str(track.artist_id),
            'artist_name': artist.username,
            'created_at': perk.created_at.isoformat()
        })
    
    return jsonify({
        'perks': perks_data,
        'count': len(perks_data)
    }), HTTPStatus.OK

@perks_bp.route('/download/<uuid:perk_id>', methods=['GET'])
@jwt_required()
@handle_errors
def download_perk(perk_id):
    """Download a perk file"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Get the perk
    perk = TrackPerk.query.get_or_404(perk_id)
    
    # Check if the user owns the track associated with this perk
    track_id = perk.track_id
    
    # For exclusive perks, check if the user owns any track from this artist
    if perk.category == Category.exclusive:
        track = Track.query.get(track_id)
        artist_id = track.artist_id
        
        # Check if user owns any track from this artist
        ownership = UserOwnedTrack.query.join(Track).filter(
            UserOwnedTrack.user_id == current_user.id,
            Track.artist_id == artist_id
        ).first()
    else:
        # For regular perks, check direct ownership
        ownership = UserOwnedTrack.query.filter_by(
            user_id=current_user.id,
            track_id=track_id
        ).first()
    
    if not ownership:
        return jsonify({'message': 'You do not have access to this perk'}), HTTPStatus.FORBIDDEN
    
    # For exclusive audio perks, we might need to get the track's s3_url
    if perk.category == Category.exclusive:
        track = Track.query.get(track_id)
        if track and track.s3_url:
            pass
        else:
            return jsonify({'message': 'No file available for this perk'}), HTTPStatus.NOT_FOUND
    # For other perk types, check if perk has a URL
    elif not perk.s3_url:
        return jsonify({'message': 'No file available for this perk'}), HTTPStatus.NOT_FOUND
    
    # For text or URL perks, just return the content
    if perk.category != Category.exclusive and (perk.perk_type == PerkType.text or perk.perk_type == PerkType.url):
        return jsonify({
            'content': perk.s3_url,
            'perk_type': perk.perk_type.name
        }), HTTPStatus.OK
    
    # For file perks, generate a pre-signed URL for download
    try:
        file_extension = '.mp3'  # Default extension
        
        # Special handling for exclusive audio perks
        if perk.category == Category.exclusive:
            # Get the track to access its audio file
            track = Track.query.get(track_id)
            if track and track.s3_url:
                # Extract the file extension from the S3 URL
                file_extension = os.path.splitext(track.s3_url)[1] if track.s3_url else '.mp3'
                file_key = f"{track_id}/audio{file_extension}"
                
                # Extract the bucket name from the S3 URL
                s3_url_parts = track.s3_url.split('/')
                bucket_name = s3_url_parts[2].split('.')[0]
                
                # Generate a pre-signed URL for the track's audio file
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.environ.get('AWS_REGION', 'eu-north-1')
                )
                
                download_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': file_key},
                    ExpiresIn=300  # 5 minutes
                )
            else:
                return jsonify({'message': 'Track audio file not found'}), HTTPStatus.NOT_FOUND
        else:
            # For regular perks, use the existing method
            download_url = s3_service.generate_presigned_url(perk.track_id, perk.id, perk.perk_type)
            
            # Extract file extension for regular perks
            if perk.s3_url:
                file_extension = os.path.splitext(perk.s3_url)[1] or file_extension
        
        return jsonify({
            'download_url': download_url,
            'filename': perk.title,
            'file_extension': file_extension,
            'perk_type': perk.perk_type.name,
            'expires_in': 300  # 5 minutes in seconds
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({'message': f'Error generating download URL: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR 