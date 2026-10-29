# 작업 요약 — 도토리 스네이크 (snake)

- **작업일:** 2026-10-01 · **세션 이름:** `Snake_Game`
- **작업 디렉터리:** `C:\programming\snake`
- **현재 산출물:** `acorn_snake.py` (게임 단일 파일, 163줄) · `plan-1.md` (기획서) · `pyproject.toml` / `uv.lock` (uv 프로젝트 설정) · `report_snake_ver3.md` (코드 해설 보고서) · `summary_snake.md` (이 문서)

> 이번 세션에서 나눈 대화만 정리했다. 정확한 시각 기록이 없어 요청 순서대로 적었다.

---

## 1. 요청·대응 이력

| 순서 | 요청 내용 | 대응 |
|---|---|---|
| 1 | "Snake_Game으로 이름 저장해줘. 왼쪽으로 움직일 때 오른쪽 키를 누르면 씹히던데, 반대로 키를 누르면 꼬리랑 머리랑 바뀌도록 해줘" | 세션 이름을 `Snake_Game`으로 변경. `acorn_snake.py`의 반대 방향 무시 규칙을 지우고 머리·꼬리 교체 로직 추가 (§2) |
| 2 | "`plan-1.md` 해당 내용 md 파일에 반영해서 수정해줘" | 기획서 세 군데 수정 (§3) |
| 3 | "이 프로그램에 대한 pyproject.toml 이랑 uv.lock을 만들어줄 수 있니" | `pyproject.toml` 작성 + `uv lock` 실행 (§4) |
| 4 | "`irm https://astral.sh/uv/install.ps1 \| iex` 이런 에러가 뜨는데" | 터미널 확인 결과 uv는 이미 설치됨(0.12.21). 실제 오류는 `C:\programming`에서 실행해 파일을 못 찾은 것 (§5) |
| 5 | "venv는 없애줘" | `.venv` 폴더 삭제. `uv run`을 쓰면 다시 생기므로 `python acorn_snake.py` 실행을 안내 |
| 6 | "지금까지 한 대화내용 wk2에 report ver3 양식에 따라서 md 파일로 저장해줘" | `wk2/report_wk2_reaction_time_ver3` 구성(기능 / 켜자마자 / 상호작용, 행 번호 인용)을 따라 `report_snake_ver3.md` 작성. 대화에서 바뀐 내용은 4장으로 추가 |
| 7 | "지금 이게 어디 폴더에 저장되어 있는 거니" | `C:\programming\snake\report_snake_ver3.md`라고 안내 |
| 8 | "대화내용 요약한 것도 snake 안에 넣어줘 / 이번 세션에서 대화한 거로" | 이 문서 작성 |

---

## 2. acorn_snake.py 수정 내용 — 반대 방향 입력 시 머리·꼬리 교체

| 위치 | 변경 전 | 변경 후 | 이유 |
|---|---|---|---|
| `on_key` 71~72행 | 큐가 가득 찼거나 **반대 방향이면** `return` | 큐가 가득 찼을 때만 `return`, 반대 방향도 큐에 넣음 | 반대 방향 키가 "씹히던" 원인 제거 |
| `tick` 91~99행 | `self.dir = self.queue.pop(0)` | 꺼낸 방향이 현재 방향의 정반대이면 `self.snake.reverse()`로 꼬리를 머리로 만들고, 새 방향 = "꼬리 바로 앞 칸 → 꼬리 끝" 방향. 아니면 그대로 적용 | 머리·꼬리 교체 |

- **새 방향을 누른 키가 아니라 꼬리 끝 방향으로 정한 이유:** 몸이 꺾여 있을 때 누른 방향으로 가면 새 머리가 곧바로 자기 목에 부딪힐 수 있다. 몸이 일직선이면 두 방향은 같다.
- **검증(창 없이 로직만 실행):** 위로 꺾인 상태 `[(10,9),(10,10),(9,10)]`에서 아래를 누르면 → `[(8,10),(9,10),(10,10)]`, 방향 왼쪽, 상태 `running` (게임 오버 없음) ✓
- 실제 창을 띄워 키보드로 플레이하는 확인은 아직 하지 않음.

---

## 3. plan-1.md 수정 내용

| 위치 | 변경 전 | 변경 후 |
|---|---|---|
| 2. 상호작용 — 방향키 | 정반대 방향은 무시한다 | 정반대를 누르면 다음 틱에서 머리와 꼬리가 바뀌고, 꼬리 끝이 향하던 바깥쪽으로 나아간다(일직선이면 누른 방향과 같음) |
| 필수 구현 | 방향키 입력 처리 + 반대 방향 무시 규칙 | 방향키 입력 처리 + 반대 방향 입력 시 머리·꼬리 교체 규칙 |
| 체크리스트 | "반대 방향 입력은 무시되어야 함" 1개 항목 | "방향키 방향으로 계속 움직임" + "반대 방향키 → 머리·꼬리 교체, 자기 몸에 부딪혀 게임 오버되면 안 됨" 2개로 분리 |

---

## 4. uv 프로젝트 설정

- `pyproject.toml`: 이름 `acorn-snake`, 버전 `0.1.0`, `requires-python = ">=3.9"`, `dependencies = []` (표준 라이브러리만 사용), `readme = "plan-1.md"`
- `uv.lock`: `uv lock`으로 생성 — 외부 패키지가 없어 프로젝트 자신(`source = { virtual = "." }`)만 기록됨
- 확인: `uv run python -c "import tkinter, acorn_snake"` → `ok` (사용 Python: CPython 3.9.13)
- 이때 생긴 `.venv`는 요청에 따라 삭제

---

## 5. 작업 중 걸린 이슈와 해결

| 이슈 | 해결 |
|---|---|
| `uv run acorn_snake.py` → `Failed to spawn: acorn_snake.py, cause: program not found`. 사용자는 uv 설치 문제로 생각함 | uv는 이미 설치되어 있었다. 터미널 위치가 `C:\programming`이라 파일을 못 찾고 프로그램 이름으로 해석한 것. `cd C:\programming\snake` 후 실행하거나 `uv run --project snake snake\acorn_snake.py`로 해결 |
| `uv run`을 할 때마다 `.venv`가 생김 | 의존성이 없으므로 `python acorn_snake.py`로 바로 실행 가능 |

---

## 6. 현재 파일 구성

| 파일 | 역할 | 비고 |
|---|---|---|
| `acorn_snake.py` | 게임 전체 — 화면·게임 루프·입력·저장 | 163줄, 표준 라이브러리만 |
| `acorn_highscore.json` | 최고 점수 저장 | 창을 닫을 때 기록 경신 시에만 덮어씀 |
| `plan-1.md` | 기획서 (요구사항·체크리스트) | 머리·꼬리 교체 규칙 반영 |
| `pyproject.toml` / `uv.lock` | uv 프로젝트 설정 | 의존성 없음 |
| `report_snake_ver3.md` | 코드 해설 보고서 (wk2 ver3 양식) | |
| `summary_snake.md` | 이 문서 — 이번 세션 대화 요약 | |
