from flask import Blueprint, request, jsonify
from app.middleware.musician_auth import musician_required
from app.extensions.extension import db
from app.models.track import Track, Genre, TrackStatus
from app.services.s3_service import S3Service
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import uuid
import json
from app.models.trackperk import TrackPerk
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

tracks_bp = Blueprint('tracks', __name__, url_prefix='/api/musician/tracks')
s3_service = S3Service(bucket_name='dreamster-tracks')

@tracks_bp.route('/', methods=['POST'])
@musician_required
@handle_errors
def upload_track(current_user):
    try:
        # Validate and process input
        title = request.form.get('title')
        if not title:
            return jsonify({'message': 'Title is required'}), HTTPStatus.BAD_REQUEST

        # Process genre - convert string to enum
        genre_str = request.form.get('genre')
        genre = None
        if genre_str:
            try:
                genre = Genre[genre_str]  # Convert string to enum
            except KeyError:
                return jsonify({'message': f'Invalid genre: {genre_str}. Valid options are: {[g.name for g in Genre]}'}), HTTPStatus.BAD_REQUEST

        # Process tags - ensure proper JSON format
        tags_str = request.form.get('tags')
        tags = None
        if tags_str:
            try:
                # If tags is already a string representation of JSON
                if isinstance(tags_str, str):
                    tags = json.loads(tags_str)
            except json.JSONDecodeError:
                return jsonify({'message': 'Invalid JSON format for tags'}), HTTPStatus.BAD_REQUEST

        # Generate track ID
        track_id = uuid.uuid4()

        # Save metadata to database
        track = Track(
            id=track_id,
            title=title,
            description=request.form.get('description'),
            genre=genre,
            tags=tags,
            starting_price=request.form.get('starting_price', 0),
            artist_id=current_user.id,
            approved=False,
            status='pending'
        )
        db.session.add(track)
        db.session.commit()

        # Upload files to S3
        audio_file = request.files.get('audio')
        artwork_file = request.files.get('artwork')
        if audio_file:
            track.s3_url = s3_service.upload_file(audio_file, track_id, is_artwork=False)
        if artwork_file:
            s3_service.upload_file(artwork_file, track_id, is_artwork=True)

        db.session.commit()

        # Return success response
        return jsonify({
            'message': 'Track uploaded successfully and pending approval',
            'track': {
                'id': str(track.id),
                'title': track.title,
                's3_url': track.s3_url,
                'status': track.status.name,
                'approved': track.approved
            }
        }), HTTPStatus.CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error uploading track: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR
        
@tracks_bp.route('/', methods=['GET'])
@musician_required
@handle_errors
def list_tracks(current_user):
    tracks = Track.query.filter_by(artist_id=current_user.id).all()
    return jsonify([{
        'id': track.id,
        'title': track.title,
        's3_url': track.s3_url
    } for track in tracks]), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>', methods=['GET'])
@musician_required
@handle_errors
def get_track_details(current_user, track_id):
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    return jsonify({
        'id': track.id,
        'title': track.title,
        'description': track.description,
        'genre': track.genre.name if track.genre else None,
        'tags': track.tags,
        'starting_price': track.starting_price,
        'created_at': track.created_at.isoformat(),
        'updated_at': track.updated_at.isoformat(),
        's3_url': track.s3_url
    }), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>', methods=['PUT'])
@musician_required
@handle_errors
def update_track(current_user, track_id):
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND

    # Validate and update track metadata
    if 'title' in request.json:
        track.title = request.json.get('title')
    
    if 'description' in request.json:
        track.description = request.json.get('description')
    
    # Process genre - convert string to enum
    if 'genre' in request.json:
        genre_str = request.json.get('genre')
        if genre_str:
            try:
                track.genre = Genre[genre_str]  # Convert string to enum
            except KeyError:
                return jsonify({'message': f'Invalid genre: {genre_str}. Valid options are: {[g.name for g in Genre]}'}), HTTPStatus.BAD_REQUEST
    
    # Process tags - ensure proper JSON format
    if 'tags' in request.json:
        tags_str = request.json.get('tags')
        if tags_str:
            try:
                # If tags is already a string representation of JSON
                if isinstance(tags_str, str):
                    track.tags = json.loads(tags_str)
            except json.JSONDecodeError:
                return jsonify({'message': 'Invalid JSON format for tags'}), HTTPStatus.BAD_REQUEST
    
    if 'starting_price' in request.json:
        try:
            price_value = request.json.get('starting_price')
            if price_value:
                track.starting_price = float(price_value)
        except ValueError:
            return jsonify({'message': 'Invalid starting price format'}), HTTPStatus.BAD_REQUEST

    db.session.commit()
    
    # Return the updated track data
    return jsonify({
        'message': 'Track updated successfully',
        'track': {
            'id': track.id,
            'title': track.title,
            'description': track.description,
            'genre': track.genre.name if track.genre else None,
            'tags': track.tags,
            'starting_price': float(track.starting_price) if track.starting_price else 0,
            's3_url': track.s3_url
        }
    }), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>', methods=['DELETE'])
