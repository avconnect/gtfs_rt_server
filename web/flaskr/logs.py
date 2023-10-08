from datetime import datetime

from flask import current_app

error_log = current_app.config.get("ERROR_LOG", None)
logging_enable = current_app.config.get("LOGGING_ENABLED", False)


def add_to_error_log(header, error_msg):
    dt = datetime.utcnow()
    if logging_enable is True:
        print(f'Error logged by {header}: {dt.isoformat()}')
        error_log_file = open(error_log, 'a')
        print(f'{header}: {dt.isoformat()}\n{error_msg}', file=error_log_file)
        error_log_file.close()
    else:
        print(dt.isoformat(), header, error_msg)
