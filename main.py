import json
import os
import sys
import urllib.error
import urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

VALUE = {"p": 1, "n": 3, "b": 3, "r": 5, "q": 9, "k": 0}
FILES = "abcdefgh"
CENTER = ("d4", "d5", "e4", "e5")


def post(path, body):
    req = urllib.request.Request(
        ENV_URL + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")


def board_of(fen):
    board = {}
    for i, row in enumerate(fen.split()[0].split("/")):
        x = 0
        for c in row:
            if c.isdigit():
                x += int(c)
            else:
                board[FILES[x] + str(8 - i)] = c
                x += 1
    return board


def apply(board, move):
    b = dict(board)
    f, t = move[:2], move[2:4]
    b[t] = b.pop(f)
    if len(move) == 5:
        b[t] = move[4].upper() if b[t].isupper() else move[4]
    return b


def eval_board(board, white_to_move):
    score = 0
    for sq, pc in board.items():
        v = VALUE[pc.lower()]
        sign = 1 if pc.isupper() else -1
        if sq in CENTER:
            v += 1
        score += sign * v
    return score if white_to_move else -score


def pawn_attacks(board, sq, by_white):
    rank = int(sq[1])
    file = FILES.index(sq[0])
    for d in (-1, 1):
        nf = file + d
        if 0 <= nf < 8:
            ns = FILES[nf] + str(rank + (1 if by_white else -1))
            pc = board.get(ns)
            if pc and pc.lower() == "p" and pc.isupper() == by_white:
                return True
    return False


def king_safety(board, color):
    """Penalty if the king's square is attacked by an enemy pawn (cheap, correct enough)."""
    king = "K" if color == "w" else "k"
    ksq = None
    for sq, pc in board.items():
        if pc == king:
            ksq = sq
            break
    if not ksq:
        return 0
    return 2 if pawn_attacks(board, ksq, color != "w") else 0


def choose(fen, legal):
    board = board_of(fen)
    wtm = fen.split()[1] == "w"

    def score(move):
        b2 = apply(board, move)
        s = eval_board(b2, wtm)
        victim = board.get(move[2:4])
        if victim:
            s += VALUE[victim.lower()] * 10
        if pawn_attacks(b2, move[2:4], not wtm):
            s -= 3
        if len(move) == 5:
            s += VALUE[move[4]] * 5
        s -= king_safety(b2, "w" if wtm else "b")
        return s

    best = None
    bs = -99999
    for m in legal:
        s = score(m)
        if s > bs:
            bs = s
            best = m
    return best


while True:
    g = post("/game", {})
    if g["status"] == "done":
        break
    while g["status"] == "your_move":
        g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
    print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
