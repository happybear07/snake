# 3주차 코드 해설 — 도토리 스네이크 (Acorn Snake)

파일: `acorn_snake.py` (화면·게임 루프·저장 전부) · 기획서 `plan-1.md` · 프로젝트 설정 `pyproject.toml` / `uv.lock` · 최고 점수 `acorn_highscore.json`

## 1. 기능

tkinter `Canvas` 20×20 격자 위에서 방향키로 다람쥐를 움직여 도토리를 먹는 스네이크 게임. 도토리를 먹으면 길이·점수 +1, 점수 5개마다 틱 간격이 8ms씩 짧아진다(110ms → 최소 50ms, 63~64행 `interval`). 벽이나 자기 몸에 닿으면 게임 오버. **진행 방향의 반대 방향키를 누르면 머리와 꼬리가 바뀐다**(이번 대화에서 추가). 최고 점수만 `acorn_highscore.json`에 저장하며, 표준 라이브러리(tkinter, random, json, pathlib)만 쓴다.

## 2. 켜자마자 일어나는 일

```
161  root = tk.Tk();  AcornSnake(root);  root.mainloop()              # 160~163행
38   self.saved_best = self.best = load_best()                        # __init__, 31~42행
42   self.reset()
```

`AcornSnake.__init__`(31~42행)은 고정 크기 창과 캔버스를 만들고 세 가지를 한다 — **기록 불러오기** `load_best`(15~20행, 파일이 없거나 깨져 있으면 0), **입력 연결** `<KeyPress>` → `on_key`, 창 닫기 → `on_close`, **처음 상태 만들기** `reset`(44~56행). `reset`은 격자 가운데에 길이 3짜리 몸을 오른쪽 방향으로 두고(`snake[0]`이 머리), 상태를 `"ready"`로 둔 뒤 도토리를 빈 칸에 놓고(`place_acorn`, 58~61행) `draw`(132~150행)로 점수 줄과 안내문을 그린다. 아직 루프는 돌지 않는다.

## 3. 상호작용할 때 일어나는 일

```
71   if self.state not in ("ready", "running") or len(self.queue) >= 2: return
73   if new != last: self.queue.append(new)          # 방향은 큐에 쌓았다가 틱에서 적용
93   if (new[0] + self.dir[0], new[1] + self.dir[1]) == (0, 0):   # 반대 방향이면
95       self.snake.reverse()                         #   머리·꼬리 교체
97       self.dir = (hx - nx, hy - ny)                #   꼬리 끝이 향하던 쪽으로
```

모든 키는 `on_key`(66~88행)로 들어온다.

**방향키** — 게임 중(`ready`/`running`)일 때만 받아 방향 큐(최대 2개)에 넣는다. 첫 입력이면 상태를 `running`으로 바꾸고 `tick`을 시작한다. 예전에는 72행에서 반대 방향을 버렸지만, 지금은 반대 방향도 큐에 넣고 판단을 `tick`에 맡긴다.

**루프 한 틱** — `tick`(90~115행)이 큐에서 방향 하나를 꺼낸다. 현재 방향의 정반대이면 몸 리스트를 뒤집어 원래 꼬리 끝을 머리로 만들고, 새 방향을 "꼬리 바로 앞 칸 → 꼬리 끝" 방향으로 정한다(93~97행). 누른 키 방향을 그대로 쓰지 않는 이유는, 몸이 꺾여 있을 때 새 머리가 곧바로 자기 목에 부딪히는 일을 막기 위해서다. 몸이 일직선이면 결과는 누른 방향과 같다. 그다음 머리를 한 칸 전진시키고, 벽 밖이거나 몸(꼬리 칸 제외 — 꼬리는 비켜 주므로)에 닿으면 `game_over`(117~121행). 도토리를 먹으면 꼬리를 남겨 길이 +1, 아니면 꼬리를 지운다. 끝으로 `root.after(self.interval(), self.tick)`로 다음 틱을 예약한다.

**스페이스 · R · 창 닫기** — 스페이스(78~86행)는 `running`이면 예약된 틱을 취소하고 "일시정지", `paused`면 재개한다. R(한글 자판 `ㄱ` 포함, 87~88행)은 언제든 `reset`. 창 X 버튼은 `on_close`(152~157행)가 예약을 취소하고, 이번 최고 점수가 파일보다 높을 때만 `save_best`로 저장한 뒤 창을 닫는다.

## 4. 이번 대화에서 바뀐 것

- **반대 방향 입력 → 머리·꼬리 교체**: "왼쪽으로 가는 중 오른쪽 키가 씹힌다"는 문제를 고쳤다. `on_key`의 반대 방향 무시 조건을 지우고 `tick`에 교체 로직(93~99행)을 넣었다. 창 없이 로직을 돌려 확인함 — 위로 꺾인 상태에서 아래를 누르면 원래 꼬리가 머리가 되어 왼쪽으로 진행, 게임 오버 없음.
- **기획서 반영**: `plan-1.md`의 상호작용 설명, 필수 구현, 체크리스트에서 "반대 방향 무시"를 "머리·꼬리 교체"로 바꾸고 체크 항목을 하나 추가했다.
- **uv 프로젝트 설정**: `pyproject.toml`(이름 `acorn-snake`, Python ≥ 3.9, 의존성 없음)을 만들고 `uv lock`으로 `uv.lock`을 생성했다. `uv run`이 만든 `.venv`는 삭제했다.
- **실행 오류 정리**: `C:\programming`에서 `uv run acorn_snake.py`를 실행해 "program not found"가 났다. uv 설치 문제가 아니라 폴더 위치 문제였다. `snake` 폴더로 이동해 실행하거나 `uv run --project snake snake\acorn_snake.py`로 실행하면 된다(`.venv` 없이 실행하려면 `python acorn_snake.py`).
