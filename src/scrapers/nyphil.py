import sys
from datetime import datetime, timedelta
import queue
import requests
import re
import html
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import common

sys.path.insert(1, 'calendar/')
import credentials
import gcalendar


class NYPhilScraper(common.MusicScraper):
    _NYPHIL_BASE = 'https://nyphil.org/'


    def _event_from_page(self, perf_url):
        events = []

        page = requests.get(perf_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        p_title = soup.find(class_='nivo-html-caption').find('h2').getText()
        p_title = p_title.replace('&rcaron', 'ř')

        p_location = soup.find(class_='event-main-content-column').find('h2').getText()

        description = '<a href="{}">Performance Page</a>'.format(perf_url)
        description += '<br><br>'

        p_description = soup.find(class_='event-info').find_all('p')
        for p in p_description:
            p = str(p).replace('<p>', '').replace('</p>', '')
            p = p.replace('\n', '')
            description += p

        description += '<br><br><b>Program</b><br>'
        p_program = soup.find(class_='program-listing')
        if p_program:
            p_program = p_program.find_all('div', {'class': re.compile(r'col[0-9]+')})
            for p in p_program:
                p = p.find(('p', 'h2'))
                if not p:
                    continue
                p = str(p).replace('<h2>', '<b>').replace('</h2>', '</b>')
                p = p.replace('<p>', '').replace('</p>', '')
                p = p.replace('\n', '')
                if p:
                    description += p + ' '

        description += '<br><br><b>Artists</b><br>'
        p_artists = soup.find(class_='artists-listing')
        if p_artists:
            p_artists = p_artists.find_all('div', {'class': re.compile(r'col[0-9]+')})

            first_artist = True
            for p in p_artists:
                p = p.find(('p', 'h2'))
                if not p:
                    continue

                p = str(p)
                if 'h2' in p and not first_artist:
                    description += '<br>'
                else:
                    first_artist = False

                p = p.replace('<h2>', '<b>').replace('</h2>', '</b>')
                p = p.replace('<p>', '').replace('</p>', '').strip()
                p = p.replace('\n', '')
                p = p.replace('<br/>', '; ')
                if p:
                    description += p + ' '

        runtime = [2]
        p_duration = soup.find('div', {'id': 'body_0_panelDuration'})
        if p_duration:
            p_duration = p_duration.find('h2').getText()
            p_duration = p_duration.split('&')
            runtime = [int(''.join(c for c in s if c.isdigit())) for s in p_duration]

        if len(runtime) == 2:
            p_delta = timedelta(hours=runtime[0], minutes=runtime[1])
        else:
            p_delta = timedelta(hours=runtime[0])

        p_dates = soup.find(class_='iblock').find_all(class_='litem')
        for date in p_dates:
            p_dateinfo = date.find_all('div', {'class': re.compile(r'col[0-9]+')})
            day = p_dateinfo[0].find(class_='date').getText()
            month = p_dateinfo[0].find(class_='month').getText()
            time = p_dateinfo[1].find('h3').getText()
            full_date = day + ' ' + month + ' ' + time
            p_datetime = datetime.strptime(full_date, '%d %b, %Y %A, %I:%M %p')

            p_endtime = p_datetime + p_delta

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
        page = requests.get(self._perf_list_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        perfset = set()

        perfs = soup.find_all('a', string='Event Details', href=True)
        for p in perfs:
            perfset.add(p['href'])

        for p in perfset:
            self._perf_queue.put(urljoin(self._NYPHIL_BASE, p))


def add_nyphil():
    calendar_name = 'New York Philharmonic'
    perfs_url = 'https://nyphil.org/calendar?season=20&page=all'
    creds_json = '../credentials/credentials.json'
    creds_token = '../credentials/token.pickle'

    scraper = NYPhilScraper(calendar_name, perfs_url, creds_json, creds_token)
    scraper.add_calendar()
