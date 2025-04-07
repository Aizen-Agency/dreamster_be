from flask import Blueprint, jsonify, request
from app.middleware.admin_auth import admin_required
from app.extensions.extension import db
from app.models.track import Track, TrackStatus
from app.models.user import User
from app.routes.user.user_utils import handle_errors
from http import HTTPStatus
from sqlalchemy import desc

track_management_bp = Blueprint('track_management', __name__, url_prefix='/api/admin/tracks')

@track_management_bp.route('/', methods=['GET'])
@admin_required
@handle_errors
def get_all_tracks(current_user):
    """Get a paginated list of all tracks for admin"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query all tracks
    query = Track.query
    
    # Sort by newest first
    query = query.order_by(desc(Track.created_at))
    
    # Execute paginated query
    tracks_pagination = query.paginate(page=page, per_page=per_page)
    
    # Format track data with artist information
    tracks_data = []
    for track in tracks_pagination.items:
        artist = User.query.get(track.artist_id)
        
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
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'status': track.status.name if track.status else None,
            'approved': track.approved,
            'rejection_reason': track.rejection_reason,
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

@track_management_bp.route('/pending', methods=['GET'])
@admin_required
@handle_errors
def get_pending_tracks(current_user):
    """Get a paginated list of tracks with pending status"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query tracks with pending status
    query = Track.query.filter_by(status=TrackStatus.pending)
    
    # Sort by newest first
    query = query.order_by(desc(Track.created_at))
    
    # Execute paginated query
    tracks_pagination = query.paginate(page=page, per_page=per_page)
    
    # Format track data with artist information
    tracks_data = []
    for track in tracks_pagination.items:
        artist = User.query.get(track.artist_id)
        
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
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'status': track.status.name,
            'approved': track.approved,
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

@track_management_bp.route('/approved', methods=['GET'])
@admin_required
@handle_errors
def get_approved_tracks(current_user):
    """Get a paginated list of approved tracks"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query approved tracks
    query = Track.query.filter_by(status=TrackStatus.active, approved=True)
    
    # Sort by newest first
    query = query.order_by(desc(Track.created_at))
    
    # Execute paginated query
    tracks_pagination = query.paginate(page=page, per_page=per_page)
    
    # Format track data with artist information
    tracks_data = []
    for track in tracks_pagination.items:
        artist = User.query.get(track.artist_id)
        
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
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'status': track.status.name,
            'approved': track.approved,
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

@track_management_bp.route('/rejected', methods=['GET'])
@admin_required
@handle_errors
def get_rejected_tracks(current_user):
    """Get a paginated list of rejected tracks"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query rejected tracks
    query = Track.query.filter_by(status=TrackStatus.rejected)
    
    # Sort by newest first
    query = query.order_by(desc(Track.created_at))
    
    # Execute paginated query
    tracks_pagination = query.paginate(page=page, per_page=per_page)
    
    # Format track data with artist information
    tracks_data = []
    for track in tracks_pagination.items:
        artist = User.query.get(track.artist_id)
        
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
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'status': track.status.name,
            'approved': track.approved,
            'rejection_reason': track.rejection_reason,
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