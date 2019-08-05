#!/usr/local/bin/python3

import sys
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

sys.path.insert(1, 'calendar/')
import credentials
import gcalendar


def main():
    service = credentials.get_service('../credentials/credentials.json', '../credentials/token.pickle')
    calendars = gcalendar.get_calendars(service)

    boston_cal = None

    for calendar in calendars:
        if calendar['summary'] == 'Boston Music Performances':
            boston_cal = calendar
            break

    event = {
        'summary': 'Test event',
        'location': 'Boston Symphony Orchestra',
        'description': 'this is a test event',
        'start': {
            'dateTime': '2019-08-05T20:00:00',
            'timeZone': 'America/New_York'
        },
        'end': {
            'dateTime': '2019-08-05T22:00:00',
            'timeZone': 'America/New_York'
        },
        'reminders': {
            'useDefault': True
        }
    }

    gcalendar.insert_event(service, boston_cal['id'], event)


if __name__ == '__main__':
    main()
