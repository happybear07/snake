"""도토리 스네이크 (Acorn Snake) - 먹이는 PokeAPI 로 받아 온 포켓몬."""
import json
import random
import tkinter as tk
from pathlib import Path
import pokemon

GRID, CELL, TOP = 20, 24, 36
BASE_MS, MIN_MS, STEP_MS = 110, 50, 8
SAVE_FILE = Path(__file__).with_name("acorn_highscore.json")
DIRS = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0)}
FONT = "Malgun Gothic"
HINT = "방향키로 시작 · 스페이스 일시정지 · R 다시 시작"


def load_best():
    try:  # 파일이 없거나 내용이 깨져 있어도 0 으로 시작한다
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
        self.feeder = pokemon.Feeder()  # 뒤에서 포켓몬을 받아 둔다
        self.sprites = {}               # 이미지 참조 보관 (GC 방지)
        self.mon = self.poll_job = None
        self.reset()
        self.poll_mon()

    def reset(self):
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None
        mid = GRID // 2
        self.snake = [(mid - i, mid) for i in range(3)]  # 머리가 맨 앞
        self.dir = (1, 0)
        self.queue = []              # 다음 틱들에 적용할 방향(최대 2개)
        self.score = self.boost = self.grow = 0   # 점수 / 가속 틱 / 꼬리 남길 틱
        self.start_best, self.state = self.best, "ready"
        self.place_acorn()
        self.draw()

    def place_acorn(self):
        free = [(x, y) for x in range(GRID) for y in range(GRID)
                if (x, y) not in self.snake]
        self.acorn = random.choice(free) if free else None
        self.take_mon()

    def take_mon(self):
        # 받아 둔 게 없으면 None -> 갈색 네모. 스프라이트 참조를 안 들고
        # 있으면 파이썬이 이미지를 치워 빈칸이 되므로 sprites 에 보관한다.
        self.mon = self.feeder.take()
        if self.mon and self.mon["name"] not in self.sprites:
            img = tk.PhotoImage(data=self.mon["png"])
            self.sprites[self.mon["name"]] = img.subsample(4, 4)  # 96 -> 24

    def poll_mon(self):
        if self.mon is None and self.acorn:   # 아직 갈색 네모면 도착했는지 확인
            self.take_mon()
            if self.mon:
                self.draw()
        self.poll_job = self.root.after(300, self.poll_mon)

    def interval(self):
        ms = BASE_MS - STEP_MS * (self.score // 5)
        return max(MIN_MS, ms // 2 if self.boost > 0 else ms)  # electric 가속

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
        elif key == "space" and self.state == "running":
            self.state = "paused"
            self.root.after_cancel(self.job)
            self.job = None
            self.draw()
        elif key == "space" and self.state == "paused":
            self.state = "running"
            self.tick()
        elif key.lower() == "r" or event.char in ("ㄱ", "R", "r"):
            self.reset()

    def tick(self):
        if self.queue:
            new = self.queue.pop(0)
            if (new[0] + self.dir[0], new[1] + self.dir[1]) == (0, 0):
                self.snake.reverse()    # 정반대: 꼬리가 머리가 되어 나아간다
                (hx, hy), (nx, ny) = self.snake[0], self.snake[1]
                self.dir = (hx - nx, hy - ny)
            else:
                self.dir = new
        head = (self.snake[0][0] + self.dir[0], self.snake[0][1] + self.dir[1])
        eating = head == self.acorn
        body = self.snake if eating else self.snake[:-1]  # 꼬리 칸은 비켜 준다
        if not (0 <= head[0] < GRID and 0 <= head[1] < GRID) or head in body:
            return self.game_over()
        self.snake.insert(0, head)
        if eating:
            self.score += self.eat()
            self.place_acorn()
        elif self.grow > 0:
            self.grow -= 1              # 한 틱 더 꼬리를 남긴다 (heavy)
        else:
            self.snake.pop()
        self.boost = max(0, self.boost - 1)
        self.best = max(self.best, self.score)
        self.draw()
        if self.acorn is None:  # 판을 꽉 채운 경우
            return self.game_over()
        self.job = self.root.after(self.interval(), self.tick)

    def eat(self):
        # 타입별 효과를 적용하고 오른 점수를 돌려준다
        kind = pokemon.effect_of(self.mon["type"]) if self.mon else "plain"
        if kind == "fast":
            self.boost = 25         # 약 25틱 동안 두 배 속도 (electric)
        if kind == "heavy":
            self.grow = 1           # 꼬리를 한 틱 더 남겨 길이 +2
            return 2
        return 1

    def game_over(self):
        self.state, self.job = "over", None
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
        mon = f" · {self.mon['name']}({self.mon['type']})" if self.mon else ""
        c.create_text(10, TOP // 2, anchor="w", font=(FONT, 11, "bold"),
                      fill="#3b2f1e", text=f"점수 {self.score} · 최고 {self.best}{mon}")
        sprite = self.sprites.get(self.mon["name"]) if self.mon else None
        if self.acorn and sprite:
            c.create_image(self.acorn[0] * CELL + CELL // 2,
                           TOP + self.acorn[1] * CELL + CELL // 2, image=sprite)
        elif self.acorn:
            self.cell(self.acorn, "#8b5a2b")        # 아직 못 받았으면 갈색 네모
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
        self.feeder.stop()
        for job in filter(None, (self.poll_job, self.job)):
            self.root.after_cancel(job)
        if self.best > self.saved_best:
            save_best(self.best)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    AcornSnake(root)
    root.mainloop()
