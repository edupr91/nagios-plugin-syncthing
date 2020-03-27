#!/usr/bin/python

# Main Author
#   - David Castañeda <edupr91@gmail.com>

import sys
import argparse
import requests
import datetime

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-H', '--host', required=True,
                    help='Syncthing Host')
parser.add_argument('-X', '--api_key', required=True,
                    help='Node API Key')
parser.add_argument('-P', '--port', default='8384',
                    help='Syncthing Port')
parser.add_argument('--https', default=False,
                    help='Https flag')
parser.add_argument('--action', default='check_alive',
                    choices=['check_alive', 'check_devices', 'check_last_scans', 'check_folders_status'],
                    help='Check to do, default check_alive')
args = vars(parser.parse_args())


def check_status(http_endpoint, headers):
    url = f"{http_endpoint}/rest/system/status"
    try:
        resp = requests.get(url=url, headers=headers)
        data = resp.json()
    except Exception as _ignored:
        print('CRITICAL: Error while getting Connection')
        sys.exit(2)
    print(f"OK: Syncthing is running.  {data['uptime']} secs uptime")
    sys.exit(0)


def get_id(http_endpoint, headers):
    url = f"{http_endpoint}/rest/system/status"
    try:
        resp = requests.get(url=url, headers=headers)
        data = resp.json()
    except Exception as _ignored:
        print('CRITICAL: Error while getting Connection')
        sys.exit(2)
    return data['myID']


def check_folder_lc(http_endpoint, headers):
    url = f"{http_endpoint}/rest/stats/folder"
    try:
        resp = requests.get(url=url, headers=headers)
        data = resp.json()
    except Exception as _ignored:
        print('CRITICAL: Error while getting Connection')
        sys.exit(2)

    folder_critical = []
    folder_warning = []
    folder_ok = []
    for folder in data:
        last_scan_str = data[folder]['lastScan'][:-4]
        last_scan = datetime.datetime.strptime(last_scan_str, '%Y-%m-%dT%H:%M:%S.%f')
        delta_time_70 = datetime.timedelta(minutes=70)
        delta_time_80 = datetime.timedelta(minutes=80)
        current_time = datetime.datetime.utcnow()
        current_time_70 = current_time - delta_time_70
        current_time_80 = current_time - delta_time_80
        if current_time_80 > last_scan:
            folder_critical += [folder]
        elif current_time_70 > last_scan:
            folder_warning += [folder]
        else:
            folder_ok += [folder]
    separator = ', '
    if 0 != len(folder_critical):
        folder_critical_str = separator.join(folder_critical)
        print(f'CRITICAL: we have this/these folder(s) with Errors {folder_critical_str}')
        sys.exit(2)
    elif 0 != len(folder_warning):
        folder_warning_str = separator.join(folder_warning)
        print(f'WARNING: we have this/these folder(s) with Errors {folder_warning_str}')
        sys.exit(1)
    else:
        folder_ok_str = separator.join(folder_ok)
        print(f'OK: all good with this/these folder(s) {folder_ok_str}')
        sys.exit(0)

def check_devices(http_endpoint, headers):

    myID = get_id(http_endpoint, headers)
    url = f"{http_endpoint}/rest/stats/device"
    try:
        resp = requests.get(url=url, headers=headers)
        data = resp.json()
    except Exception as _ignored:
        print('CRITICAL: Error while getting Connection')
        sys.exit(2)

    device_critical = []
    device_warning = []
    device_ok = []
    for device in data:
        # No need to check the last time you the server has seen himself
        # it always print "1970-01-01T00:00:00Z"
        if device == myID:
            continue
        last_scan_str = data[device]['lastSeen'][:-4]
        last_scan = datetime.datetime.strptime(last_scan_str, '%Y-%m-%dT%H:%M:%S.%f')

        delta_time_5 = datetime.timedelta(minutes=5)
        delta_time_10 = datetime.timedelta(minutes=10)
        current_time = datetime.datetime.utcnow()
        current_time_5 = current_time - delta_time_5
        current_time_10 = current_time - delta_time_10
        if current_time_10 > last_scan:
            device_critical += [device]
            # status = 'critical'
        elif current_time_5 > last_scan:
            device_warning += [device]
            status = 'warning'
        else:
            device_ok += [device]
            status = 'ok'

    device_critical_len = len(device_critical)
    device_warning_len = len(device_warning)
    device_ok_len = len(device_ok)

    if 0 != device_critical_len:
        print(f'CRITICAL: {device_critical_len} device(s) that haven\'t been seen in more than 10 min')
        sys.exit(2)
    elif 0 != device_warning_len:
        print(f'WARNING: {device_warning_len} device(s) that haven\'t been seen in the last 5 min')
        sys.exit(1)

    else:
        print(f'OK: {device_ok_len} devices have been seen lately')
        sys.exit(0)

def check_folder_status(http_endpoint, headers):

    url = f"{http_endpoint}/rest/stats/folder"
    try:
        resp = requests.get(url=url, headers=headers)
        data = resp.json()
    except Exception as _ignored:
        print('CRITICAL: Error while getting Connection')
        sys.exit(2)

    folder_critical = []
    folder_warning = []
    for folder in data:
        # get folder status in db
        folder_url = f"{http_endpoint}/rest/db/status?folder={folder}"
        folder_resp = requests.get(url=folder_url, headers=headers)
        folder_status = folder_resp.json()

        if folder_status['errors'] > 0:
            folder_critical += [f"{folder}:{folder_status['errors']}"]
        elif folder_status['pullErrors'] > 0:
            folder_critical += [f"{folder}:{folder_status['pullErrors']}"]
        elif folder_status['needBytes'] > 0:
            folder_warning += [f"{folder}:{folder_status['needBytes']}"]

    separator = ', '
    if len(folder_critical) > 0:
        folder_critical_str = separator.join(folder_critical)
        print(f'CRITICAL: folder_id:number_of_error - {folder_critical_str}')
        sys.exit(2)
    elif len(folder_warning) > 0:
        folder_warning_str = separator.join(folder_warning)
        print(f'WARNING: folder_id:bytes_behind - {folder_warning_str}')
        sys.exit(1)
    else:
        print(f"OK: All folders are 'UP to Date'")
        sys.exit(0)

def action_to_do(action, http_endpoint, headers):
    if action == 'check_alive':
        check_status(http_endpoint, headers),
    elif action == 'check_devices':
        check_devices(http_endpoint, headers),
    elif action == 'check_last_scans':
        check_folder_lc(http_endpoint, headers),
    elif action == 'check_folders_status':
        check_folder_status(http_endpoint, headers),

action = args['action']
if args['https']:
    http_endpoint = f"https://{args['host']}:{args['port']}"
else:
    http_endpoint = f"http://{args['host']}:{args['port']}"
headers = {'X-API-Key': args['api_key']}

action_to_do(action, http_endpoint, headers)