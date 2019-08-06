import sys
import time
from datetime import datetime, timedelta
import queue
import requests
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import common

sys.path.insert(1, 'calendar/')
import credentials
import gcalendar


class CSScraper(common.MusicScraper):
    _exclude_page = 'https://www.celebrityseries.org/live-performances/public-performance-projects/concert-for-one-1-musician-1-listener-1-minute-of-music/'


    def _event_from_page(self, perf_url):
        # slow down for rate limiting
        time.sleep(0.1)

        events = []
        page = requests.get(perf_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        p_title = soup.find(class_='spotlight_title').getText().strip()
        p_info = soup.find_all(class_='spotlight_info')
        p_location = p_info[0].find(class_='spotlight_info_label').getText()
        p_location = p_location.strip()

        p_dates = soup.find_all(class_='spotlight_info_date')
        for date in p_dates:
            p_date = date.getText()

            p_datetime = datetime.strptime(
                p_date.replace('\n', ''),
                '%a. %B %d, %I:%M %p'
            )

            today = datetime.now()
            month_percent = int(today.strftime('%m')) / 12

            # get the year
            if int(p_datetime.strftime('%m')) / 12 > 0.5:
                if month_percent > 0.5:
                    p_datetime = p_datetime.replace(year=today.year)
                else:
                    p_datetime = p_datetime.replace(year=today.year - 1)
            else:
                if month_percent > 0.5:
                    p_datetime = p_datetime.replace(year=today.year + 1)
                else:
                    p_datetime = p_datetime.replace(year=today.year)

            p_endtime = p_datetime + timedelta(hours=2)

            description = '<a href="{}">Performance Page</a>'.format(perf_url)

            p_description = soup.find(class_='typography')
            for p in p_description:
                if '<strong>' not in str(p):
                    description += '<br>'
                text = str(p).strip().replace('<p>', '').replace('</p>', '')
                text = text.replace('<br>', '')
                text = text.replace('<strong>', '').replace('</strong>', '')
                text = text.replace('<h2>', '<b>').replace('</h2>', '</b>')
                description += text

            event = {
                'summary': p_title,
                'location': p_location,
                'description': description,
                'start': {
                    'dateTime': p_datetime.isoformat(),
                    'timeZone': 'America/New_York'
                },
                'end': {
                    'dateTime': p_endtime.isoformat(),
                    'timeZone': 'America/New_York'
                },
                'reminders': {
                    'useDefault': True
                }
            }

            events.append(event)

        return events


    def _get_performance_urls(self):
        pages = set()
        page = requests.get(self._perf_list_url)
        while True:
            soup = BeautifulSoup(page.text, 'html.parser')

            perfs = soup.find_all(class_='event_item_title_link', href=True)
            for p in perfs:
                if p['href'] == self._exclude_page:
                    continue

                pages.add(p['href'])

            next_page = soup.find(class_='pagination_arrow_right', href=True)
            next_page = urljoin(self._perf_list_url, next_page['href'])
            if next_page == page.url:
                break

            page = requests.get(next_page)

        for item in pages:
            self._perf_queue.put(item)


def add_celebseries():
    calendar_name = 'Celebrity Series of Boston'
    perfs_url = 'https://www.celebrityseries.org/calendar-tickets/'
    creds_json = '../credentials/credentials.json'
    creds_token = '../credentials/token.pickle'

    scraper = CSScraper(calendar_name, perfs_url, creds_json, creds_token)
    scraper.add_calendar()
