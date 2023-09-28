from flask import request

# ARGS
FEED_ID = 'feed_id'
COMPANY_NAME = 'company_name'
GTFS_ID = 'gtfs_id'
DAY = 'day'
TRIP_IDS = 'trip_ids'
PAGE = 'page'


def check_get_args(args_list):
    """
    Make sure all required args are in get
    :return: True, None if OK, False, missing arg
    """
    missing_args = [arg for arg in args_list if not request.args.get(arg, False)]
    if len(missing_args) > 0:
        return False, {"missing parameters": str(missing_args)}
    return True, None


def check_get_form_args(args_list):
    missing_args = [arg for arg in args_list if not request.form.get(arg, False)]
    if len(missing_args) > 0:
        return False, {"missing parameters": str(missing_args)}
    return True, None


def check_json_post_args(args_list):
    """
    Make sure all required args are keys in posted json
    :return: True, None if OK, False, missing args
    """
    missing_args = [arg for arg in args_list if arg not in request.json.keys()]
    if len(missing_args) > 0:
        return {}, {"missing parameters": str(missing_args)}
    return request.json, None
