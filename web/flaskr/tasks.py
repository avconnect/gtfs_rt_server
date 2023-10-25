from .gtfs_update import update_vehicle_position, update_trip_updates
from .extensions import scheduler, db
from .models import Feed
from datetime import datetime


@scheduler.task('cron', id='update_feed_all', second=0, misfire_grace_time=10)
def update_feeds():
    with scheduler.app.app_context():
        time_start = datetime.utcnow().replace(microsecond=0)
        feeds = db.session.query(Feed).all()
        for feed in feeds:
            print(f'Updating Feed {feed.id}')
            update_vehicle_position(feed.id, time_start)
            update_trip_updates(feed.id, time_start)
        time_end = datetime.utcnow().replace(microsecond=0)
        print(f'All feeds updated {time_end.isoformat()}\n')

