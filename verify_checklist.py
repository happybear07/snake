"""plan.md 와 api-plan.md 의 「체크리스트」 22개 항목 자동 검증.

방향키/스페이스/R 은 tkinter event_generate 로 실제 KeyPress 이벤트를 창에 보낸다.
루프 진행은 (a) 실제 시간을 흘려보내거나 (b) 예약을 취소하고 tick() 을 한 번 호출한다.
PokeAPI 를 실제로 부르는 항목은 15·16·20·22 번뿐이고, 나머지는 네트워크를 끊은
상태로 돌려 결과가 인터넷 사정에 흔들리지 않게 한다.
결과는 verify_result.txt (UTF-8) 에 적는다.
"""
import ast
import gc
import io
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path

import acorn_snake as A
import pokemon

OUT = []
RESULTS = []

_real_fetch = pokemon.fetch_one
_real_get = pokemon.requests.Session.get


def offline(on=True):
    """포켓몬을 한 마리도 못 받는 상태로 만든다(또는 되돌린다)."""
    pokemon.fetch_one = (lambda session: None) if on else _real_fetch


def cut_network(on=True):
    """requests 자체가 실패하게 만든다 — 인터넷이 끊긴 상황."""
    if on:
        pokemon.fetch_one = _real_fetch       # 실패 처리를 진짜로 거치게 한다

        def boom(*a, **k):
            raise pokemon.requests.ConnectionError("network cut (테스트)")
        pokemon.requests.Session.get = boom
    else:
        pokemon.requests.Session.get = _real_get
        offline(True)


def log(s=""):
    OUT.append(s)


def wait(root, ms):
    """실제 시간을 흘려보내며 after() 콜백이 돌게 한다."""
    end = time.perf_counter() + ms / 1000.0
    while time.perf_counter() < end:
        root.update()


def tidy(root, g, destroy):
    """예약된 after() 와 받아오던 스레드를 정리하고 창을 닫는다.

    바로 destroy() 하면 남아 있던 예약이 없어진 창을 찾아 Tcl 경고를 뿜는다.
    게임의 on_close() 가 하는 일과 같지만, 최고 점수는 건드리지 않는다.
    """
    g.feeder.stop()
    for job in filter(None, (g.poll_job, g.job)):
        try:
            root.after_cancel(job)
        except tk.TclError:
            pass
    g.poll_job = g.job = None
    g.sprites.clear()        # 창이 살아 있는 동안 이미지를 먼저 버린다
    root.destroy = destroy   # 덮어쓴 것을 되돌려 순환 참조를 끊는다
    destroy()                # (안 끊으면 Tk 객체가 끝까지 남아 종료 때 말썽)
    gc.collect()             # 다음 창을 만들기 전에 앞 창의 뒤처리를 끝낸다


def new_game(acorn=None):
    root = tk.Tk()
    g = A.AcornSnake(root)
    if acorn is not None:
        g.acorn = acorn          # 우연히 먹이를 먹어 결과가 흐려지지 않게 멀리 둔다
    root.update()
    real = root.destroy
    root.destroy = lambda: tidy(root, g, real)  # 검사마다 뒤처리를 빠뜨리지 않게
    return root, g


def wait_for_mon(root, g, limit=15):
    """포켓몬이 도착할 때까지 기다린다. (받은 것, 기다린 초) 를 돌려준다."""
    start = time.perf_counter()
    while g.mon is None and time.perf_counter() - start < limit:
        wait(root, 100)
    return g.mon, time.perf_counter() - start


def press(root, key):
    root.deiconify()
    root.lift()
    root.focus_force()          # 키 이벤트는 포커스를 가진 창으로만 전달된다
    root.update()
    root.event_generate("<KeyPress-%s>" % key, when="now")
    root.update()


def step(root, g):
    """예약된 틱을 취소하고 한 틱만 수동 진행."""
    if g.job:
        root.after_cancel(g.job)
        g.job = None
    g.tick()
    root.update()


def texts_of(g):
    return [g.canvas.itemcget(i, "text")
            for i in g.canvas.find_all() if g.canvas.type(i) == "text"]


def check(no, name, fn):
    try:
        ok, detail = fn()
    except Exception:
        ok = False
        detail = "예외: " + traceback.format_exc(limit=2).strip().replace("\n", " / ")
    RESULTS.append((no, name, ok, detail))
    log("[%s] %-2s %s" % ("O" if ok else "X", no, name))
    log("       " + detail)


