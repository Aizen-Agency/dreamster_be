from flask import Blueprint, request, jsonify
from app.extensions.extension import db
from app.models.track import Track, TrackStatus
from app.models.user import User, UserRole
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
from sqlalchemy import desc
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import uuid

public_tracks_bp = Blueprint('public_tracks', __name__, url_prefix='/api/tracks')

@public_tracks_bp.route('/', methods=['GET'])
@handle_errors
def get_tracks():
    """Get a paginated list of all tracks with basic metadata"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    genre = request.args.get('genre')
    sort_by = request.args.get('sort_by', 'created_at')
    
    # Check if the current user is an artist or admin
    is_artist = False
    is_admin = False
    current_user_id = None
    
    try:
        verify_jwt_in_request(optional=True)
        current_user_id = get_jwt_identity()
        if current_user_id:
            current_user = User.query.get(current_user_id)
            if current_user:
                is_artist = current_user.role == UserRole.musician
                is_admin = current_user.role == UserRole.admin
    except Exception:
        pass
    
    # Build query
    query = Track.query
    
    # Apply access rules:
    # 1. Admin can see all tracks
    # 2. Artist can see all approved tracks and their own tracks
    # 3. Regular users can only see approved and active tracks
    if not is_admin:
        if is_artist and current_user_id:
            # Artists can see their own tracks plus approved active tracks from others
            query = query.filter(
                (Track.artist_id == current_user_id) | 
                ((Track.approved == True) & (Track.status == TrackStatus.active))
            )
        else:
            # Regular users can only see approved and active tracks
            query = query.filter_by(approved=True, status=TrackStatus.active)
    
    # Apply filters
    if genre:
        query = query.filter(Track.genre == genre)
    
    # Apply sorting
    if sort_by == 'popular':
        query = query.order_by(desc(Track.stream_count))
    elif sort_by == 'newest':
        query = query.order_by(desc(Track.created_at))
    
    # Execute paginated query
    tracks_pagination = query.paginate(page=page, per_page=per_page)
    
    # Get artist information for each track
    tracks_data = []
    for track in tracks_pagination.items:
        artist = User.query.get(track.artist_id)
        
        # Generate artwork URL safely
        artwork_url = None
        if track.s3_url:
            # Extract the base URL from the audio URL and construct the artwork URL
            base_url_parts = track.s3_url.split('/audio')
            if len(base_url_parts) > 0:
                artwork_url = f"{base_url_parts[0]}/artwork.jpg"
        
        tracks_data.append({
            'id': str(track.id),
            'title': track.title,
            'description': track.description,
            'genre': track.genre.name if track.genre else None,
            'tags': track.tags,
            'starting_price': float(track.starting_price) if track.starting_price else 0,
            'duration': track.duration,
            'stream_count': track.stream_count,
            'likes': track.likes,
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'artist': {
                'id': str(artist.id),
                'name': artist.username,
                'username': artist.username
            }
        })
    
    return jsonify({
        'tracks': tracks_data,
        'total': tracks_pagination.total,
        'pages': tracks_pagination.pages,
        'current_page': page
    }), HTTPStatus.OK

@public_tracks_bp.route('/<uuid:track_id>', methods=['GET'])
@handle_errors
def get_track_details(track_id):
    """Get detailed information about a specific track"""
    track = Track.query.get_or_404(track_id)
    
    # Check if the current user is the artist or an admin
    is_artist = False
    is_admin = False
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            current_user = User.query.get(user_id)
            is_artist = current_user and str(track.artist_id) == str(current_user.id)
            is_admin = current_user and current_user.role == UserRole.admin
    except Exception:
        pass
    
    # If track is not approved and the user is not the artist or admin, return 404
    if not (track.approved and track.status == TrackStatus.active) and not (is_artist or is_admin):
        return jsonify({'message': 'Track not found or not available'}), HTTPStatus.NOT_FOUND
    
    artist = User.query.get(track.artist_id)
    
    # Increment view count
    track.views += 1
    db.session.commit()
    
    # Generate artwork URL safely
    artwork_url = None
    if track.s3_url:
        base_url_parts = track.s3_url.split('/audio')
        if len(base_url_parts) > 0:
            artwork_url = f"{base_url_parts[0]}/artwork.jpg"
    
    # Check if the current user has liked this track
    user_liked = False
    
    # Try to get the user identity, but don't require authentication
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            from app.models.track_like import TrackLike
            user_liked = TrackLike.query.filter_by(
                user_id=user_id, 
                track_id=track_id
            ).first() is not None
    except Exception:
        # If there's any error with the JWT, just assume the user is not authenticated
        pass
    
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
        'comments': track.comments,
        'views': track.views,
        'shares': track.shares,
        'created_at': track.created_at.isoformat(),
        'artwork_url': artwork_url,
        'user_liked': user_liked,
        'artist': {
            'id': str(artist.id),
            'name': artist.username,
            'username': artist.username
        }
    }), HTTPStatus.OK 

@public_tracks_bp.route('/artist/<uuid:artist_id>', methods=['GET'])
@handle_errors
def get_artist_tracks(artist_id):
    """Get a paginated list of all tracks by a specific artist"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    sort_by = request.args.get('sort_by', 'created_at')
    
    # Verify artist exists
    artist = User.query.get_or_404(artist_id)
    
    # Check if the current user is the artist or an admin
    is_artist = False
    is_admin = False
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            current_user = User.query.get(user_id)
            is_artist = current_user and current_user.role == UserRole.musician
            is_admin = current_user and current_user.role == UserRole.admin
    except Exception:
        pass
    
    # Build query for artist's tracks
    query = Track.query.filter_by(artist_id=artist_id)
    
    # If not the artist themselves or an admin, only show approved tracks
    if not (is_artist or is_admin):
        query = query.filter_by(approved=True, status=TrackStatus.active)
    
    # Apply sorting
    if sort_by == 'popular':
        query = query.order_by(desc(Track.stream_count))
    elif sort_by == 'newest':
        query = query.order_by(desc(Track.created_at))
    
    # Execute paginated query
    tracks_pagination = query.paginate(page=page, per_page=per_page)
    
    # Format track data
    tracks_data = []
    for track in tracks_pagination.items:
        # Generate artwork URL safely
        artwork_url = None
        if track.s3_url:
            base_url_parts = track.s3_url.split('/audio')
            if len(base_url_parts) > 0:
                artwork_url = f"{base_url_parts[0]}/artwork.jpg"
        
        tracks_data.append({
            'id': str(track.id),
            'title': track.title,
            'description': track.description,
            'genre': track.genre.name if track.genre else None,
            'tags': track.tags,
            'starting_price': float(track.starting_price) if track.starting_price else 0,
            'duration': track.duration,
            'stream_count': track.stream_count,
            'likes': track.likes,
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'status': track.status.name if track.status else None,
            'approved': track.approved
        })
    
    return jsonify({
        'artist': {
            'id': str(artist.id),
            'name': artist.username,
            'username': artist.username
        },
        'tracks': tracks_data,
        'total': tracks_pagination.total,
        'pages': tracks_pagination.pages,
        'current_page': page
    }), HTTPStatus.OK 