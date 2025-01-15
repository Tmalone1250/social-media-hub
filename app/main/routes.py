from flask import render_template
from flask_login import login_required
from app.main import bp

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return render_template('index.html')

@bp.route('/content-library')
@login_required
def content_library():
    return render_template('main/content_library.html')