# ---------------------------------------------------------------------- 1
def t1():
    root, g = new_game()
    before = list(g.snake)
    texts = texts_of(g)
    wait(root, 600)                       # 방향키를 누르지 않고 0.6초 기다림
    moved = g.snake != before
    ok = (g.state == "ready" and g.job is None and len(g.snake) == 3
          and g.dir == (1, 0) and g.acorn not in g.snake
          and any("점수 0" in t for t in texts) and A.HINT in texts
          and not moved)
    d = ("state=%s job=%s 몸=%s dir=%s 도토리=%s / 캔버스 글자=%s / 0.6초 후 이동=%s"
         % (g.state, g.job, before, g.dir, g.acorn, texts, moved))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 2
def t2():
    root, g = new_game(acorn=(0, 0))
    press(root, "Down")                   # 아래 방향키 1회만
    ys = [g.snake[0][1]]
    for _ in range(5):
        wait(root, 130)                   # 틱 간격 110ms -> 실제 시간으로 진행
        ys.append(g.snake[0][1])
    ok = (g.state == "running" and g.dir == (0, 1)
          and ys == sorted(ys) and ys[-1] - ys[0] >= 4)
    d = "아래 1회 후 추가 입력 없이 0.65초: 머리 y=%s, dir=%s, state=%s" % (ys, g.dir, g.state)
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 3
def t3():
    root, g = new_game(acorn=(0, 0))
    press(root, "Right")                  # 시작 (오른쪽)
    step(root, g)
    press(root, "Up")                     # 위로 꺾기
    step(root, g)
    bent, bent_dir = list(g.snake), g.dir
    press(root, "Down")                   # 진행 방향의 정반대
    step(root, g)
    ok = (g.state == "running" and len(g.snake) == 3 and g.dir == (-1, 0)
          and g.snake[1] == bent[-1])
    d = ("오른쪽 2틱 -> 위 1틱: 몸=%s dir=%s  |  아래키 1틱 후: 몸=%s dir=%s state=%s"
         % (bent, bent_dir, g.snake, g.dir, g.state))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 4
def t4():
    root, g = new_game()
    press(root, "Right")
    hx, hy = g.snake[0]
    g.acorn = (hx + 1, hy)                # 머리 바로 앞에 도토리를 놓음
    n0, s0 = len(g.snake), g.score
    step(root, g)
    ok = (len(g.snake) == n0 + 1 and g.score == s0 + 1
          and g.acorn is not None and g.acorn not in g.snake)
    d = ("길이 %d->%d, 점수 %d->%d, 새 도토리=%s (몸 위 아님=%s)"
         % (n0, len(g.snake), s0, g.score, g.acorn, g.acorn not in g.snake))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 5
def t5():
    root, g = new_game()
    table = []
    for s in (0, 4, 5, 9, 10, 15, 20, 40, 100):
        g.score = s
        table.append((s, g.interval()))
    vals = [v for _, v in table]
    by = dict(table)
    ok = (vals == sorted(vals, reverse=True) and min(vals) == A.MIN_MS
          and by[0] == A.BASE_MS and by[5] < by[4] and by[10] < by[9])
    d = ("점수->틱간격(ms) " + ", ".join("%d:%d" % t for t in table)
         + " / 기본 %dms, 하한 %dms" % (A.BASE_MS, A.MIN_MS))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 6
def t6():
    root, g = new_game(acorn=(0, 0))                 # (a) 벽
    press(root, "Right")
    g.snake = [(A.GRID - 1, 5), (A.GRID - 2, 5), (A.GRID - 3, 5)]
    g.dir = (1, 0)
    step(root, g)
    wall = (g.state, g.job, [t for t in texts_of(g) if "GAME OVER" in t])
    root.destroy()

    root, g = new_game(acorn=(0, 0))                 # (b) 자기 몸 (고리 모양)
    press(root, "Right")
    g.snake = [(5, 5), (6, 5), (6, 6), (5, 6), (4, 6), (4, 5)]
    g.dir = (0, 1)                                   # 아래 -> (5,6) 은 자기 몸
    step(root, g)
    body = (g.state, g.job, [t for t in texts_of(g) if "GAME OVER" in t])
    root.destroy()

    ok = (wall[0] == "over" and wall[1] is None and wall[2]
          and body[0] == "over" and body[1] is None and body[2])
    d = "벽 밖: state=%s job=%s 화면=%s  |  자기 몸: state=%s job=%s 화면=%s" % (wall + body)
    return ok, d


