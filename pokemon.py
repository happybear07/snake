"""PokeAPI에서 포켓몬을 미리 받아 두는 모듈.

게임 루프가 네트워크를 기다리면 화면이 멈추므로, 받아오는 일은 전부
백그라운드 스레드에서 한다. 게임 쪽은 take() 로 "준비된 게 있으면 하나,
없으면 None" 만 받아 가고 절대 기다리지 않는다.
"""
import base64
import queue
import random
import threading

import requests

API = "https://pokeapi.co/api/v2/pokemon/{}"
MAX_ID = 151          # 1세대까지만 쓴다
TIMEOUT = 5           # 초
PREFETCH = 8          # 켤 때 미리 받아 둘 마리 수

FAST = {"electric"}                    # 먹으면 빨라진다
HEAVY = {"rock", "ground", "steel"}    # 점수도 길이도 2씩


def effect_of(type_name):
    """타입 이름을 효과 세 가지 중 하나로 분류한다."""
    if type_name in FAST:
        return "fast"
    if type_name in HEAVY:
        return "heavy"
    return "plain"


def fetch_one(session):
    """포켓몬 한 마리를 받아 온다. 실패하면 None 을 돌려준다."""
    try:
        data = session.get(API.format(random.randint(1, MAX_ID)),
                           timeout=TIMEOUT).json()
        url = data["sprites"]["front_default"]
        if not url:                      # 스프라이트가 없는 포켓몬은 건너뛴다
            return None
        png = session.get(url, timeout=TIMEOUT).content
        return {
            "name": data["name"],
            "type": data["types"][0]["type"]["name"],
            "png": base64.b64encode(png),   # tkinter PhotoImage 가 받는 형식
        }
    except (requests.RequestException, ValueError, KeyError,
            TypeError, IndexError):
        return None                      # 인터넷이 없거나 응답이 깨진 경우


class Feeder:
    """준비된 포켓몬을 담아 두는 큐. 비어 있으면 게임은 갈색 네모를 쓴다."""

    def __init__(self, count=PREFETCH):
        self.ready = queue.Queue()
        self._session = requests.Session()
        self._stop = threading.Event()
        self._spawn(count)

    def _spawn(self, n):
        # daemon=True: 창을 닫을 때 이 스레드를 기다리지 않는다
        threading.Thread(target=self._work, args=(n,), daemon=True).start()

    def _work(self, n):
        got = 0
        tries = 0
        while got < n and tries < n * 3 and not self._stop.is_set():
            tries += 1
            one = fetch_one(self._session)
            if one:
                self.ready.put(one)
                got += 1

    def take(self):
        """준비된 포켓몬 하나. 없으면 None — 기다리지 않는다."""
        try:
            one = self.ready.get_nowait()
        except queue.Empty:
            return None
        self._spawn(1)                   # 하나 꺼냈으니 하나 더 채워 둔다
        return one

    def stop(self):
        self._stop.set()
