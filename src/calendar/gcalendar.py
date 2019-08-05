import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def get_calendars(service):
    calendars = []
    page_token = None

    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            calendars.append(calendar_list_entry)
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

    return calendars


def insert_event(service, calendar_id, event):
    new_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return new_event
