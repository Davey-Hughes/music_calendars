import sys
from datetime import datetime, timedelta
import requests
import queue
from multiprocessing import cpu_count, Lock
import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

sys.path.insert(1, 'calendar/')
import credentials
import gcalendar

BSO_BASE = 'https://www.bso.org'
BSO_PERFORMANCES = urljoin(BSO_BASE, 'Performance/Listing')
SYMPHONY_HALL = 'Boston Symphony Hall, 301 Massachusetts Ave, Boston, MA 02115, USA'

performance_queue = queue.Queue()
event_counter = 0
event_lock = Lock()


def thread_work(service, calendar_id, num_events):
    while True:
        performance = performance_queue.get()

        if performance is None:
            break

        this_event_num = 0

        with event_lock:
            global event_counter
            event_counter += 1
            this_event_num = event_counter

        print('({}/{}) {}'.format(event_counter, num_events, performance))

        event = event_from_page(performance)
        gcalendar.insert_event(service, calendar_id, event)

        performance_queue.task_done()


def event_from_page(performance):
    page = requests.get(performance)
    soup = BeautifulSoup(page.text, 'html.parser')

    p_detail = soup.find(class_='performance-detail')
    p_title = p_detail.find(class_='performance-title')
    p_location = p_detail.find(class_='facility')
    p_location_name = p_location.contents[0].strip()
    if p_location_name == 'Symphony Hall':
        p_location_name = SYMPHONY_HALL

    p_description = p_detail.find(class_='performance-description')
    p_description = str(p_description.find('p')).replace('<p>', '').replace('</p>', '')

    description = '<a href="{}">Performance Page</a>'.format(performance)
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


def get_performance_urls():
    page = requests.get(BSO_PERFORMANCES)
    soup = BeautifulSoup(page.text, 'html.parser')

    performances = soup.find_all(
        lambda tag: tag.name == 'div' and tag.get('class') == ['performance']
    )
    for p in performances:
        detail_url = p.find('a', href=True)
        performance_queue.put(urljoin(BSO_BASE, detail_url['href']))

    return performance_queue


def add_bso(calendars):
    bso_calendar = None
    for calendar in calendars:
        if calendar['summary'] == 'Boston Symphony Orchestra':
            bso_calendar = calendar
            break

    get_performance_urls()
    num_events = performance_queue.qsize()
    num_threads = cpu_count()
    threads = []
    services = []

    for _ in range(num_threads):
        s = credentials.get_service(
            '../credentials/credentials.json',
            '../credentials/token.pickle'
        )
        services.append(s)

    # launch threads
    for i in range(num_threads):
        thread = threading.Thread(
            target=thread_work,
            args=(services[i], bso_calendar['id'], num_events)
        )
        thread.start()
        threads.append(thread)

    # wait for all URLs to be processed
    performance_queue.join()

    # tell threads to exit
    for _ in range(num_threads):
        performance_queue.put(None)

    # wait for threads to finish
    for t in threads:
        t.join()