# ---------------------------------------------------------------------- 7
def t7():
    root, g = new_game(acorn=(0, 0))
    press(root, "Right")
    g.snake = [(A.GRID - 1, 5), (A.GRID - 2, 5), (A.GRID - 3, 5)]
    g.dir = (1, 0)
    step(root, g)                         # 게임 오버로 보냄
    before, state0 = list(g.snake), g.state
    for k in ("Up", "Down", "Left", "Right"):
        press(root, k)
    wait(root, 500)
    ok = (state0 == "over" and g.state == "over" and g.job is None
          and g.snake == before)
    d = ("게임 오버(state=%s) 상태에서 ↑↓←→ 4회 + 0.5초 대기: 몸 %s -> %s, state=%s job=%s"
         % (state0, before, g.snake, g.state, g.job))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 8
def t8():
    root, g = new_game(acorn=(0, 0))
    press(root, "Down")
    wait(root, 250)
    press(root, "space")                  # 일시정지
    p_snake, p_state, p_job = list(g.snake), g.state, g.job
    p_text = [t for t in texts_of(g) if "일시정지" in t]
    wait(root, 800)                       # 0.8초 방치
    frozen = g.snake == p_snake
    press(root, "space")                  # 재개
    r_job = g.job
    wait(root, 300)
    moved_again = g.snake != p_snake
    ok = (p_state == "paused" and p_job is None and frozen and p_text
          and g.state == "running" and r_job is not None and moved_again)
    d = ("space -> state=%s job=%s 화면=%s / 0.8초 방치 후 몸 그대로=%s / "
         "다시 space -> state=%s job 재예약=%s 이동재개=%s"
         % (p_state, p_job, p_text, frozen, g.state, r_job is not None, moved_again))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 9
def t9():
    root, g = new_game(acorn=(0, 0))
    press(root, "Down")
    wait(root, 250)
    g.score = 3
    press(root, "space")
    p_state = g.state
    press(root, "r")                      # 일시정지 중 R
    texts = texts_of(g)
    ok = (p_state == "paused" and g.state == "ready" and g.score == 0
          and len(g.snake) == 3 and g.dir == (1, 0) and g.job is None
          and A.HINT in texts)
    d = ("점수 3 에서 space(=%s) -> r: state=%s 점수=%s 길이=%d dir=%s job=%s 안내문=%s"
         % (p_state, g.state, g.score, len(g.snake), g.dir, g.job, A.HINT in texts))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 10
def t10():
    if A.SAVE_FILE.exists():
        A.SAVE_FILE.unlink()
    root, g = new_game(acorn=(0, 0))
    press(root, "Right")
    g.score = g.best = 7
    g.on_close()                          # 창의 X 버튼과 같은 경로
    saved = A.SAVE_FILE.read_text(encoding="utf-8")
    reloaded = A.load_best()
    root2, g2 = new_game()                # 다시 켜기
    texts = [t for t in texts_of(g2) if "점수" in t]
    ok = (reloaded == 7 and g2.best == 7 and any("최고 7" in t for t in texts))
    d = ("점수 7 로 X 닫기 -> 파일 내용 %s, load_best()=%s / 다시 켠 화면=%s"
         % (saved, reloaded, texts))
    root2.destroy()
    return ok, d


# ---------------------------------------------------------------------- 11
def t11():
    A.SAVE_FILE.write_text("{이건 망가진 JSON", encoding="utf-8")   # (a) 내용 손상
    broken = A.load_best()
    root, g = new_game()
    t_broken = [t for t in texts_of(g) if "점수" in t]
    ok1 = (broken == 0 and g.best == 0 and any("최고 0" in t for t in t_broken))
    root.destroy()

    A.SAVE_FILE.unlink()                                           # (b) 파일 삭제
    gone = A.load_best()
    root, g = new_game()
    t_gone = [t for t in texts_of(g) if "점수" in t]
    ok2 = (gone == 0 and g.best == 0 and any("최고 0" in t for t in t_gone))
    root.destroy()

    d = ("내용 손상: load_best()=%s 화면=%s / 파일 삭제: load_best()=%s 화면=%s"
         % (broken, t_broken, gone, t_gone))
    return ok1 and ok2, d


