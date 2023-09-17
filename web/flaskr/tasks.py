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


'''
# create tasks for existing companies
def add_gtfs_tasks_existing():
    feeds = db.session.query(Feed).all()
    for feed in feeds:
        add_gtfs_tasks(feed.id)


# add new task
# if we allow each job to be executed by different threads(), then put lock on add_vehicle function
def add_gtfs_tasks(feed_id: int):
    scheduler.add_job(
        func=update_vehicle_position,
        trigger="cron",
        second=0,
        args=[feed_id],
        id=f"{feed_id}_update_vehicle_positions",
        name=f"{feed_id}: update vehicle positions",
        replace_existing=True
    )
    scheduler.add_job(
        func=update_trip_updates,
        trigger="cron",
        second=0,
        args=[feed_id],
        id=f"{feed_id}_update_trip_updates",
        name=f"{feed_id}: update trip records and stop distance",
        replace_existing=True
    )
    print(f"Tasks Added for {feed_id}")
'''
