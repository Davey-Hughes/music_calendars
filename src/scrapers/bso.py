import sys
from datetime import datetime, timedelta
import queue
import requests
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import common

sys.path.insert(1, 'calendar/')
import credentials
import gcalendar


class BSOScraper(common.MusicScraper):
    _SYMPHONY_HALL_ADDR = \
        'Boston Symphony Hall, 301 Massachusetts Ave, Boston, MA 02115, USA'
    _BSO_BASE = 'https://www.bso.org'

    def _event_from_page(self, perf_url):
        page = requests.get(perf_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        p_detail = soup.find(class_='performance-detail')
        p_title = p_detail.find(class_='performance-title')
        p_location = p_detail.find(class_='facility')
        p_location_name = p_location.contents[0].strip()
        if p_location_name == 'Symphony Hall':
            p_location_name = self._SYMPHONY_HALL_ADDR

        p_description = p_detail.find(class_='performance-description')
        p_description = str(p_description.find('p'))
        p_description = p_description.replace('<p>', '').replace('</p>', '')

        description = '<a href="{}">Performance Page</a>'.format(perf_url)
        description += '<br><br>' + p_description

        p_performers = p_detail.find_all(class_='perfDetailsCell')
        if p_performers:
            description += '<br><br><b>Performers</b>'
            for performer in p_performers:
                description += '<br>' + performer.getText().strip()

        p_program = p_detail.find_all(class_='notes-title')
        if p_program:
            description += '<br><br><b>Program</b>'
            for note in p_program:
                description += '<br>' + note.getText().strip()

        p_date = p_detail.time.attrs['datetime'].split()[0]
        p_time = p_detail.find(class_='performance-time').getText()
        p_time = p_time.strip().split(', ')[1]

        p_datetime = datetime.strptime(
            p_date + ' ' + p_time,
            '%m/%d/%Y %I:%M %p'
        )

        p_endtime = p_datetime + timedelta(hours=2)

        event = {
            'summary': p_title.getText(),
            'location': p_location_name,
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

        return event


    def _get_performance_urls(self):
        page = requests.get(self._perf_list_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        perfs = soup.find_all(
            lambda tag: tag.name == 'div' and tag.get('class') == ['performance']
        )
        for p in perfs:
            detail_url = p.find('a', href=True)
            self._perf_queue.put(urljoin(self._BSO_BASE, detail_url['href']))


def add_bso():
    calendar_name = 'Boston Symphony Orchestra'
    perfs_url = 'https://www.bso.org/Performance/Listing'
    creds_json = '../credentials/credentials.json'
    creds_token = '../credentials/token.pickle'

    scraper = BSOScraper(calendar_name, perfs_url, creds_json, creds_token)
    scraper.add_calendar()
