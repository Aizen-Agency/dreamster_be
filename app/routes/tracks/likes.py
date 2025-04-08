from flask import Blueprint, jsonify, request
from app.extensions.extension import db
from app.models.track import Track
from app.models.track_like import TrackLike
from app.models.user import User
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

likes_bp = Blueprint('likes', __name__, url_prefix='/api/tracks')

@likes_bp.route('/<uuid:track_id>/like', methods=['POST'])
@jwt_required()
@handle_errors
def like_track(track_id):
    """Like a track"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    track = Track.query.get_or_404(track_id)
    
    # Check if user already liked this track
    existing_like = TrackLike.query.filter_by(
        user_id=user_id, 
        track_id=track_id
    ).first()
    
    if existing_like:
        return jsonify({
            'message': 'You have already liked this track',
            'liked': True
        }), HTTPStatus.OK
    
    # Create new like
    try:
        new_like = TrackLike(user_id=user_id, track_id=track_id)
        db.session.add(new_like)
        
        # Increment track like count
        track.increment_like_count()
        
        return jsonify({
            'message': 'Track liked successfully',
            'liked': True,
            'likes_count': track.likes
        }), HTTPStatus.CREATED
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'message': 'You have already liked this track',
            'liked': True
        }), HTTPStatus.OK

@likes_bp.route('/<uuid:track_id>/like', methods=['DELETE'])
@jwt_required()
@handle_errors
def unlike_track(track_id):
    """Unlike a track"""
    user_id = get_jwt_identity()
    track = Track.query.get_or_404(track_id)
    
    # Find the like
    like = TrackLike.query.filter_by(
        user_id=user_id, 
        track_id=track_id
    ).first()
    
    if not like:
        return jsonify({
            'message': 'You have not liked this track',
            'liked': False
        }), HTTPStatus.NOT_FOUND
    
    # Remove the like
    db.session.delete(like)
    
    # Decrement track like count
    track.decrement_like_count()
    
    return jsonify({
        'message': 'Track unliked successfully',
        'liked': False,
        'likes_count': track.likes
    }), HTTPStatus.OK

@likes_bp.route('/<uuid:track_id>/like/status', methods=['GET'])
@jwt_required()
@handle_errors
def check_like_status(track_id):
    """Check if user has liked a track"""
    user_id = get_jwt_identity()
    track = Track.query.get_or_404(track_id)
    
    # Check if user liked this track
    like_exists = TrackLike.query.filter_by(
        user_id=user_id, 
        track_id=track_id
    ).first() is not None
    
    return jsonify({
        'liked': like_exists,
        'likes_count': track.likes
    }), HTTPStatus.OK

@likes_bp.route('/liked', methods=['GET'])
@jwt_required()
@handle_errors
def get_liked_tracks():
    """Get all tracks liked by the current user"""
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get liked track IDs with pagination
    liked_tracks_pagination = TrackLike.query.filter_by(
        user_id=user_id
    ).order_by(
        TrackLike.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    # Get track details for each liked track
    tracks_data = []
    for like in liked_tracks_pagination.items:
        track = Track.query.get(like.track_id)
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
            'likes': track.likes,
            'created_at': track.created_at.isoformat(),
            'artwork_url': artwork_url,
            'liked_at': like.created_at.isoformat(),
            'exclusive': track.exclusive,
            'artist': {
                'id': str(artist.id),
                'name': artist.name if hasattr(artist, 'name') else artist.username,
                'username': artist.username
            }
        })
    
    return jsonify({
        'tracks': tracks_data,
        'total': liked_tracks_pagination.total,
        'pages': liked_tracks_pagination.pages,
        'current_page': page
    }), HTTPStatus.OK 