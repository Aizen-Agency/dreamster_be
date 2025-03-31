from flask import Blueprint, jsonify, request
from app.middleware.admin_auth import admin_required
from app.extensions.extension import db
from app.models.user import User, UserRole
from app.models.track import Track
from app.routes.user.user_utils import handle_errors
from http import HTTPStatus
from sqlalchemy import func
from datetime import datetime, timedelta
import calendar

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
@handle_errors
def get_admin_stats(current_user):
    """Get comprehensive statistics for admin dashboard"""
    
    today = datetime.utcnow().date()
    current_month_start = datetime(today.year, today.month, 1)
    
    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year
    
    prev_month_start = datetime(prev_year, prev_month, 1)
    prev_month_end = current_month_start - timedelta(days=1)
    
    two_months_ago = today - timedelta(days=60)
    
    total_users = User.query.count()
    total_users_prev_month = User.query.filter(User.created_at < current_month_start, User.role == 'fan').count()
    users_growth = calculate_percentage_change(total_users, total_users_prev_month)
    
    new_signups = User.query.filter(User.created_at >= current_month_start, User.role == 'fan').count()
    new_signups_prev_month = User.query.filter(
        User.created_at >= prev_month_start,
        User.created_at < current_month_start,
        User.role == 'fan'
    ).count()
    signups_growth = calculate_percentage_change(new_signups, new_signups_prev_month)
    
    total_musicians = User.query.filter(User.role == UserRole.musician).count()
    total_musicians_prev_month = User.query.filter(
        User.role == UserRole.musician,
        User.created_at < current_month_start
    ).count()
    musicians_growth = calculate_percentage_change(total_musicians, total_musicians_prev_month)
    
    active_musicians_subquery = db.session.query(Track.artist_id.distinct()).filter(
        Track.created_at >= two_months_ago
    ).subquery()
    
    active_musicians = db.session.query(func.count(User.id)).filter(
        User.role == UserRole.musician,
        User.id.in_(active_musicians_subquery)
    ).scalar()
    
    prev_two_months_ago = prev_month_start - timedelta(days=60)
    active_musicians_prev_subquery = db.session.query(Track.artist_id.distinct()).filter(
        Track.created_at >= prev_two_months_ago,
        Track.created_at < current_month_start
    ).subquery()
    
    active_musicians_prev = db.session.query(func.count(User.id)).filter(
        User.role == UserRole.musician,
        User.id.in_(active_musicians_prev_subquery)
    ).scalar()
    
    active_musicians_growth = calculate_percentage_change(active_musicians, active_musicians_prev)
    
    inactive_musicians = total_musicians - active_musicians
    inactive_musicians_prev = total_musicians_prev_month - active_musicians_prev
    inactive_musicians_growth = calculate_percentage_change(inactive_musicians, inactive_musicians_prev)
    
    # Get total tracks
    total_tracks = Track.query.count()
    total_tracks_prev_month = Track.query.filter(Track.created_at < current_month_start).count()
    tracks_growth = calculate_percentage_change(total_tracks, total_tracks_prev_month)
    
    # New tracks this month
    new_tracks = Track.query.filter(Track.created_at >= current_month_start).count()
    new_tracks_prev_month = Track.query.filter(
        Track.created_at >= prev_month_start,
        Track.created_at < current_month_start
    ).count()
    new_tracks_growth = calculate_percentage_change(new_tracks, new_tracks_prev_month)

    total_admins_prev_month = User.query.filter(
        User.role == UserRole.admin,
        User.created_at < current_month_start
    ).count()
    total_admins = User.query.filter(User.role == UserRole.admin).count()
    admins_growth = calculate_percentage_change(total_admins, total_admins_prev_month)
    
    return jsonify({
        'total_users': {
            'count': total_users,
            'growth': users_growth
        },
        'new_signups': {
            'count': new_signups,
            'growth': signups_growth
        },
        'musicians': {
            'total': {
                'count': total_musicians,
                'growth': musicians_growth
            },
            'active': {
                'count': active_musicians,
                'growth': active_musicians_growth
            },
            'inactive': {
                'count': inactive_musicians,
                'growth': inactive_musicians_growth
            }
        },
        'admins': {
            'count': total_admins,
            'growth': admins_growth
        },
        'tracks': {
            'total': {
                'count': total_tracks,
                'growth': tracks_growth
            },
            'new': {
                'count': new_tracks,
                'growth': new_tracks_growth
            }
        },
        'time_period': {
            'current_month': f"{today.year}-{today.month}",
            'previous_month': f"{prev_year}-{prev_month}"
        }
    }), HTTPStatus.OK

