from flask import Blueprint, request, jsonify, make_response
from app.middleware.musician_auth import musician_required
from app.extensions.extension import db
from app.models.track import Track, Genre, TrackStatus
from app.services.s3_service import S3Service
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import uuid
import json
from app.models.trackperk import TrackPerk, PerkType
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import os
import mimetypes
from botocore.exceptions import NoCredentialsError, ClientError

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

        # Process exclusive flag
        exclusive = request.form.get('exclusive', 'false').lower() == 'true'

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
            status='pending',
            exclusive=exclusive
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
                'approved': track.approved,
                'exclusive': track.exclusive
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
    
    if 'exclusive' in request.json:
        track.exclusive = bool(request.json.get('exclusive'))

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
            's3_url': track.s3_url,
            'exclusive': track.exclusive
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
        s3_url=data.get('url'),
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
            's3_url': perk.s3_url,
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
        's3_url': perk.s3_url,
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
        's3_url': perk.s3_url,
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
    if 's3_url' in data:
        perk.s3_url = data['s3_url']
    if 'active' in data:
        perk.active = data['active']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Track perk updated successfully',
        'perk': {
            'id': perk.id,
            'title': perk.title,
            'description': perk.description,
            's3_url': perk.s3_url,
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

@tracks_bp.route('/<uuid:track_id>/perks/bulk', methods=['POST'])
@musician_required
@handle_errors
def bulk_update_perks(current_user, track_id):
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Process each perk in the request
    perks_data = []
    
    # Check if it's a multipart form (file uploads) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Parse the perks JSON from the form
        perks_json = request.form.get('perks')
        if not perks_json:
            return jsonify({'message': 'No perks data provided'}), HTTPStatus.BAD_REQUEST
        
        try:
            perks_data = json.loads(perks_json)
        except json.JSONDecodeError:
            return jsonify({'message': 'Invalid JSON format for perks'}), HTTPStatus.BAD_REQUEST
        
        # Process each perk
        updated_perks = []
        for perk_data in perks_data:
            perk_id = perk_data.get('id')
            
            # If perk has an ID, update existing perk
            if perk_id:
                perk = TrackPerk.query.filter_by(id=perk_id, track_id=track_id).first()
                if not perk:
                    continue  # Skip if perk not found
                
                # Update perk fields
                if 'title' in perk_data:
                    perk.title = perk_data['title']
                if 'description' in perk_data:
                    perk.description = perk_data['description']
                if 's3_url' in perk_data:
                    perk.s3_url = perk_data['s3_url']
                if 'active' in perk_data:
                    perk.active = perk_data['active']
                if 'perk_type' in perk_data:
                    try:
                        perk.perk_type = PerkType[perk_data['perk_type']]
                    except KeyError:
                        continue  # Skip invalid perk type
                
                # Check if there are multiple files for this perk
                file_keys = [k for k in request.files.keys() if k.startswith(f"file_{perk_id}_")]
                
                if file_keys:
                    # Handle multiple files
                    if not perk.additional_urls:
                        perk.additional_urls = {}
                    
                    for i, file_key in enumerate(file_keys):
                        file = request.files[file_key]
                        if file and perk.perk_type in [PerkType.file, PerkType.audio]:
                            # Upload new file with index
                            is_audio = perk.perk_type == PerkType.audio
                            file_url = s3_service.upload_perk_file(
                                file, track_id, perk_id, is_audio=is_audio, file_index=i
                            )
                            
                            # Store the URL in the appropriate place
                            if i == 0 and not perk.s3_url:
                                perk.s3_url = file_url
                            else:
                                perk.additional_urls[f"file_{i}"] = file_url
                else:
                    # Check for single file (original implementation)
                    file_key = f"file_{perk_id}"
                    if file_key in request.files:
                        file = request.files[file_key]
                        if file and perk.perk_type in [PerkType.file, PerkType.audio]:
                            # Delete old file if it exists
                            if perk.s3_url:
                                s3_service.delete_perk_file(track_id, perk_id, is_audio=(perk.perk_type == PerkType.audio))
                            
                            # Upload new file
                            is_audio = perk.perk_type == PerkType.audio
                            perk.s3_url = s3_service.upload_perk_file(file, track_id, perk_id, is_audio=is_audio)
            else:
                # Create new perk
                try:
                    perk_type = PerkType[perk_data.get('perk_type', 'text')]
                except KeyError:
                    perk_type = PerkType.text
                
                perk = TrackPerk(
                    title=perk_data.get('title', 'New Perk'),
                    description=perk_data.get('description'),
                    s3_url=perk_data.get('s3_url'),
                    track_id=track_id,
                    active=perk_data.get('active', False),
                    perk_type=perk_type,
                    additional_urls={}
                )
                
                db.session.add(perk)
                db.session.flush()  # Get the ID without committing
                
                # Check for multiple files for new perk
                temp_id = perk_data.get('temp_id')
                if temp_id:
                    file_keys = [k for k in request.files.keys() if k.startswith(f"file_{temp_id}_")]
                    
                    if file_keys:
                        for i, file_key in enumerate(file_keys):
                            file = request.files[file_key]
                            if file and perk.perk_type in [PerkType.file, PerkType.audio]:
                                # Upload new file with index
                                is_audio = perk.perk_type == PerkType.audio
                                file_url = s3_service.upload_perk_file(
                                    file, track_id, perk.id, is_audio=is_audio, file_index=i
                                )
                                
                                # Store the URL in the appropriate place
                                if i == 0:
                                    perk.s3_url = file_url
                                else:
                                    perk.additional_urls[f"file_{i}"] = file_url
                    else:
                        # Check for single file
                        file_key = f"file_{temp_id}"
                        if file_key in request.files:
                            file = request.files[file_key]
                            if file and perk.perk_type in [PerkType.file, PerkType.audio]:
                                # Upload new file
                                is_audio = perk.perk_type == PerkType.audio
                                perk.s3_url = s3_service.upload_perk_file(file, track_id, perk.id, is_audio=is_audio)
            
            # Prepare response with all URLs
            perk_response = {
                'id': str(perk.id),
                'title': perk.title,
                'description': perk.description,
                's3_url': perk.s3_url,
                'active': perk.active,
                'perk_type': perk.perk_type.name,
                'temp_id': perk_data.get('temp_id')  # Return temp_id for frontend reference
            }
            
            # Add additional URLs if they exist
            if perk.additional_urls:
                perk_response['additional_urls'] = perk.additional_urls
                
            updated_perks.append(perk_response)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Perks updated successfully',
            'perks': updated_perks
        }), HTTPStatus.OK
    else:
        data = request.get_json()
        if not data or 'perks' not in data:
            return jsonify({'message': 'No perks data provided'}), HTTPStatus.BAD_REQUEST
        
        perks_data = data['perks']
        
        # Process each perk
        updated_perks = []
        for perk_data in perks_data:
            perk_id = perk_data.get('id')
            
            # If perk has an ID, update existing perk
            if perk_id:
                perk = TrackPerk.query.filter_by(id=perk_id, track_id=track_id).first()
                if not perk:
                    continue  # Skip if perk not found
                
                # Update perk fields
                if 'title' in perk_data:
                    perk.title = perk_data['title']
                if 'description' in perk_data:
                    perk.description = perk_data['description']
                if 's3_url' in perk_data:
                    perk.s3_url = perk_data['s3_url']
                if 'active' in perk_data:
                    perk.active = perk_data['active']
                if 'perk_type' in perk_data:
                    try:
                        perk.perk_type = PerkType[perk_data['perk_type']]
                    except KeyError:
                        continue  # Skip invalid perk type
            else:
                # Create new perk
                try:
                    perk_type = PerkType[perk_data.get('perk_type', 'text')]
                except KeyError:
                    perk_type = PerkType.text
                
                perk = TrackPerk(
                    title=perk_data.get('title', 'New Perk'),
                    description=perk_data.get('description'),
                    s3_url=perk_data.get('s3_url'),
                    track_id=track_id,
                    active=perk_data.get('active', False),
                    perk_type=perk_type,
                    additional_urls={}
                )
                
                db.session.add(perk)
                db.session.flush()  # Get the ID without committing
            
            updated_perks.append({
                'id': perk.id,
                'title': perk.title,
                'description': perk.description,
                's3_url': perk.s3_url,
                'active': perk.active,
                'perk_type': perk.perk_type.name,
                'temp_id': perk_data.get('temp_id')  # Return temp_id for frontend reference
            })
        
        db.session.commit()
        
        return jsonify({
            'message': 'Perks updated successfully',
            'perks': updated_perks
        }), HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/files/stem', methods=['OPTIONS'])
