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

sys.path.insert(1, 'scrapers/')
import bso
import celebseries


def main():
    # bso.add_bso()
    celebseries.add_celebseries()

if __name__ == '__main__':
    main()
