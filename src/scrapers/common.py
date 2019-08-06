import sys
import requests
import queue
import multiprocessing
import threading
import queue

from bs4 import BeautifulSoup

sys.path.insert(1, 'calendar/')
import credentials
import gcalendar


class CalendarNotFound(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class MusicScraper:
    _credentials_json = None
    _credentials_token = None

    _gcalendar_name = None
    _perf_list_url = None

    _calendar_list = None
    _calendar = None

    _num_events = None
    _event_counter = 0
    _event_lock = multiprocessing.Lock()
    _perf_queue = queue.Queue()

    def __init__(self, gcalendar_name,
                 perf_list_url, creds_json,
                 creds_token):
        self._gcalendar_name = gcalendar_name
        self._perf_list_url = perf_list_url
        self._credentials_json = creds_json
        self._credentials_token = creds_token


    def __thread_work(self, service):
        while True:
            perf_url = self._perf_queue.get()

            if perf_url is None:
                break

            progress = 0
            with self._event_lock:
                self._event_counter += 1
                progress = self._event_counter

            print('({}/{}) {}'.format(progress,
                                      self._num_events,
                                      perf_url))

            event = self._event_from_page(perf_url)
            gcalendar.insert_event(service, self._calendar['id'], event)

            self._perf_queue.task_done()


    def _event_from_page(self, perf_url):
        raise NotImplementedError


    def _get_performance_urls(self):
        raise NotImplementedError


    def __get_calendars(self):
        service = credentials.get_service(
            self._credentials_json,
            self._credentials_token
        )

        self._calendar_list = gcalendar.get_calendars(service)


    def add_calendar(self):
        self.__get_calendars()
        for calendar in self._calendar_list:
            if calendar['summary'] == self._gcalendar_name:
                self._calendar = calendar
                break

        if self._calendar is None:
            raise CalendarNotFound(self._gcalendar_name, "Calendar not found")

        self._get_performance_urls()
        self._num_events = self._perf_queue.qsize()
        num_threads = multiprocessing.cpu_count()
        threads = []
        services = []

        # get a connection to google calendar for each thread
        for _ in range(num_threads):
            s = credentials.get_service(
                self._credentials_json,
                self._credentials_token
            )
            services.append(s)

        # launch threads
        for i in range(num_threads):
            thread = threading.Thread(
                target=self.__thread_work, args=(services[i],))
            thread.start()
            threads.append(thread)

        # wait for all URLs to be processed
        self._perf_queue.join()

        # tell threads to exit
        for _ in range(num_threads):
            self._perf_queue.put(None)

        # wait for threads to finish
        for t in threads:
            t.join()
