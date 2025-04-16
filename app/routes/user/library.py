from flask import Blueprint, jsonify
from http import HTTPStatus
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions.extension import db
from app.models.user import User
from app.models.user_owned_track import UserOwnedTrack
from app.routes.user.user_utils import handle_errors

library_bp = Blueprint('library', __name__, url_prefix='/api/user/library')

@library_bp.route('/', methods=['GET'])
@jwt_required()
@handle_errors
def get_user_library():
    """Get all tracks owned by the current user"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Query user's owned tracks with related data
    owned_tracks = UserOwnedTrack.query.filter_by(user_id=current_user.id).all()
    
    # Format response
    library = []
    for owned in owned_tracks:
        track = owned.track
        artist = User.query.filter_by(id=track.artist_id).first()
        if track.s3_url:
            artwork_url = f"{track.s3_url.split('/audio')[0]}/artwork.jpg"
        else:
            artwork_url = ''

        library.append({
            'id': str(track.id),
            'title': track.title,
            'artist': artist.username if artist else '',
            'genre': track.genre.name if track.genre else None,
            's3_url': track.s3_url,
            'artwork_url': artwork_url,
            'purchase_date': owned.purchase_date.isoformat(),
            'exclusive': track.exclusive
        })
    
    return jsonify({
        'library': library,
        'count': len(library)
    }), HTTPStatus.OK

@library_bp.route('/transactions', methods=['GET'])
@jwt_required()
@handle_errors
def get_user_transactions():
    """Get all transactions for the current user"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Import Transaction model
    from app.models.transaction import Transaction
    
    # Query user's transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    
    # Format response
    transactions_list = []
    for tx in transactions:
        track = tx.track
        transactions_list.append({
            'id': str(tx.id),
            'track_id': str(track.id),
            'track_title': track.title,
            'artist': track.artist.username,
            'amount': float(tx.amount),
            'status': tx.status.name,
            'payment_id': tx.payment_id,
            'date': tx.created_at.isoformat(),
            'error': tx.error_message
        })
    
    return jsonify({
        'transactions': transactions_list,
        'count': len(transactions_list)
    }), HTTPStatus.OK

@library_bp.route('/owned-tracks', methods=['GET'])
@jwt_required()
@handle_errors
def get_owned_tracks():
    """Get all tracks owned by the current user"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Query user's owned tracks with related data
    owned_tracks = UserOwnedTrack.query.filter_by(user_id=current_user.id).all()
    
    # Format response
    owned_tracks_list = []
    for owned in owned_tracks:
        track = owned.track
        owned_tracks_list.append({
            'id': str(track.id),
            'title': track.title,
            'artist': track.artist.username,
            'genre': track.genre.name if track.genre else None,
            's3_url': track.s3_url,
            'artwork_url': track.s3_url.replace("audio", "artwork") if track.s3_url else None,
            'purchase_date': owned.purchase_date.isoformat(),
            'exclusive': track.exclusive
        })

    return jsonify({
        'owned_tracks': owned_tracks_list,
        'count': len(owned_tracks_list)
    }), HTTPStatus.OK

@library_bp.route('/owns/<uuid:track_id>', methods=['GET'])
@jwt_required()
@handle_errors
def check_track_ownership(track_id):
    """Check if the current user owns a specific track"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Check ownership
    ownership = UserOwnedTrack.query.filter_by(
        user_id=current_user.id,
        track_id=track_id
    ).first()
    
    if ownership:
        return jsonify({
            'owns': True,
            'purchase_date': ownership.purchase_date.isoformat()
        }), HTTPStatus.OK
    
    return jsonify({'owns': False}), HTTPStatus.OK 