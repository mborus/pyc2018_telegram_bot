from pprint import pprint
import requests
import re
from collections import defaultdict, namedtuple
import logging
import json

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

URL_SA = "https://barcamptools.eu/pycamp201804/events/37163d8f-6122-4d7c-9d07-aa3d87ef00b3#sessions"
URL_SO = "https://barcamptools.eu/pycamp201804/events/05521a5d-3f4c-4a19-81a9-1f4bc6aa5985#sessions"
URL = URL_SO
URL_ADVICE = 'http://api.adviceslip.com/advice'


class PyCSession:

    def __init__(self, title, description=None, room=None):
        self.title = title
        self.description = description
        self._room = room

    @property
    def room(self):
        return self._room

    @room.setter
    def room(self, value: str):
        if value.startswith('Room:'):
            self._room = value[6:]
        else:
            self._room = value

    def __repr__(self):
        return '{} in {}'.format(self.title,
                                 self.room)


class PyCamp():
    def __init__(self, fake=False):
        # self.rooms, self.sessions = get_sessionplan_from_file('sa.html')
        self.rooms, self.sessions = get_sessionplan_from_url(URL)

    def filter_session_time(self, timestring):
        return [(v.title, v.room) for v in self.sessions.get(timestring, dict()) if v]

    def filter_session_room(self, room):
        return [(k, s.title) for k, v in self.sessions.items() for s in v if s.room == room]

    def filter_session_times(self):
        return sorted(set([k for k, v in self.sessions.items() for s in v if k[0] != '0']))

    def filter_rooms(self, all=True):

        if all:
            return [r for r in self.rooms if not any(['morgen' in r.lower(),
                                                      'ersatz' in r.lower()])]

        return sorted(set([s.room for k, v in self.sessions.items() for s in v]))

    def update(self):
        _rooms, _sessions = get_sessionplan_from_url(URL)
        if _sessions:
            self.rooms = _rooms
            self.sessions = _sessions


def cut_session_raw(sessionraw):
    current_part = []
    for line in sessionraw:
        if '<div class="sessionslot' in line:
            if current_part:
                yield current_part
                current_part = []
        current_part.append(line)
    if current_part:
        yield current_part


def parse_session_raw(sessionraw):
    sessions = []

    for i, part in enumerate(cut_session_raw(sessionraw)):
        line = ''.join(part)
        m = re.search('<h5>(.*?)<.h5>', line)
        if m:
            current_session = PyCSession(m.group(1))
            m = re.search('<div class="description">(.*?)</div>', line)
            if m:
                current_session.description = m.group(1)
            m = re.search('<div class="room-description">(.*?)</div>', line)
            if m:
                current_session.room = m.group(1)
            if not 'Morgen' in current_session.room:
                sessions.append(current_session)
    return sessions


def get_rooms_and_sessions(body):
    lines = iter(body.split('\n'))
    line = next(lines)
    rooms = []
    sessions_raws = defaultdict(list)

    # skip header
    try:
        while not 'sessiontable sessiontable-cols-' in line:
            line = next(lines)
    except StopIteration:
        return None

    # get rooms
    try:
        while not '<div class="timeslot cell">' in line:
            if '<div class="room' in line:
                line = next(lines)
            m = re.search('<h3>(.*)<.h3>', line)
            if m:
                rooms.append(m.group(1))
            line = next(lines)
    except StopIteration:
        return None

    # get sessions
    try:
        current_session = None
        while not '<div class="sessiontable-actions">' in line:
            if '<div class="timeslot cell">' in line:
                line = next(lines)
            m = re.search('<h3>(.*)<.h3>', line)
            if m:
                current_session = m.group(1)

            if current_session:
                sessions_raws[current_session].append(line)

            line = next(lines)
    except StopIteration:
        return None

    return rooms, {k: parse_session_raw(v) for k, v in sessions_raws.items()}


def get_sessionplan_from_file(filename):
    with open(filename, encoding='utf-8') as f1:
        body = f1.read()

    rooms, sessions = get_rooms_and_sessions(body)
    return rooms, sessions


def get_sessionplan_from_url(url):
    r = requests.get(url)
    logger.debug(url)
    if r.status_code == 200:
        body = r.text
        logger.debug('update erfolgreich')
    else:
        logger.debug('update fail')

    rooms, sessions = get_rooms_and_sessions(body)
    return rooms, sessions


def random_advice():
    r = requests.get(URL_ADVICE)
    if r.status_code == 200:
        return json.loads(r.text).get('slip').get('advice')


if __name__ == '__main__':
    pyc = PyCamp()

    pprint(pyc.filter_session_time('08:00'))
    pprint(pyc.filter_session_room('Plenum'))
    pprint(pyc.filter_session_times())
    pprint(pyc.filter_rooms())
    print(random_advice())
