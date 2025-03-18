from flask import Blueprint, request, jsonify
from app.middleware.musician_auth import musician_required
from app.extensions.extension import db
from app.models.track import Track
from app.services.s3_service import S3Service
from http import HTTPStatus
from app.routes.user.user_utils import handle_errors
import uuid

tracks_bp = Blueprint('tracks', __name__, url_prefix='/api/musician/tracks')
s3_service = S3Service(bucket_name='your-s3-bucket-name')

@tracks_bp.route('/', methods=['POST'])
@musician_required
@handle_errors
def upload_track(current_user):
    try:
        # Validate and process input
        title = request.form.get('title')
        if not title:
            return jsonify({'message': 'Title is required'}), HTTPStatus.BAD_REQUEST

        # Save metadata to database
        track_id = uuid.uuid4()
        track = Track(
            id=track_id,
            title=title,
            description=request.form.get('description'),
            genre=request.form.get('genre'),
            tags=request.form.get('tags'),
            starting_price=request.form.get('starting_price', 0),
            artist_id=current_user.id
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
            'message': 'Track uploaded successfully',
            'track': {
                'id': track.id,
                'title': track.title,
                's3_url': track.s3_url
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
    track.title = request.form.get('title', track.title)
    track.description = request.form.get('description', track.description)
    track.genre = request.form.get('genre', track.genre)
    track.tags = request.form.get('tags', track.tags)
    track.starting_price = request.form.get('starting_price', track.starting_price)

    db.session.commit()
    return jsonify({'message': 'Track updated successfully'}), HTTPStatus.OK

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