@admin_bp.route('/monthly-trends', methods=['GET'])
@admin_required
@handle_errors
def get_monthly_trends(current_user):
    """Get monthly trends for the past 6 months"""
    
    today = datetime.utcnow().date()
    
    # Initialize data structure for the past 6 months
    months_data = []
    for i in range(5, -1, -1):
        # Calculate month and year
        month_offset = (today.month - i - 1) % 12 + 1
        year_offset = today.year - ((today.month - i - 1) // 12)
        
        # Calculate start and end dates for this month
        month_start = datetime(year_offset, month_offset, 1)
        
        # Calculate end date (start of next month - 1 day)
        if month_offset == 12:
            next_month_start = datetime(year_offset + 1, 1, 1)
        else:
            next_month_start = datetime(year_offset, month_offset + 1, 1)
        
        month_end = next_month_start - timedelta(days=1)
        
        # Get month name
        month_name = calendar.month_name[month_offset]
        
        # Count new users for this month
        new_users = User.query.filter(
            User.created_at >= month_start,
            User.created_at <= month_end
        ).count()
        
        # Count new musicians for this month
        new_musicians = User.query.filter(
            User.role == UserRole.musician,
            User.created_at >= month_start,
            User.created_at <= month_end
        ).count()
        
        # Count new tracks for this month
        new_tracks = Track.query.filter(
            Track.created_at >= month_start,
            Track.created_at <= month_end
        ).count()
        
        months_data.append({
            'month': f"{month_name} {year_offset}",
            'new_users': new_users,
            'new_musicians': new_musicians,
            'new_tracks': new_tracks
        })
    
    return jsonify({
        'monthly_trends': months_data
    }), HTTPStatus.OK

@admin_bp.route('/users', methods=['GET'])
@admin_required
@handle_errors
def get_all_users(current_user):
    """Get all users with pagination and filtering options."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_term = request.args.get('search')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    # Build query
    query = User.query
    
    # Apply search filter if provided
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
    
    # Apply sorting
    if sort_by == 'username':
        order_func = User.username.desc() if sort_order == 'desc' else User.username
    elif sort_by == 'email':
        order_func = User.email.desc() if sort_order == 'desc' else User.email
    else:  # default to created_at
        order_func = User.created_at.desc() if sort_order == 'desc' else User.created_at
    
    query = query.order_by(order_func)
    
    # Execute paginated query
    users_pagination = query.paginate(page=page, per_page=per_page)
    
    # Format user data
    users_data = []
    for user in users_pagination.items:
        # Get track count for musicians
        track_count = 0
        if user.role == UserRole.musician:
            track_count = Track.query.filter_by(artist_id=user.id).count()
        
        # Check if musician is active (uploaded tracks in last 60 days)
        is_active = False
        if user.role == UserRole.musician:
            two_months_ago = datetime.utcnow() - timedelta(days=60)
            recent_tracks = Track.query.filter(
                Track.artist_id == user.id,
                Track.created_at >= two_months_ago
            ).count()
            is_active = recent_tracks > 0
        
        users_data.append({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': user.role.name if user.role else None,
            'joined': user.created_at.isoformat(),
            'phone_number': user.phone_number,
            'track_count': track_count if user.role == UserRole.musician else None,
            'avatar': user.profile_picture_url if user.profile_picture_url else None,
            'is_active': is_active if user.role == UserRole.musician else None
        })
    
    return jsonify({
        'users': users_data,
        'total': users_pagination.total,
        'pages': users_pagination.pages,
        'current_page': page,
        'per_page': per_page
    }), HTTPStatus.OK

@admin_bp.route('/user-distribution', methods=['GET'])
@admin_required
@handle_errors
def get_user_distribution(current_user):
    """Get distribution of users by role with counts, percentages, and growth"""
    
    today = datetime.utcnow().date()
    current_month_start = datetime(today.year, today.month, 1)
    
    # Calculate previous month
    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year
    
    prev_month_start = datetime(prev_year, prev_month, 1)
    
    # Get total users count
    total_users = User.query.count()
    total_users_prev_month = User.query.filter(User.created_at < current_month_start).count()
    
    # Get counts by role
    musicians_count = User.query.filter(User.role == UserRole.musician).count()
    fans_count = User.query.filter(User.role == UserRole.fan).count()
    admins_count = User.query.filter(User.role == UserRole.admin).count()
    
    # Get previous month counts by role
    musicians_prev = User.query.filter(
        User.role == UserRole.musician,
        User.created_at < current_month_start
    ).count()
    
    fans_prev = User.query.filter(
        User.role == UserRole.fan,
        User.created_at < current_month_start
    ).count()
    
    admins_prev = User.query.filter(
        User.role == UserRole.admin,
        User.created_at < current_month_start
    ).count()
    
    # Calculate growth rates
    musicians_growth = calculate_percentage_change(musicians_count, musicians_prev)
    fans_growth = calculate_percentage_change(fans_count, fans_prev)
    admins_growth = calculate_percentage_change(admins_count, admins_prev)
    
    # Calculate percentages of total users
    musicians_percentage = round((musicians_count / total_users * 100), 2) if total_users > 0 else 0
    fans_percentage = round((fans_count / total_users * 100), 2) if total_users > 0 else 0
    admins_percentage = round((admins_count / total_users * 100), 2) if total_users > 0 else 0
    
    return jsonify({
        'musicians': {
            'count': musicians_count,
            'percentage': musicians_percentage,
            'growth': musicians_growth
        },
        'fans': {
            'count': fans_count,
            'percentage': fans_percentage,
            'growth': fans_growth
        },
        'admins': {
            'count': admins_count,
            'percentage': admins_percentage,
            'growth': admins_growth
        }
    }), HTTPStatus.OK
    
def calculate_percentage_change(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100 if current > 0 else 0
    
    change = ((current - previous) / previous) * 100
    return round(change, 2) 