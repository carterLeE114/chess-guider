"""国际象棋 AI 网页界面 — 用浏览器打开即可对弈。"""
import json
import chess
import engine
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── 游戏状态 ────────────────────────────────────────────
game = {
    "board": chess.Board(),
    "user_color": chess.WHITE,
}


def new_game(user_color_str):
    game["board"] = chess.Board()
    game["user_color"] = chess.WHITE if user_color_str == "w" else chess.BLACK


def get_ai_move():
    board = game["board"]
    if board.is_game_over():
        return None
    move = engine.find_best_move(board, depth=5, time_limit=5.0)
    if move is None:
        return None
    san = board.san(move)
    board.push(move)
    return {
        "uci": move.uci(),
        "san": san,
    }


def make_user_move(uci_str):
    board = game["board"]
    try:
        move = chess.Move.from_uci(uci_str)
        if move not in board.legal_moves:
            # 尝试自动补全升变
            if move.promotion is None:
                for promo in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
                    promo_move = chess.Move(move.from_square, move.to_square, promotion=promo)
                    if promo_move in board.legal_moves:
                        move = promo_move
                        break
            if move not in board.legal_moves:
                return None
        san = board.san(move)
        board.push(move)
        return {"uci": move.uci(), "san": san}
    except (ValueError, chess.InvalidMoveError):
        return None


def get_game_state():
    board = game["board"]
    result = None
    if board.is_checkmate():
        winner = "black" if board.turn == chess.WHITE else "white"
        result = f"checkmate_{winner}"
    elif board.is_stalemate():
        result = "stalemate"
    elif board.is_insufficient_material():
        result = "insufficient"
    elif board.can_claim_draw():
        result = "draw_claim"
    elif board.is_fifty_moves():
        result = "fifty_moves"

    return {
        "fen": board.fen(),
        "turn": "w" if board.turn == chess.WHITE else "b",
        "is_check": board.is_check(),
        "is_game_over": board.is_game_over(),
        "result": result,
        "user_color": "w" if game["user_color"] == chess.WHITE else "b",
        "legal_moves": [m.uci() for m in board.legal_moves],
    }


