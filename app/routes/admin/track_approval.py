from flask import Blueprint, jsonify, request
from app.middleware.admin_auth import admin_required
from app.extensions.extension import db
from app.models.track import Track, TrackStatus
from app.models.user import User
from app.routes.user.user_utils import handle_errors
from http import HTTPStatus
from sqlalchemy import desc
from datetime import datetime
from app.services.s3_service import S3Service
import os

track_approval_bp = Blueprint('track_approval', __name__, url_prefix='/api/admin/tracks')

# Initialize the service
s3_service = S3Service(bucket_name=os.environ.get('AWS_S3_BUCKET', 'dreamster-tracks'))

@track_approval_bp.route('/pending', methods=['GET'])
@admin_required
@handle_errors
def get_pending_tracks(current_user):
    """Get a paginated list of tracks pending approval"""
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
        artwork_url = s3_service.get_file_url(track.id, is_artwork=True) if track.s3_url else None
        
        tracks_data.append({
            'id': str(track.id),
            'title': track.title,
            'description': track.description,
            'genre': track.genre.name if track.genre else None,
            'tags': track.tags,
            'starting_price': float(track.starting_price) if track.starting_price else 0,
            'duration': track.duration,
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

@track_approval_bp.route('/<uuid:track_id>/approve', methods=['POST'])
@admin_required
@handle_errors
def approve_track(current_user, track_id):
    """Approve a track for public visibility"""
    track = Track.query.get_or_404(track_id)
    
    # Check if track is already approved
    if track.approved and track.status == 'active':
        return jsonify({
            'message': 'Track is already approved'
        }), HTTPStatus.BAD_REQUEST
    
    # Approve the track
    track.approved = True
    track.status = TrackStatus.active
    track.rejection_reason = None
    track.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Track approved successfully',
        'track_id': str(track.id),
        'status': track.status.name,
        'approved': track.approved
    }), HTTPStatus.OK

@track_approval_bp.route('/<uuid:track_id>/reject', methods=['POST'])
@admin_required
@handle_errors
def reject_track(current_user, track_id):
    """Reject a track with a reason"""
    data = request.get_json()
    rejection_reason = data.get('rejection_reason', '')
    
    track = Track.query.get_or_404(track_id)
    
    # Check if track is already rejected
    if track.status == 'rejected':
        return jsonify({
            'message': 'Track is already rejected'
        }), HTTPStatus.BAD_REQUEST
    
    # Reject the track
    track.approved = False
    track.status = TrackStatus.rejected
    track.rejection_reason = rejection_reason
    track.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Track rejected successfully',
        'track_id': str(track.id),
        'status': track.status.name,
        'approved': track.approved,
        'rejection_reason': track.rejection_reason
    }), HTTPStatus.OK

@track_approval_bp.route('/stats', methods=['GET'])
@admin_required
@handle_errors
def get_approval_stats(current_user):
    """Get statistics about track approvals"""
    pending_count = Track.query.filter_by(status=TrackStatus.pending).count()
    approved_count = Track.query.filter_by(status=TrackStatus.active).count()
    rejected_count = Track.query.filter_by(status=TrackStatus.rejected).count()
    total_count = Track.query.count()
    
    # Calculate approval rate
    approval_rate = (approved_count / total_count * 100) if total_count > 0 else 0
    
    return jsonify({
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
        'approval_rate': round(approval_rate, 2)
    }), HTTPStatus.OK 