@musician_required
@handle_errors
def delete_track(current_user, track_id):
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND

    # Delete track from database and S3
    s3_service.delete_file(track_id, is_artwork=False)
    s3_service.delete_file(track_id, is_artwork=True)
    db.session.delete(track)
    db.session.commit()

    return jsonify({'message': 'Track deleted successfully'}), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/perks', methods=['POST'])
@musician_required
@handle_errors
def create_track_perk(current_user, track_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Validate input
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'message': 'Title is required'}), HTTPStatus.BAD_REQUEST
    
    # Create new perk
    perk = TrackPerk(
        title=data.get('title'),
        description=data.get('description'),
        url=data.get('url'),
        track_id=track_id,
        active=data.get('active', False)
    )
    
    db.session.add(perk)
    db.session.commit()
    
    return jsonify({
        'message': 'Track perk created successfully',
        'perk': {
            'id': perk.id,
            'title': perk.title,
            'description': perk.description,
            'url': perk.url,
            'active': perk.active,
            'created_at': perk.created_at.isoformat(),
            'track_id': perk.track_id
        }
    }), HTTPStatus.CREATED

@tracks_bp.route('/<uuid:track_id>/perks', methods=['GET'])
@musician_required
@handle_errors
def list_track_perks(current_user, track_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get all perks for the track
    perks = TrackPerk.query.filter_by(track_id=track_id).all()
    
    return jsonify([{
        'id': perk.id,
        'title': perk.title,
        'description': perk.description,
        'url': perk.url,
        'active': perk.active,
        'created_at': perk.created_at.isoformat(),
        'updated_at': perk.updated_at.isoformat(),
    } for perk in perks]), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/perks/<uuid:perk_id>', methods=['GET'])
@musician_required
@handle_errors
def get_track_perk(current_user, track_id, perk_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get the specific perk
    perk = TrackPerk.query.filter_by(id=perk_id, track_id=track_id).first()
    if not perk:
        return jsonify({'message': 'Perk not found'}), HTTPStatus.NOT_FOUND
    
    return jsonify({
        'id': perk.id,
        'title': perk.title,
        'description': perk.description,
        'url': perk.url,
        'active': perk.active,
        'created_at': perk.created_at.isoformat(),
        'updated_at': perk.updated_at.isoformat(),
        'track_id': perk.track_id
    }), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/perks/<uuid:perk_id>', methods=['PUT'])
@musician_required
@handle_errors
def update_track_perk(current_user, track_id, perk_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get the specific perk
    perk = TrackPerk.query.filter_by(id=perk_id, track_id=track_id).first()
    if not perk:
        return jsonify({'message': 'Perk not found'}), HTTPStatus.NOT_FOUND
    
    # Update perk fields
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
    
    if 'title' in data:
        perk.title = data['title']
    if 'description' in data:
        perk.description = data['description']
    if 'url' in data:
        perk.url = data['url']
    if 'active' in data:
        perk.active = data['active']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Track perk updated successfully',
        'perk': {
            'id': perk.id,
            'title': perk.title,
            'description': perk.description,
            'url': perk.url,
            'active': perk.active,
            'updated_at': perk.updated_at.isoformat(),
            'track_id': perk.track_id
        }
    }), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/perks/<uuid:perk_id>', methods=['DELETE'])
@musician_required
@handle_errors
def delete_track_perk(current_user, track_id, perk_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get the specific perk
    perk = TrackPerk.query.filter_by(id=perk_id, track_id=track_id).first()
    if not perk:
        return jsonify({'message': 'Perk not found'}), HTTPStatus.NOT_FOUND
    
    # Delete the perk
    db.session.delete(perk)
    db.session.commit()
    
    return jsonify({'message': 'Track perk deleted successfully'}), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/perks/toggle/<uuid:perk_id>', methods=['PATCH'])
@musician_required
@handle_errors
def toggle_perk_status(current_user, track_id, perk_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Get the specific perk
    perk = TrackPerk.query.filter_by(id=perk_id, track_id=track_id).first()
    if not perk:
        return jsonify({'message': 'Perk not found'}), HTTPStatus.NOT_FOUND
    
    # Toggle active status
    perk.active = not perk.active
    db.session.commit()
    
    return jsonify({
        'message': f'Perk {"activated" if perk.active else "deactivated"} successfully',
        'active': perk.active
    }), HTTPStatus.OK 