# ---------------------------------------------------------------------- 12
def t12():
    root, g = new_game(acorn=(0, 0))
    press(root, "Down")
    wait(root, 150)
    had_job = g.job is not None
    err = None
    try:
        g.on_close()                      # 게임이 도는 중에 X
    except Exception as e:
        err = repr(e)
    try:
        alive = bool(root.winfo_exists())
    except tk.TclError:
        alive = False                     # 창이 이미 파괴됨
    ok = (err is None and had_job and not alive)
    d = "진행 중(job 예약됨=%s)에 on_close() -> 예외=%s, 창 살아있음=%s" % (had_job, err, alive)
    return ok, d


# ---------------------------------------------------------------------- 13
def t13():
    """외부 패키지는 requests 하나, pyproject 와 uv.lock 에 잠겨 있다."""
    mods = set()
    for f in (A.__file__, pokemon.__file__):
        for node in ast.walk(ast.parse(Path(f).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[0])
    stdlib = {"json", "random", "tkinter", "pathlib", "base64", "queue", "threading"}
    third = mods - stdlib - {"pokemon"}
    pyproj = Path("pyproject.toml").read_text(encoding="utf-8")
    lock = Path("uv.lock").read_text(encoding="utf-8")
    locked = [ln.split('"')[1] for ln in lock.splitlines() if ln.startswith("name = ")]
    ok = (third == {"requests"} and "requests" in pyproj
          and "requests" in locked and "acorn-snake" in locked)
    d = ("import=%s / 외부 패키지=%s / pyproject 에 requests 있음=%s / "
         "uv.lock 에 잠긴 이름=%s"
         % (sorted(mods), sorted(third), "requests" in pyproj, locked))
    return ok, d


# ---------------------------------------------------------------------- 14
def t14():
    """게임 코드와 API 코드가 나뉘고, 각 파일이 200줄 이하다."""
    sizes = {}
    for f in (A.__file__, pokemon.__file__):
        sizes[Path(f).name] = len(Path(f).read_text(encoding="utf-8").splitlines())
    src = (Path(A.__file__).read_text(encoding="utf-8")
           + Path(pokemon.__file__).read_text(encoding="utf-8"))
    classes = [ln.strip() for ln in src.splitlines() if ln.strip().startswith("class ")]
    multi = [c for c in classes if "," in c]
    banned = [w for w in ("flask", "django", "fastapi", "pygame", "http.server",
                          "webbrowser", "<html", "PIL", "Pillow") if w in src]
    ok = (len(sizes) == 2 and max(sizes.values()) <= 200 and not multi and not banned)
    d = ("파일 줄 수=%s (전부 200 이하=%s) / 클래스=%s (다중상속=%s) / "
         "웹·프레임워크·이미지 라이브러리=%s"
         % (sizes, max(sizes.values()) <= 200, classes, multi or "없음",
            banned or "없음"))
    return ok, d


# ---------------------------------------------------------------------- 15
def t15():
    """창은 기다림 없이 뜨고, 잠시 뒤 먹이가 포켓몬 그림으로 바뀐다."""
    offline(False)
    t0 = time.perf_counter()
    root = tk.Tk()
    g = A.AcornSnake(root)
    root.update()
    open_sec = time.perf_counter() - t0
    first = g.mon                              # 켠 직후에는 아직 없는 게 정상
    got, waited = wait_for_mon(root, g)
    images = [i for i in g.canvas.find_all() if g.canvas.type(i) == "image"]
    ok = (open_sec < 1.0 and first is None and got is not None and bool(images))
    d = ("창 뜨는 데 %.3f초(<1초), 켠 직후 먹이=%s, %.1f초 뒤 포켓몬=%s, "
         "캔버스 image 요소=%d개"
         % (open_sec, first, waited, got and got["name"], len(images)))
    tidy(root, g, root.destroy)
    offline(True)
    return ok, d


# ---------------------------------------------------------------------- 16
def t16():
    """점수바에 지금 먹이의 이름과 타입이 보인다."""
    offline(False)
    root, g = new_game()
    mon, waited = wait_for_mon(root, g)
    bar = [t for t in texts_of(g) if "점수" in t]
    ok = bool(mon and bar and mon["name"] in bar[0] and mon["type"] in bar[0])
    d = ("%.1f초 뒤 받은 포켓몬=%s / 점수바=%s"
         % (waited, mon and (mon["name"], mon["type"]), bar))
    root.destroy()
    offline(True)
    return ok, d


def feed(g, root, type_name):
    """머리 바로 앞에 주어진 타입의 먹이를 놓고 한 틱 진행한다."""
    g.mon = {"name": "test-" + type_name, "type": type_name, "png": b""}
    hx, hy = g.snake[0]
    g.acorn = (hx + g.dir[0], hy + g.dir[1])
    n0, s0 = len(g.snake), g.score
    step(root, g)
    return n0, s0


# ---------------------------------------------------------------------- 17
def t17():
    """electric: 점수 +1, 길이 +1, 그리고 틱 간격이 절반이 된다."""
    root, g = new_game(acorn=(0, 0))
    press(root, "Right")
    plain_ms = g.interval()
    n0, s0 = feed(g, root, "electric")
    fast_ms, boost = g.interval(), g.boost
    ok = (g.score == s0 + 1 and len(g.snake) == n0 + 1 and boost > 0
          and fast_ms < plain_ms and fast_ms == max(A.MIN_MS, plain_ms // 2))
    d = ("점수 %d->%d, 길이 %d->%d, 남은 가속 틱=%d, 틱 간격 %dms->%dms"
         % (s0, g.score, n0, len(g.snake), boost, plain_ms, fast_ms))
    root.destroy()
    return ok, d


# ---------------------------------------------------------------------- 18
def t18():
    """rock·ground·steel: 점수 +2, 길이 +2."""
    rows, oks = [], []
    for name in ("rock", "ground", "steel"):
        root, g = new_game(acorn=(0, 0))
        press(root, "Right")
        n0, s0 = feed(g, root, name)
        g.acorn = (0, 0)
        step(root, g)                   # 꼬리를 한 틱 더 남겨 길이가 2 늘어난다
        after = len(g.snake)
        step(root, g)                   # 그다음 틱부터는 다시 꼬리를 뗀다
        oks.append(g.score == s0 + 2 and after == n0 + 2
                   and len(g.snake) == n0 + 2)
        rows.append("%s 점수 %d->%d 길이 %d->%d(그 뒤 %d 유지)"
                    % (name, s0, g.score, n0, after, len(g.snake)))
        root.destroy()
    return all(oks), " / ".join(rows)


# ---------------------------------------------------------------------- 19
def t19():
    """그 밖의 타입: 5주차와 같이 점수 +1, 길이 +1."""
    rows, oks = [], []
    for name in ("water", "fire", "grass", "psychic"):
        root, g = new_game(acorn=(0, 0))
        press(root, "Right")
        n0, s0 = feed(g, root, name)
        oks.append(g.score == s0 + 1 and len(g.snake) == n0 + 1 and g.boost == 0)
        rows.append("%s 점수+%d 길이+%d 가속=%d"
                    % (name, g.score - s0, len(g.snake) - n0, g.boost))
        root.destroy()
    return all(oks), " / ".join(rows)


# ---------------------------------------------------------------------- 20
def t20():
    """먹을 때마다 다른 포켓몬이 나온다."""
    offline(False)
    feeder = pokemon.Feeder(count=6)
    names, end = [], time.time() + 25
    while len(names) < 4 and time.time() < end:
        one = feeder.take()
        if one:
            names.append(one["name"])
        else:
            time.sleep(0.2)
    feeder.stop()
    offline(True)
    ok = len(names) == 4 and len(set(names)) >= 3
    d = "연달아 받은 4마리=%s (서로 다른 이름 %d종)" % (names, len(set(names)))
    return ok, d


# ---------------------------------------------------------------------- 21
def t21():
    """인터넷이 끊겨도 오류 없이 켜지고, 갈색 네모로 끝까지 플레이된다."""
    cut_network(True)                  # 모든 요청이 실패하는 상태로 만든다
    err, images = None, []
    no_mon = moved = ate = False
    try:
        root, g = new_game(acorn=(0, 0))
        wait(root, 1200)               # 받아올 시간을 줘도 큐가 비어 있어야 한다
        no_mon = g.mon is None
        images = [i for i in g.canvas.find_all() if g.canvas.type(i) == "image"]
        press(root, "Down")
        before = list(g.snake)
        wait(root, 400)
        moved = g.snake != before
        hx, hy = g.snake[0]
        g.acorn = (hx, hy + 1)
        s0 = g.score
        step(root, g)
        ate = g.score == s0 + 1
        root.destroy()
    except Exception as exc:
        err = repr(exc)
    finally:
        cut_network(False)
    ok = (err is None and no_mon and not images and moved and ate)
    d = ("예외=%s / 먹이 없음=%s, 캔버스 image 요소=%d개(갈색 네모) / "
         "방향키로 이동=%s / 먹으면 점수+1=%s"
         % (err, no_mon, len(images), moved, ate))
    return ok, d


# ---------------------------------------------------------------------- 22
def t22():
    """받아오는 도중에 X 로 닫아도 오류 없이 끝난다."""
    offline(False)
    err, pending, root = None, False, None
    try:
        root = tk.Tk()
        g = A.AcornSnake(root)
        root.update()                  # 아직 받아오는 중인 시점
        pending = g.mon is None
        g.on_close()
    except Exception as exc:
        err = repr(exc)
    try:
        alive = bool(root and root.winfo_exists())
    except tk.TclError:
        alive = False
    offline(True)
    ok = (err is None and pending and not alive)
    d = ("받아오는 중(먹이 아직 없음=%s)에 on_close() -> 예외=%s, 창 살아있음=%s"
         % (pending, err, alive))
    return ok, d


CHECKS = [
    ("1", "켜자마자 다람쥐·먹이·점수·안내문이 보이고, 방향키 전엔 안 움직임", t1),
    ("2", "방향키를 누르면 그 방향으로 계속 움직임", t2),
    ("3", "반대 방향키 -> 머리·꼬리 교체, 자기 몸에 부딪혀 게임 오버 안 됨", t3),
    ("4", "먹이를 먹으면 길이+1 점수+1, 새 먹이는 몸이 아닌 빈 칸", t4),
    ("5", "점수 5·10·15…에서 빨라지되 어느 한도 이하로는 안 빨라짐", t5),
    ("6", "벽 밖/자기 몸에 닿으면 즉시 멈추고 게임 오버 화면", t6),
    ("7", "게임 오버 뒤 방향키를 눌러도 움직이지 않음", t7),
    ("8", "스페이스로 멈춘 동안 한 칸도 움직이지 않음", t8),
    ("9", "일시정지 중 R 을 누르면 정지가 풀리며 처음 상태", t9),
    ("10", "최고 점수가 창을 닫은 뒤에도 남아 다시 켜면 보임", t10),
    ("11", "JSON 을 지우거나 망가뜨려도 켜지고 최고 점수 0", t11),
    ("12", "게임 도중 X 로 닫아도 오류 없이 종료", t12),
    ("13", "외부 패키지는 requests 하나, pyproject·uv.lock 에 잠겨 있음", t13),
    ("14", "게임 코드와 API 코드가 나뉘고 각 파일 200줄 이하", t14),
    ("15", "창은 기다림 없이 바로 뜨고, 잠시 뒤 먹이가 포켓몬 그림이 됨", t15),
    ("16", "점수바에 지금 먹이의 이름과 타입이 보임", t16),
    ("17", "electric: 점수+1 길이+1, 틱 간격이 절반으로 빨라짐", t17),
    ("18", "rock·ground·steel: 점수+2 길이+2", t18),
    ("19", "그 밖의 타입: 점수+1 길이+1 (5주차와 같음)", t19),
    ("20", "먹을 때마다 다른 포켓몬이 나옴", t20),
    ("21", "인터넷이 끊겨도 켜지고 갈색 네모로 플레이됨", t21),
    ("22", "받아오는 도중 X 로 닫아도 오류 없이 종료", t22),
]

offline(True)       # 기본은 네트워크를 끊은 상태

log("verify_checklist.py — plan.md·api-plan.md 「체크리스트」 자동 검증")
log("python %s / Tk %s / 실행 폴더 %s"
    % (sys.version.split()[0], tk.TkVersion, Path.cwd()))
log("실행 시각 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
log("1~14·17~19·21 번은 네트워크를 끊고 돌려, 5주차 동작이 API 와 무관한 것도 함께 본다.")
log("「.venv 를 지우고 uv run 으로 다시 실행」 항목은 창을 띄우는 검사가 아니라")
log("명령줄에서 따로 확인하고 README 에 적는다.")
log("=" * 78)
for no, name, fn in CHECKS:
    check(no, name, fn)
log("=" * 78)
passed = sum(1 for r in RESULTS if r[2])
log("통과 %d / %d" % (passed, len(RESULTS)))

if A.SAVE_FILE.exists():
    A.SAVE_FILE.unlink()                  # 검증이 만든 기록 파일 정리

io.open("verify_result.txt", "w", encoding="utf-8").write("\n".join(OUT) + "\n")
print("passed %d/%d -> verify_result.txt" % (passed, len(RESULTS)))