# ── HTML 前端 ───────────────────────────────────────────
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国际象棋 AI</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #1a1a2e; color: #e0e0e0;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh;
  }
  .container {
    display: flex; gap: 32px; align-items: flex-start;
    padding: 24px; max-width: 1100px;
  }
  .board-wrap { flex-shrink: 0; }
  .panel {
    width: 300px; display: flex; flex-direction: column; gap: 16px;
  }
  .card {
    background: #16213e; border-radius: 12px; padding: 20px;
    border: 1px solid #0f3460;
  }
  .card h3 {
    font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
    color: #7a8ba6; margin-bottom: 12px;
  }
  .status {
    font-size: 18px; font-weight: 600; text-align: center;
    padding: 8px; border-radius: 8px;
  }
  .status.check { background: #e94560; color: #fff; }
  .status.thinking { background: #0f3460; color: #53a8b6; }
  .status.over { background: #533483; color: #fff; }
  .status.normal { background: #16213e; color: #e0e0e0; }
  .btn {
    display: block; width: 100%; padding: 12px;
    border: none; border-radius: 8px; font-size: 15px;
    font-weight: 600; cursor: pointer; transition: all 0.2s;
  }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: #0f3460; color: #53a8b6; }
  .btn-primary:hover:not(:disabled) { background: #1a4a8a; }
  .btn-white { background: #e0e0e0; color: #1a1a2e; }
  .btn-white:hover:not(:disabled) { background: #fff; }
  .btn-black { background: #333; color: #e0e0e0; border: 1px solid #555; }
  .btn-black:hover:not(:disabled) { background: #444; }
  .color-picker { display: flex; gap: 8px; }
  .color-picker .btn { flex: 1; }
  .move-list {
    max-height: 240px; overflow-y: auto; font-family: monospace;
    font-size: 14px; line-height: 1.8;
  }
  .move-list .move-num { color: #7a8ba6; }
  .move-list .white-move { color: #e0e0e0; }
  .move-list .black-move { color: #53a8b6; }
  .move-list::-webkit-scrollbar { width: 4px; }
  .move-list::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 2px; }
  .ai-info { font-size: 14px; color: #53a8b6; text-align: center; min-height: 20px; }
  .spinner {
    display: inline-block; width: 16px; height: 16px;
    border: 2px solid #53a8b6; border-top-color: transparent;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .welcome { text-align: center; }
  .welcome h2 { font-size: 22px; margin-bottom: 8px; color: #53a8b6; }
  .welcome p { color: #7a8ba6; margin-bottom: 20px; font-size: 14px; }

  /* ── 棋盘样式 ── */
  .chess-board {
    display: grid;
    grid-template-columns: repeat(8, 60px);
    grid-template-rows: repeat(8, 60px);
    border: 3px solid #0f3460;
    border-radius: 4px;
    user-select: none;
  }
  .chess-square {
    display: flex; align-items: center; justify-content: center;
    font-size: 42px; cursor: pointer; position: relative;
    transition: background 0.1s;
  }
  .chess-square.light { background: #eeeed2; }
  .chess-square.dark { background: #769656; }
  .chess-square.selected { background: #f6f669 !important; }
  .chess-square.legal-target::after {
    content: ''; position: absolute;
    width: 18px; height: 18px; border-radius: 50%;
    background: rgba(0,0,0,0.2);
  }
  .chess-square.legal-capture { box-shadow: inset 0 0 0 4px rgba(0,0,0,0.2); }
  .chess-square.last-move { background: rgba(255,255,100,0.4) !important; }
  .chess-square.check-square { background: #e94560 !important; }
  .rank-labels, .file-labels {
    display: flex; font-size: 12px; color: #7a8ba6;
  }
  .rank-labels {
    flex-direction: column; justify-content: space-around;
    padding-right: 6px; height: 484px;
  }
  .file-labels {
    justify-content: space-around;
    padding-top: 4px; width: 484px; margin-left: 18px;
  }
  .rank-labels span, .file-labels span {
    width: 60px; text-align: center;
  }
  .rank-labels span { width: auto; }
  .board-row { display: flex; }
  .piece-white { color: #fff; text-shadow: 0 0 2px #000, 0 0 2px #000, 1px 1px 1px #000; }
  .piece-black { color: #222; text-shadow: 0 0 1px rgba(255,255,255,0.3); }
</style>
</head>
<body>
<div class="container">
  <div class="board-wrap">
    <div class="board-row">
      <div class="rank-labels" id="rankLabels"></div>
      <div>
        <div class="chess-board" id="board"></div>
        <div class="file-labels" id="fileLabels"></div>
      </div>
    </div>
  </div>
  <div class="panel">
    <div class="card" id="welcomeCard">
      <div class="welcome">
        <h2>国际象棋 AI</h2>
        <p>选择你的执子颜色开始对弈</p>
        <div class="color-picker">
          <button class="btn btn-white" onclick="startGame('w')">执白</button>
          <button class="btn btn-black" onclick="startGame('b')">执黑</button>
        </div>
      </div>
    </div>
    <div class="card" id="statusCard" style="display:none">
      <h3>状态</h3>
      <div id="statusText" class="status normal">你的回合</div>
      <div id="aiInfo" class="ai-info"></div>
    </div>
    <div class="card" id="moveCard" style="display:none">
      <h3>走法记录</h3>
      <div id="moveList" class="move-list"></div>
    </div>
    <div class="card" id="controlCard" style="display:none">
      <button class="btn btn-primary" onclick="undoMove()">悔棋</button>
      <button class="btn btn-primary" style="margin-top:8px" onclick="showWelcome()">新游戏</button>
    </div>
  </div>
</div>

<script>
// ── Unicode 棋子映射 ──
const PIECE_UNICODE = {
  'K': '\u2654', 'Q': '\u2655', 'R': '\u2656', 'B': '\u2657', 'N': '\u2658', 'P': '\u2659',
  'k': '\u265A', 'q': '\u265B', 'r': '\u265C', 'b': '\u265D', 'n': '\u265E', 'p': '\u265F'
};

let currentFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR';
let userColor = 'w';
let orientation = 'w'; // 'w' = white at bottom
let moveHistory = [];
let isOpponentTurn = false; // true = 等待用户输入对手走法
let gameActive = false;
let selectedSquare = null;
let legalMoves = [];
let lastMoveFrom = null;
let lastMoveTo = null;
let kingInCheck = null;

function fenToBoard(fen) {
  const rows = fen.split(' ')[0].split('/');
  const board = [];
  for (const row of rows) {
    const boardRow = [];
    for (const ch of row) {
      if (ch >= '1' && ch <= '8') {
        for (let i = 0; i < parseInt(ch); i++) boardRow.push(null);
      } else {
        boardRow.push(ch);
      }
    }
    board.push(boardRow);
  }
  return board;
}

function squareName(row, col) {
  const file = String.fromCharCode(97 + col);
  const rank = 8 - row;
  return file + rank;
}

function renderBoard() {
  const boardEl = document.getElementById('board');
  boardEl.innerHTML = '';
  const board = fenToBoard(currentFen);

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const displayR = orientation === 'b' ? 7 - r : r;
      const displayC = orientation === 'b' ? 7 - c : c;

      const sq = document.createElement('div');
      const isLight = (displayR + displayC) % 2 === 0;
      sq.className = 'chess-square ' + (isLight ? 'light' : 'dark');
      sq.dataset.row = displayR;
      sq.dataset.col = displayC;

      const sqName = squareName(displayR, displayC);

      // 高亮上一步
      if (sqName === lastMoveFrom || sqName === lastMoveTo) {
        sq.classList.add('last-move');
      }
      // 高亮将军
      if (kingInCheck && sqName === kingInCheck) {
        sq.classList.add('check-square');
      }
      // 高亮选中
      if (selectedSquare && sqName === selectedSquare) {
        sq.classList.add('selected');
      }
      // 合法目标
      if (selectedSquare) {
        const isTarget = legalMoves.some(m => {
          const from = m.substring(0, 2);
          const to = m.substring(2, 4);
          return from === selectedSquare && to === sqName;
        });
        if (isTarget) {
          const piece = board[displayR][displayC];
          sq.classList.add(piece ? 'legal-capture' : 'legal-target');
        }
      }

      const piece = board[displayR][displayC];
      if (piece) {
        const span = document.createElement('span');
        span.textContent = PIECE_UNICODE[piece];
        span.className = piece === piece.toUpperCase() ? 'piece-white' : 'piece-black';
        sq.appendChild(span);
      }

      sq.addEventListener('click', () => onSquareClick(sqName));
      boardEl.appendChild(sq);
    }
  }

  // 标签
  const rankEl = document.getElementById('rankLabels');
  const fileEl = document.getElementById('fileLabels');
  rankEl.innerHTML = '';
  fileEl.innerHTML = '';
  for (let i = 0; i < 8; i++) {
    const rankNum = orientation === 'b' ? i + 1 : 8 - i;
    const fileChar = orientation === 'b' ? String.fromCharCode(104 - i) : String.fromCharCode(97 + i);
    rankEl.innerHTML += `<span>${rankNum}</span>`;
    fileEl.innerHTML += `<span>${fileChar}</span>`;
  }
}

function onSquareClick(sqName) {
  if (!gameActive || !isOpponentTurn) return;

  if (selectedSquare) {
    // 尝试走子（输入对手走法）
    const uci = selectedSquare + sqName;
    tryOpponentMove(uci, selectedSquare, sqName);
  } else {
    // 选中对手棋子
    const board = fenToBoard(currentFen);
    const row = 8 - parseInt(sqName[1]);
    const col = sqName.charCodeAt(0) - 97;
    const piece = board[row][col];
    if (piece && isOpponentPiece(piece)) {
      selectedSquare = sqName;
      renderBoard();
    }
  }
}

function isOpponentPiece(piece) {
  // 对手的棋子：如果用户执白，对手是黑方（小写）
  if (userColor === 'w') return piece === piece.toLowerCase();
  return piece === piece.toUpperCase();
}

function tryOpponentMove(uci, from, to) {
  fetch('/api/move', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({uci: uci})
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      currentFen = data.fen;
      lastMoveFrom = from;
      lastMoveTo = to;
      kingInCheck = data.state.is_check ? findKing(data.fen) : null;
      selectedSquare = null;
      addMoveToHistory(data.san, data.turn_before);
      isOpponentTurn = false;
      renderBoard();
      updateStatus(data.state);
      if (!data.state.is_game_over) aiSuggestMove();
    } else {
      // 尝试升变
      tryPromotions(from, to);
    }
  });
}

function tryPromotions(from, to) {
  const promos = ['q', 'r', 'b', 'n'];
  let tried = 0;
  function tryNext() {
    if (tried >= promos.length) {
      selectedSquare = null;
      renderBoard();
      return;
    }
    const uci = from + to + promos[tried];
    tried++;
    fetch('/api/move', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({uci: uci})
    })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        currentFen = data.fen;
        lastMoveFrom = from;
        lastMoveTo = to;
        kingInCheck = data.state.is_check ? findKing(data.fen) : null;
        selectedSquare = null;
        addMoveToHistory(data.san, data.turn_before);
        isOpponentTurn = false;
        renderBoard();
        updateStatus(data.state);
        if (!data.state.is_game_over) aiSuggestMove();
      } else {
        tryNext();
      }
    });
  }
  tryNext();
}

function findKing(fen) {
  const board = fenToBoard(fen);
  const turn = fen.split(' ')[1];
  const target = turn === 'w' ? 'K' : 'k';
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      if (board[r][c] === target) return squareName(r, c);
    }
  }
  return null;
}

function aiSuggestMove() {
  setStatus('thinking', 'AI 正在为你思考...');
  document.getElementById('aiInfo').innerHTML = '<span class="spinner"></span>AI 正在计算';

  fetch('/api/ai_move', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      if (data.move) {
        currentFen = data.fen;
        const uci = data.move.uci;
        lastMoveFrom = uci.substring(0, 2);
        lastMoveTo = uci.substring(2, 4);
        kingInCheck = data.state.is_check ? findKing(data.fen) : null;
        addMoveToHistory(data.move.san, data.turn_before);
      }
      isOpponentTurn = true;
      selectedSquare = null;
      renderBoard();
      updateStatus(data.state);
      const colorLabel = userColor === 'w' ? '白方' : '黑方';
      document.getElementById('aiInfo').textContent = data.move
        ? 'AI 建议 ' + colorLabel + ' 走: ' + data.move.san : '';
    });
}

function startGame(color) {
  userColor = color;
  orientation = color;
  moveHistory = [];
  selectedSquare = null;
  lastMoveFrom = null;
  lastMoveTo = null;
  kingInCheck = null;
  document.getElementById('moveList').innerHTML = '';
  document.getElementById('aiInfo').textContent = '';

  fetch('/api/new_game', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({color: color})
  })
  .then(r => r.json())
  .then(data => {
    gameActive = true;
    currentFen = data.fen;
    legalMoves = data.legal_moves;
    renderBoard();
    document.getElementById('welcomeCard').style.display = 'none';
    document.getElementById('statusCard').style.display = '';
    document.getElementById('moveCard').style.display = '';
    document.getElementById('controlCard').style.display = '';

    if (color === 'w') {
      // 用户执白：AI 先帮白方走第一步
      isOpponentTurn = false;
      aiSuggestMove();
    } else {
      // 用户执黑：等待用户输入白方对手的走法
      isOpponentTurn = true;
      setStatus('normal', '请输入对手(白方)走法');
    }
  });
}

function undoMove() {
  fetch('/api/undo', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        currentFen = data.fen;
        legalMoves = data.state.legal_moves;
        lastMoveFrom = null;
        lastMoveTo = null;
        kingInCheck = null;
        moveHistory.pop();
        moveHistory.pop();
        renderMoveHistory();
        // 悔棋后回到对手输入状态
        isOpponentTurn = true;
        selectedSquare = null;
        renderBoard();
        updateStatus(data.state);
        document.getElementById('aiInfo').textContent = '';
      }
    });
}

function showWelcome() {
  gameActive = false;
  document.getElementById('welcomeCard').style.display = '';
  document.getElementById('statusCard').style.display = 'none';
  document.getElementById('moveCard').style.display = 'none';
  document.getElementById('controlCard').style.display = 'none';
}

function addMoveToHistory(san, turnBefore) {
  moveHistory.push({san: san, turn: turnBefore});
  renderMoveHistory();
}

function renderMoveHistory() {
  const el = document.getElementById('moveList');
  let html = '';
  for (let i = 0; i < moveHistory.length; i++) {
    const m = moveHistory[i];
    if (m.turn === 'w') {
      const num = Math.floor(i / 2) + 1;
      html += `<span class="move-num">${num}.</span> `;
      html += `<span class="white-move">${m.san}</span> `;
    } else {
      if (i === 0) {
        html += `<span class="move-num">1.</span> `;
        html += `<span class="move-num">...</span> `;
      }
      html += `<span class="black-move">${m.san}</span> `;
    }
  }
  el.innerHTML = html;
  el.scrollTop = el.scrollHeight;
}

function setStatus(type, text) {
  const el = document.getElementById('statusText');
  el.className = 'status ' + type;
  el.textContent = text;
}

function updateStatus(state) {
  if (!state) return;
  legalMoves = state.legal_moves;
  if (state.is_game_over) {
    if (state.result && state.result.startsWith('checkmate_')) {
      const winner = state.result === 'checkmate_white' ? '白方' : '黑方';
      setStatus('over', '将杀! ' + winner + '获胜!');
    } else if (state.result === 'stalemate') {
      setStatus('over', '逼和!');
    } else {
      setStatus('over', '和棋!');
    }
    gameActive = false;
    return;
  }
  if (state.is_check) {
    setStatus('check', '将军!');
  } else if (isOpponentTurn) {
    const opponentLabel = userColor === 'w' ? '黑方' : '白方';
    setStatus('normal', '请输入对手(' + opponentLabel + ')走法');
  }
}

// 初始渲染
renderBoard();
</script>
</body>
</html>
"""


# ── HTTP 服务器 ─────────────────────────────────────────
class ChessHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/state":
            self._send_json(get_game_state())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/new_game":
            body = self._read_body()
            new_game(body.get("color", "w"))
            self._send_json(get_game_state())

        elif self.path == "/api/move":
            body = self._read_body()
            state_before = get_game_state()
            result = make_user_move(body.get("uci", ""))
            if result:
                state = get_game_state()
                self._send_json({
                    "ok": True,
                    "san": result["san"],
                    "fen": state["fen"],
                    "turn_before": state_before["turn"],
                    "state": state,
                })
            else:
                self._send_json({"ok": False})

        elif self.path == "/api/ai_move":
            state_before = get_game_state()
            move = get_ai_move()
            state = get_game_state()
            self._send_json({
                "move": move,
                "fen": state["fen"],
                "turn_before": state_before["turn"],
                "state": state,
            })

        elif self.path == "/api/undo":
            board = game["board"]
            undone = 0
            # 撤销两步（用户 + AI）
            while undone < 2 and len(board.move_stack) > 0:
                board.pop()
                undone += 1
            state = get_game_state()
            self._send_json({"ok": undone > 0, "fen": state["fen"], "state": state})

        else:
            self.send_error(404)


def main():
    port = 8080
    server = HTTPServer(("127.0.0.1", port), ChessHandler)
    print(f"国际象棋 AI 已启动: http://127.0.0.1:{port}")
    print("按 Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
        server.server_close()


if __name__ == "__main__":
    main()
