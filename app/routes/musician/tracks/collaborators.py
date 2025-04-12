from flask import Blueprint, request, jsonify
from app.middleware.musician_auth import musician_required
from app.extensions.extension import db
from app.models.track import Track
from app.models.user import User
from app.models.collaborator import Collaborator
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import uuid

collaborators_bp = Blueprint('collaborators', __name__, url_prefix='/api/musician/tracks')

@collaborators_bp.route('/<uuid:track_id>/collaborators', methods=['GET'])
@musician_required
@handle_errors
def get_collaborators(current_user, track_id):
    """Get all collaborators for a track"""
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get all collaborators for the track
    collaborators = Collaborator.query.filter_by(track_id=track_id).all()
    
    # Format response
    collaborators_data = [{
        'id': str(collab.id),
        'user_id': str(collab.user_id),
        'username': collab.user.username,
        'split_share': float(collab.split_share),
        'wallet_address': collab.wallet_address,
        'created_at': collab.created_at.isoformat()
    } for collab in collaborators]
    
    return jsonify(collaborators_data), HTTPStatus.OK

@collaborators_bp.route('/<uuid:track_id>/collaborators', methods=['POST'])
@musician_required
@handle_errors
def add_collaborator(current_user, track_id):
    """Add a new collaborator to a track"""
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Validate input
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
    
    if 'user_id' not in data or 'split_share' not in data:
        return jsonify({'message': 'User ID and split share are required'}), HTTPStatus.BAD_REQUEST
    
    try:
        # Convert string ID to UUID if needed
        user_id = uuid.UUID(data['user_id']) if isinstance(data['user_id'], str) else data['user_id']
        
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
        
        # Validate split_share is a number between 0 and 100
        split_share = float(data['split_share'])
        if split_share <= 0 or split_share > 100:
            return jsonify({'message': 'Split share must be between 0 and 100'}), HTTPStatus.BAD_REQUEST
        
        # Check if collaborator already exists
        existing_collab = Collaborator.query.filter_by(
            track_id=track_id,
            user_id=user_id
        ).first()
        
        if existing_collab:
            return jsonify({'message': 'Collaborator already exists for this track'}), HTTPStatus.CONFLICT
        
        # Create new collaborator
        new_collab = Collaborator(
            track_id=track_id,
            user_id=user_id,
            split_share=split_share,
            wallet_address=data.get('wallet_address')
        )
        
        db.session.add(new_collab)
        db.session.commit()
        
        return jsonify({
            'message': 'Collaborator added successfully',
            'collaborator': {
                'id': str(new_collab.id),
                'user_id': str(new_collab.user_id),
                'username': user.username,
                'split_share': float(new_collab.split_share),
                'wallet_address': new_collab.wallet_address,
                'created_at': new_collab.created_at.isoformat()
            }
        }), HTTPStatus.CREATED
        
    except (ValueError, TypeError):
        return jsonify({'message': 'Invalid data format'}), HTTPStatus.BAD_REQUEST

@collaborators_bp.route('/<uuid:track_id>/collaborators/<uuid:collaborator_id>', methods=['PUT'])
@musician_required
@handle_errors
def update_collaborator(current_user, track_id, collaborator_id):
    """Update an existing collaborator"""
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get the collaborator
    collaborator = Collaborator.query.filter_by(id=collaborator_id, track_id=track_id).first()
    if not collaborator:
        return jsonify({'message': 'Collaborator not found'}), HTTPStatus.NOT_FOUND
    
    # Validate input
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
    
    # Update fields
    if 'split_share' in data:
        try:
            split_share = float(data['split_share'])
            if split_share <= 0 or split_share > 100:
                return jsonify({'message': 'Split share must be between 0 and 100'}), HTTPStatus.BAD_REQUEST
            collaborator.split_share = split_share
        except (ValueError, TypeError):
            return jsonify({'message': 'Invalid split share format'}), HTTPStatus.BAD_REQUEST
    
    if 'wallet_address' in data:
        collaborator.wallet_address = data['wallet_address']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Collaborator updated successfully',
        'collaborator': {
            'id': str(collaborator.id),
            'user_id': str(collaborator.user_id),
            'username': collaborator.user.username,
            'split_share': float(collaborator.split_share),
            'wallet_address': collaborator.wallet_address,
            'updated_at': collaborator.updated_at.isoformat()
        }
    }), HTTPStatus.OK

@collaborators_bp.route('/<uuid:track_id>/collaborators/<uuid:collaborator_id>', methods=['DELETE'])
@musician_required
@handle_errors
def delete_collaborator(current_user, track_id, collaborator_id):
    """Delete a collaborator from a track"""
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get the collaborator
    collaborator = Collaborator.query.filter_by(id=collaborator_id, track_id=track_id).first()
    if not collaborator:
        return jsonify({'message': 'Collaborator not found'}), HTTPStatus.NOT_FOUND
    
    # Delete the collaborator
    db.session.delete(collaborator)
    db.session.commit()
    
    return jsonify({
        'message': 'Collaborator removed successfully'
    }), HTTPStatus.OK 