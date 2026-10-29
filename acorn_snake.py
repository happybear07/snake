"""도토리 스네이크 (Acorn Snake) - 표준 라이브러리(tkinter)만 사용."""
import json
import random
import tkinter as tk
from pathlib import Path

GRID, CELL, TOP = 20, 24, 36
BASE_MS, MIN_MS, STEP_MS = 110, 50, 8
SAVE_FILE = Path(__file__).with_name("acorn_highscore.json")
DIRS = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0)}
FONT = "Malgun Gothic"
HINT = "방향키로 시작 · 스페이스 일시정지 · R 다시 시작"


def load_best():
    try:
        value = json.loads(SAVE_FILE.read_text(encoding="utf-8"))["best"]
        return value if isinstance(value, int) and value > 0 else 0
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_best(best):
    try:
        SAVE_FILE.write_text(json.dumps({"best": best}), encoding="utf-8")
    except OSError:
        pass


class AcornSnake:
    def __init__(self, root):
        self.root = root
        root.title("도토리 스네이크")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=GRID * CELL, height=TOP + GRID * CELL,
                                bg="#f5efe0", highlightthickness=0)
        self.canvas.pack()
        self.saved_best = self.best = load_best()
        root.bind("<KeyPress>", self.on_key)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.job = None
        self.reset()

    def reset(self):
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None
        mid = GRID // 2
        self.snake = [(mid - i, mid) for i in range(3)]  # 머리가 맨 앞
        self.dir = (1, 0)
        self.queue = []  # 다음 틱들에 적용할 방향(최대 2개)
        self.score = 0
        self.start_best = self.best
        self.state = "ready"
        self.place_acorn()
        self.draw()

    def place_acorn(self):
        free = [(x, y) for x in range(GRID) for y in range(GRID)
                if (x, y) not in self.snake]
        self.acorn = random.choice(free) if free else None

    def interval(self):
        return max(MIN_MS, BASE_MS - STEP_MS * (self.score // 5))

    def on_key(self, event):
        key = event.keysym
        if key in DIRS:
            new = DIRS[key]
            last = self.queue[-1] if self.queue else self.dir
            if self.state not in ("ready", "running") or len(self.queue) >= 2:
                return  # 게임 중이 아닐 때는 무시 (반대 방향은 tick에서 머리·꼬리 교체)
            if new != last:
                self.queue.append(new)
            if self.state == "ready":
                self.state = "running"
                self.tick()
        elif key == "space":
            if self.state == "running":
                self.state = "paused"
                self.root.after_cancel(self.job)
                self.job = None
                self.draw()
            elif self.state == "paused":
                self.state = "running"
                self.tick()
        elif key.lower() == "r" or event.char in ("ㄱ", "R", "r"):
            self.reset()

    def tick(self):
        if self.queue:
            new = self.queue.pop(0)
            if (new[0] + self.dir[0], new[1] + self.dir[1]) == (0, 0):
                # 반대 방향: 꼬리가 머리가 되어 꼬리 끝이 향하던 쪽으로 나아감
                self.snake.reverse()
                (hx, hy), (nx, ny) = self.snake[0], self.snake[1]
                self.dir = (hx - nx, hy - ny)
            else:
                self.dir = new
        head = (self.snake[0][0] + self.dir[0], self.snake[0][1] + self.dir[1])
        eating = head == self.acorn
        body = self.snake if eating else self.snake[:-1]  # 꼬리 칸은 비켜 주므로 통과 가능
        if not (0 <= head[0] < GRID and 0 <= head[1] < GRID) or head in body:
            return self.game_over()
        self.snake.insert(0, head)
        if eating:
            self.score += 1
            self.place_acorn()
        else:
            self.snake.pop()
        self.best = max(self.best, self.score)
        self.draw()
        if self.acorn is None:  # 판을 꽉 채운 경우
            return self.game_over()
        self.job = self.root.after(self.interval(), self.tick)

    def game_over(self):
        self.state = "over"
        self.job = None
        self.best = max(self.best, self.score)
        self.draw()

    def cell(self, pos, color):
        x, y = pos[0] * CELL, TOP + pos[1] * CELL
        self.canvas.create_rectangle(x + 1, y + 1, x + CELL - 1, y + CELL - 1,
                                     fill=color, outline="")

    def message(self, text, dy=0, size=14, color="#3b2f1e"):
        self.canvas.create_text(GRID * CELL // 2, TOP + GRID * CELL // 2 + dy,
                                text=text, font=(FONT, size, "bold"), fill=color)

    def draw(self):
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, GRID * CELL, TOP, fill="#e6dcc3", outline="")
        c.create_text(10, TOP // 2, anchor="w", font=(FONT, 12, "bold"), fill="#3b2f1e",
                      text=f"점수 {self.score} · 최고 {self.best}")
        if self.acorn:
            self.cell(self.acorn, "#8b5a2b")
        for i, pos in enumerate(self.snake):
            self.cell(pos, "#2e7d32" if i == 0 else "#4caf50")
        if self.state == "ready":
            self.message(HINT, size=12)
        elif self.state == "paused":
            self.message("일시정지", size=20)
        elif self.state == "over":
            self.message(f"GAME OVER · 점수 {self.score}", -14, 18, "#b71c1c")
            if self.score > self.start_best:
                self.message("최고 기록!", 16, 14, "#e65100")
            self.message("R 다시 시작", 44, 12)

    def on_close(self):
        if self.job:
            self.root.after_cancel(self.job)
        if self.best > self.saved_best:
            save_best(self.best)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    AcornSnake(root)
    root.mainloop()
