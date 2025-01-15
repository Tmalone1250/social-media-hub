from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.campaign import bp
from app.models import Campaign, Post, db
from datetime import datetime
import json

@bp.route('/calendar')
@login_required
def calendar():
    return render_template('campaign/calendar.html')

@bp.route('/campaigns')
@login_required
def campaigns():
    return render_template('campaign/campaigns.html')

@bp.route('/api/campaigns/active')
@login_required
def get_active_campaigns():
    campaigns = Campaign.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).all()
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'start_date': c.start_date.isoformat(),
        'end_date': c.end_date.isoformat(),
        'status': c.status
    } for c in campaigns])

@bp.route('/api/campaigns', methods=['POST'])
@login_required
def create_campaign():
    data = request.get_json()
    campaign = Campaign(
        title=data['title'],
        description=data.get('description', ''),
        start_date=datetime.fromisoformat(data['start_date']),
        end_date=datetime.fromisoformat(data['end_date']),
        status='draft',
        user_id=current_user.id
    )
    db.session.add(campaign)
    db.session.commit()
    return jsonify({
        'id': campaign.id,
        'title': campaign.title,
        'status': campaign.status
    }), 201

@bp.route('/api/campaigns/<int:campaign_id>/posts')
@login_required
def get_campaign_posts(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    posts = Post.query.filter_by(campaign_id=campaign_id).all()
    return jsonify([{
        'id': p.id,
        'content': p.content,
        'media_url': p.media_url,
        'platform': p.platform,
        'scheduled_time': p.scheduled_time.isoformat(),
        'status': p.status
    } for p in posts])

@bp.route('/api/campaigns/<int:campaign_id>/posts', methods=['POST'])
@login_required
def create_post(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    post = Post(
        content=data['content'],
        media_url=data.get('media_url'),
        platform=data['platform'],
        scheduled_time=datetime.fromisoformat(data['scheduled_time']),
        status='pending',
        campaign_id=campaign_id
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({
        'id': post.id,
        'status': post.status
    }), 201

@bp.route('/api/campaigns/<int:campaign_id>', methods=['PUT'])
@login_required
def update_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if 'status' in data:
        campaign.status = data['status']
    if 'title' in data:
        campaign.title = data['title']
    if 'description' in data:
        campaign.description = data['description']
    if 'start_date' in data:
        campaign.start_date = datetime.fromisoformat(data['start_date'])
    if 'end_date' in data:
        campaign.end_date = datetime.fromisoformat(data['end_date'])
    
    db.session.commit()
    return jsonify({
        'id': campaign.id,
        'status': campaign.status,
        'title': campaign.title
    })

@bp.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
@login_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(campaign)
    db.session.commit()
    return '', 204

@bp.route('/api/campaigns')
@login_required
def get_campaigns():
    status = request.args.get('status')
    query = Campaign.query.filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    campaigns = query.all()
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'start_date': c.start_date.isoformat(),
        'end_date': c.end_date.isoformat(),
        'status': c.status
    } for c in campaigns])

@bp.route('/api/calendar/events')
@login_required
def get_calendar_events():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    posts = Post.query.join(Campaign).filter(
        Campaign.user_id == current_user.id,
        Post.scheduled_time.between(start_date, end_date)
    ).all()
    
    return jsonify([{
        'id': p.id,
        'title': p.content[:30] + '...' if len(p.content) > 30 else p.content,
        'start': p.scheduled_time.isoformat(),
        'platform': p.platform,
        'status': p.status,
        'campaign_id': p.campaign_id,
        'content': p.content,
        'media_url': p.media_url
    } for p in posts])

@bp.route('/api/posts/<int:post_id>', methods=['PUT'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    campaign = Campaign.query.get_or_404(post.campaign_id)
    
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if 'scheduled_time' in data:
        post.scheduled_time = datetime.fromisoformat(data['scheduled_time'])
    if 'content' in data:
        post.content = data['content']
    if 'platform' in data:
        post.platform = data['platform']
    if 'status' in data:
        post.status = data['status']
    
    db.session.commit()
    return jsonify({
        'id': post.id,
        'status': post.status,
        'scheduled_time': post.scheduled_time.isoformat()
    })

@bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    campaign = Campaign.query.get_or_404(post.campaign_id)
    
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(post)
    db.session.commit()
    return '', 204

@bp.route('/api/posts/bulk-schedule', methods=['POST'])
@login_required
def bulk_schedule_posts():
    data = request.get_json()
    campaign_id = data.get('campaign_id')
    posts_data = data.get('posts', [])
    
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    created_posts = []
    for post_data in posts_data:
        post = Post(
            campaign_id=campaign_id,
            content=post_data['content'],
            platform=post_data['platform'],
            scheduled_time=datetime.fromisoformat(post_data['scheduled_time']),
            status='pending'
        )
        db.session.add(post)
        created_posts.append(post)
    
    db.session.commit()
    
    return jsonify([{
        'id': p.id,
        'status': p.status,
        'scheduled_time': p.scheduled_time.isoformat()
    } for p in created_posts])
