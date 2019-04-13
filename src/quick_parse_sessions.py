from pprint import pprint
import requests
import re
from collections import defaultdict, namedtuple
import logging
import json
import time

import datetime

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG


URL_SA = "https://barcamptools.eu/pycamp201904/events/37163d8f-6122-4d7c-9d07-aa3d87ef00b3#sessions"
URL_SO = "https://barcamptools.eu/pycamp201904/events/05521a5d-3f4c-4a19-81a9-1f4bc6aa5985#sessions"
URL = None
if datetime.datetime.now().day == 13:
    URL = URL_SO
if datetime.datetime.now().day == 14:
    URL = URL_SO


URL_ADVICE = "http://api.adviceslip.com/advice"


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
        if value.startswith("Room:"):
            self._room = value[6:]
        else:
            self._room = value

    def __repr__(self):
        return "{} in {}".format(self.title, self.room)


class PyCamp:
    def __init__(self, fake=False):
        # self.rooms, self.sessions = get_sessionplan_from_file('sa.html')
        self.rooms, self.sessions = get_sessionplan_from_url(URL)

    def filter_session_time(self, timestring):
        return [(v.title, v.room) for v in self.sessions.get(timestring, dict()) if v]

    def filter_session_room(self, room):
        return [
            (k, s.title)
            for k, v in self.sessions.items()
            for s in v
            if s.room == room
            if len(s.title) > 3
        ]

    def filter_session_times(self):
        if self.sessions:
            return sorted(set([k for k, v in self.sessions.items() for s in v]))

    def filter_rooms(self):
        if self.rooms:
            return sorted(
                set(
                    [
                        s.room
                        for k, v in self.sessions.items()
                        for s in v
                        if not any(["ersatz" in s.room.lower(),
                                    "morgen" in s.room.lower()])
                    ]
                )
            )

    def update(self):

        url = URL_SA
        if datetime.datetime.now().day == 13:
            url = URL_SA
        if datetime.datetime.now().day == 14:
            url = URL_SO
        if datetime.datetime.now().day == 15:
            url = None

        if url:
            _rooms, _sessions = get_sessionplan_from_url(url)
        else:
            self.sessions = None
        if _sessions:
            self.rooms = _rooms
            self.sessions = _sessions

        # if datetime.datetime.now().day == 11:
        #    self.sessions = []


    def get_now_and_next(self):
        now = datetime.datetime.strptime(time.strftime('%H:%M', time.localtime(time.time())), '%H:%M')
        mynow = None
        mynext = None
        for t in self.sessions:
            dts = datetime.datetime.strptime(t, '%H:%M')
            if dts <= now:
                if not mynow:
                    mynow = dts
                else:
                    if mynow < dts:
                        mynow = dts
            if dts > now:
                if not mynext:
                    mynext = dts
                else:
                    if mynext > dts:
                        mynow = dts
        if mynow:
            mynow = datetime.datetime.strftime(mynow, '%H:%M')
        if mynext:
            mynext = datetime.datetime.strftime(mynext, '%H:%M')
        return mynow, mynext, time.strftime('%H:%M', time.localtime(time.time()))



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
        line = "".join(part)
        m = re.search("<h5>(.*?)<.h5>", line)
        if m:
            current_session = PyCSession(m.group(1))
            m = re.search('<div class="description">(.*?)</div>', line)
            if m:
                current_session.description = m.group(1)
            m = re.search('<div class="room-description">(.*?)</div>', line)
            if m:
                current_session.room = m.group(1)
            if not any(
                [
                    "morgen" in (current_session.room or "").lower(),
                    "ersatz" in (current_session.room or "").lower(),
                ]
            ):
                sessions.append(current_session)
    return sessions


def get_rooms_and_sessions(body):
    lines = iter(body.split("\n"))
    line = next(lines)
    rooms = []
    sessions_raws = defaultdict(list)

    # skip header
    try:
        while not "sessiontable sessiontable-cols-" in line:
            line = next(lines)
    except StopIteration:
        return None

    # get rooms
    try:
        while not '<div class="timeslot cell">' in line:
            if '<div class="room' in line:
                line = next(lines)
            m = re.search("<h3>(.*)<.h3>", line)
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
            m = re.search("<h3>(.*)<.h3>", line)
            if m:
                current_session = m.group(1)

            if current_session:
                sessions_raws[current_session].append(line)

            line = next(lines)
    except StopIteration:
        return None

    return rooms, {k: parse_session_raw(v) for k, v in sessions_raws.items()}


def get_sessionplan_from_file(filename):
    with open(filename, encoding="utf-8") as f1:
        body = f1.read()

    rooms, sessions = get_rooms_and_sessions(body)
    return rooms, sessions


def get_sessionplan_from_url(url):

    if url:
        r = requests.get(url)
        logger.debug(url)
        if r.status_code == 200:
            body = r.text
            logger.debug("update erfolgreich")
        else:
            logger.debug("update fail")

        rooms, sessions = get_rooms_and_sessions(body)

        return rooms, sessions
    return None, None



def random_advice():
    r = requests.get(URL_ADVICE)
    if r.status_code == 200:
        return json.loads(r.text).get("slip").get("advice")


if __name__ == "__main__":
    pyc = PyCamp()

    pprint(pyc.filter_session_time("08:00"))
    pprint(pyc.filter_session_room("Raum 13"))
    pprint(pyc.filter_session_times())
    pprint(pyc.filter_rooms())
    print(random_advice())