def handle_stem_options(track_id):
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
    return response, HTTPStatus.OK

@tracks_bp.route('/<uuid:track_id>/files/stem', methods=['POST'])
@musician_required
@handle_errors
def upload_stem_file(current_user, track_id):
    """Upload a stem file for a track"""
    # Verify track exists and belongs to the musician
    track = Track.query.filter_by(id=track_id, artist_id=current_user.id).first()
    if not track:
        return jsonify({'message': 'Track not found'}), HTTPStatus.NOT_FOUND
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), HTTPStatus.BAD_REQUEST
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), HTTPStatus.BAD_REQUEST
    
    # Create a new perk for the stem
    perk = TrackPerk(
        title=request.form.get('title', 'Stem'),
        description=request.form.get('description', 'Downloadable stem file'),
        track_id=track_id,
        active=request.form.get('active', 'true').lower() == 'true',
        perk_type=PerkType.audio
    )
    
    db.session.add(perk)
    db.session.flush()  # Get the ID without committing
    
    # Upload the file to S3
    try:
        perk.s3_url = s3_service.upload_perk_file(
            file, track_id, perk.id, is_audio=True
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Stem file uploaded successfully',
            'perk': {
                'id': str(perk.id),
                'title': perk.title,
                'description': perk.description,
                's3_url': perk.s3_url,
                'active': perk.active,
                'perk_type': perk.perk_type.name
            }
        }), HTTPStatus.CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error uploading stem file: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR 