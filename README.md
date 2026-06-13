English | [中文](./README_CN.md)

# Chess Guider - Chess AI Advisor

A chess AI engine based on Alpha-Beta search, offering both command-line and browser interfaces. It runs in **advisor mode** — the AI plays your color, and you are responsible for syncing the opponent's moves on the board.

## Project Structure

```
├── engine.py        # Search engine core (evaluation, search, transposition table)
├── chess_ai.py      # Command-line interface
├── chess_web.py     # Browser-based web interface (zero external dependencies)
├── test_engine.py   # Engine test suite (40 tests)
└── test_tt.py       # Transposition table verification tests
```

## Quick Start

### Install Dependencies

```bash
pip install chess
```

### Command-Line Mode

```bash
python chess_ai.py
```

Choose to play as White (w) or Black (b). The AI will suggest your moves, and you input the opponent's moves.

### Browser Mode

```bash
python chess_web.py
```

Open your browser and navigate to `http://127.0.0.1:8080`. Click "Play White" or "Play Black" to start.

## Advisor Mode

Unlike traditional "human vs. AI" gameplay, this program runs in **advisor mode**:

| Scenario | Flow |
|----------|------|
| Playing White | AI automatically plays White's first move → you input Black's move → AI suggests White's next move → loop |
| Playing Black | You input White's move → AI suggests Black's next move → you input White's move → loop |

In the browser interface, simply click the opponent's piece and drag it to the target square to input their move. The AI will automatically calculate and execute the move for your color.

---

## Algorithm Details

### 1. Alpha-Beta Pruning Search

The core search algorithm uses Negamax-style Alpha-Beta pruning. By maintaining a search window `[alpha, beta]`, branches whose evaluation falls outside the window are pruned, avoiding the exploration of clearly inferior options.

```
alpha_beta(board, depth, alpha, beta, maximizing):
    if depth == 0: return quiescence(...)
    for move in ordered_moves:
        score = -alpha_beta(board, depth-1, -beta, -alpha, ...)
        if score >= beta: return beta  // beta cutoff
        alpha = max(alpha, score)
    return alpha
```

### 2. Iterative Deepening

The search starts at depth=1 and gradually increases the depth until the maximum depth is reached or time runs out.

**Advantages:**
- A best move is always available at any point, preventing timeouts
- The best move from the previous iteration is stored in the transposition table, providing a PV move for the next iteration and significantly improving pruning efficiency
- The time cost of shallow searches is negligible compared to deeper searches

```python
for current_depth in range(1, max_depth + 1):
    score, move = alpha_beta(board, current_depth, ...)
    best_move = move  # always keep the latest result
    if elapsed > time_limit:
        break
```

Default parameters: max depth 5, time limit 5 seconds.

### 3. Quiescence Search

When the main search reaches depth=0, instead of returning a static evaluation directly, it continues searching all capture moves until the position is "quiet" (no more captures available).

**Problem solved:** Horizon Effect — if the search stops in the middle of a tactical exchange, the evaluation can be severely distorted. For example, if a white queen captures a black rook and the search stops there, but black can recapture the white queen, white is actually at a loss.

```
quiescence(board, alpha, beta):
    stand_pat = evaluate(board)  // static evaluation without making a move
    if stand_pat >= beta: return beta
    for capture_move in ordered_captures:
        score = -quiescence(board after capture)
        if score >= beta: return beta
    return best_score
```

Capture moves are sorted by **MVV-LVA** (Most Valuable Victim - Least Valuable Aggressor): captures where a lower-value piece takes a higher-value piece are searched first.

### 4. Transposition Table

A transposition table based on **Zobrist hashing** that stores results of previously searched positions. The same position can be reached through different move orders (transpositions), and the table avoids redundant searches.

**Stored content:** `(depth, score, flag, best_move)`

**Three flags:**
| Flag | Meaning |
|------|---------|
| `TT_EXACT` | Exact value (alpha < score < beta) |
| `TT_LOWERBOUND` | Lower bound (beta cutoff, actual value >= score) |
| `TT_UPPERBOUND` | Upper bound (did not exceed alpha, actual value <= score) |

**Replacement policy:** Depth-preferred — deeper search results are never overwritten by shallower ones. Capacity limit: 1 million entries; cleared when exceeded.

**Dual purpose:**
1. When depth is sufficient, return the cached score directly (pruning)
2. When depth is insufficient, still return `best_move` for move ordering (PV move)

### 5. Check Extension

When a move results in the opponent being in check, the search depth is not reduced (effectively a +1 depth extension).

**Rationale:** Check positions are forcing (the opponent must respond to the check) and have high information density. Without extension, checkmate sequences can be missed. Since there are typically few responses to a check, the extension does not significantly increase the search tree.

**Safety mechanism:** The `ply` parameter tracks the total search depth, and `MAX_PLY=64` prevents infinite recursion from consecutive checks.

### 6. Null Move Pruning

Assume "skipping a turn" (letting the opponent move twice). If the position is still >= beta, it indicates a huge advantage, and the branch can be pruned.

```
if allow_null and depth >= 3 and not in_check:
    board.push(null_move)
    null_score = -alpha_beta(board, depth-1-R, -beta, -beta+1, ...)
    board.pop()
    if null_score >= beta:
        return null_score  // prune
```

**Key parameters:**
- `NULL_MOVE_REDUCTION = 2`: depth reduction for null move search
- Zero-window search `(-beta, -beta+1)`: only verifies whether the score is >= beta
- `allow_null=False`: prevents consecutive null moves
- Not used when in check (must respond to check; null move is meaningless)

### 7. Move Ordering

Move ordering quality directly determines Alpha-Beta pruning efficiency. Priority from highest to lowest:

| Priority | Move Type | Score |
|----------|-----------|-------|
| 1 | Transposition table best move (TT move) | 1,000,000 |
| 2 | Captures (MVV-LVA) | 10 × victim value - aggressor value |
| 3 | Promotions | Queen value (900) |
| 4 | All other moves | 0 |

### 8. Evaluation Function

The evaluation function consists of three components:

**Material values:**
| Piece | Pawn | Knight | Bishop | Rook | Queen | King |
|-------|------|--------|--------|------|-------|------|
| Value | 100 | 320 | 330 | 500 | 900 | 20000 |

**Piece-Square Tables (PST):** Each piece type receives positional bonuses on different squares. For example:
- Pawns get bonuses in the center (d4/e5) and no bonus on the edges (a2/h2)
- Knights get bonuses in the center and large penalties in the corners
- The King gets bonuses for staying on the kingside during the middlegame

**Mobility:** Number of legal moves × 2, encouraging piece development.

---

## Estimated Elo

Based on the engine's features, the estimated strength is approximately **1000-1300 Elo**:

- Alpha-Beta depth=5 + Quiescence: won't blunder pieces at a glance, but cannot calculate tactics beyond 3 moves deep
- Transposition table + Iterative deepening: efficient search, but the evaluation function lacks king safety and passed pawn considerations
- No killer moves / LMR: search efficiency still has room for improvement

## Possible Improvements

| Priority | Improvement | Expected Effect |
|----------|-------------|-----------------|
| 1 | King safety evaluation | Avoid voluntarily exposing the king |
| 2 | Killer Moves | Improve move ordering quality |
| 3 | Late Move Reductions (LMR) | Double search efficiency |
| 4 | Passed pawn evaluation | Stronger endgame play |
| 5 | Opening book | Avoid wasting time in the opening |

## Tech Stack

- **Language:** Python 3
- **Chess Logic:** [python-chess](https://github.com/niklasf/python-chess)
- **Frontend:** Pure HTML/CSS/JS + Unicode chess pieces, zero external dependencies
- **Backend:** Python built-in `http.server`

## License

MIT
