from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

from .extensions import db
from .models import Feed

bp = Blueprint('companies', __name__)


@bp.route('/')
def index():
    feeds = Feed.query.order_by(Feed.company_name.asc()).all()
    print(len(feeds))
    return render_template('companies/index.html', feeds=feeds)


@bp.route('/add_company', methods=('GET', 'POST'))
def add_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name', None, type=str)
        timezone = request.form.get('timezone', None, type=str)
        if not company_name:
            error = 'Enter company name'
            flash(error)
            return render_template('companies/add_company.html')
        company_name = company_name.lower()
        service_alert_url = request.form.get('service_alert_url', None, type=str)
        position_url = request.form.get('vehicle_position_url', None, type=str)
        trip_update_url = request.form.get('trip_update_url', None, type=str)
        '''for url in [position_url, trip_update_url, service_alert_url]:
            if not url:
                continue
            error = validate_url(url)
            if error is not None:
                flash(error)
                return render_template('companies/add_company.html')'''

        feed = Feed.query.filter_by(company_name=company_name).first()
        if feed is not None:
            # update
            feed.company_name = company_name
            feed.vehicle_position_url = position_url
            feed.trip_update_url = trip_update_url
            feed.service_alert_url = service_alert_url
            feed.timezone = timezone if timezone else None
        else:
            # create new
            feed = Feed()
            feed.company_name = company_name
            feed.vehicle_position_url = position_url if position_url else None
            feed.trip_update_url = trip_update_url if trip_update_url else None
            feed.service_alert_url = service_alert_url if service_alert_url else None
            feed.timezone = timezone if timezone else None
            db.session.add(feed)
        db.session.commit()
        print(f'Created company {company_name}')
        '''from .tasks import add_gtfs_tasks
        add_gtfs_tasks(feed.id)'''
        return redirect(url_for('companies.index'))
    return render_template('companies/add_company.html')


def validate_url(url: str):
    if url.startswith('http://'):
        return None
    elif url.startswith('https://'):
        return None
    return "malformed URL detected"
