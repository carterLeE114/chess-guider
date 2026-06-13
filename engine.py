import chess
import chess.polyglot
import time

# ── 置换表标志 ──────────────────────────────────────────
TT_EXACT = 0      # 精确值
TT_LOWERBOUND = 1 # 下界（beta 剪枝产生）
TT_UPPERBOUND = 2 # 上界（未超过 alpha 产生）


class TranspositionTable:
    """基于 Zobrist 哈希的置换表，存储已搜索局面的结果以避免重复计算。"""

    def __init__(self, max_size=1_000_000):
        self.table = {}
        self.max_size = max_size

    def store(self, board, depth, score, flag, best_move):
        """将一个局面的搜索结果存入置换表。"""
        key = chess.polyglot.zobrist_hash(board)
        existing = self.table.get(key)
        # 深度优先替换策略：新结果深度 >= 旧结果深度时才覆盖
        if existing and existing[0] > depth:
            return
        self.table[key] = (depth, score, flag, best_move)
        # 超出容量时清空（简单策略，实际引擎可用 LRU 或分代替换）
        if len(self.table) > self.max_size:
            self.table.clear()

    def probe(self, board, depth, alpha, beta):
        """查询置换表。命中且深度足够时返回 (score, best_move)，否则返回 None。"""
        key = chess.polyglot.zobrist_hash(board)
        entry = self.table.get(key)
        if entry is None:
            return None

        tt_depth, tt_score, tt_flag, tt_move = entry

        # 深度不够，不能直接使用分数，但可以返回 best_move 用于走法排序
        if tt_depth < depth:
            return (None, tt_move)

        if tt_flag == TT_EXACT:
            return (tt_score, tt_move)
        if tt_flag == TT_LOWERBOUND and tt_score >= beta:
            return (tt_score, tt_move)
        if tt_flag == TT_UPPERBOUND and tt_score <= alpha:
            return (tt_score, tt_move)

        # 分数不可用，但走法仍可用于排序
        return (None, tt_move)

    def clear(self):
        self.table.clear()


# 全局置换表实例
tt = TranspositionTable()

# ── 搜索参数 ────────────────────────────────────────────
MAX_PLY = 64              # 最大搜索深度（防止将军延伸无限递归）
NULL_MOVE_REDUCTION = 2   # 空着裁剪减少的搜索深度


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

PAWN_TABLE = (
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
)

KNIGHT_TABLE = (
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
)

BISHOP_TABLE = (
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
)

ROOK_TABLE = (
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
)

QUEEN_TABLE = (
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
)

KING_MIDDLE_TABLE = (
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
)

PIECE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_MIDDLE_TABLE,
}


def _pst_index(square, is_white):
    if is_white:
        return 56 - (square // 8) * 8 + (square % 8)
    return square


def evaluate(board):
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -999999
        return 999999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        value = PIECE_VALUES[piece.piece_type]
        pst_value = PIECE_TABLES[piece.piece_type][_pst_index(square, piece.color == chess.WHITE)]

        if piece.color == chess.WHITE:
            score += value + pst_value
        else:
            score -= value + pst_value

    mobility_white = 0
    mobility_black = 0
    board_copy = board.copy()
    board_copy.turn = chess.WHITE
    mobility_white = len(list(board_copy.legal_moves))
    board_copy.turn = chess.BLACK
    mobility_black = len(list(board_copy.legal_moves))
    score += (mobility_white - mobility_black) * 2

    return score


def _order_moves(board, tt_move=None):
    moves = list(board.legal_moves)

    def move_priority(move):
        score = 0
        # 置换表最佳走法优先级最高
        if tt_move and move == tt_move:
            return 1000000
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            aggressor = board.piece_at(move.from_square)
            if victim and aggressor:
                score += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[aggressor.piece_type]
        if move.promotion:
            score += PIECE_VALUES[chess.QUEEN]
        return score

    moves.sort(key=move_priority, reverse=True)
    return moves


def _order_captures(board):
    """只收集吃子和升变走法，并按 MVV-LVA 排序。"""
    capture_moves = []
    for move in board.legal_moves:
        if board.is_capture(move) or move.promotion:
            capture_moves.append(move)

    def capture_priority(move):
        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            aggressor = board.piece_at(move.from_square)
            if victim and aggressor:
                score += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[aggressor.piece_type]
        if move.promotion:
            score += PIECE_VALUES[chess.QUEEN]
        return score

    capture_moves.sort(key=capture_priority, reverse=True)
    return capture_moves


def quiescence(board, alpha, beta, maximizing):
    """静态搜索：在深度为 0 后继续搜索吃子走法，直到局面"安静"，
    避免因截断而忽略正在进行的战术交换（水平线效应）。"""
    stand_pat = evaluate(board)

    if maximizing:
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat
        for move in _order_captures(board):
            board.push(move)
            score = quiescence(board, alpha, beta, False)
            board.pop()
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        return alpha
    else:
        if stand_pat <= alpha:
            return alpha
        if stand_pat < beta:
            beta = stand_pat
        for move in _order_captures(board):
            board.push(move)
            score = quiescence(board, alpha, beta, True)
            board.pop()
            if score < beta:
                beta = score
            if alpha >= beta:
                break
        return beta


def alpha_beta(board, depth, alpha, beta, maximizing, ply=0, allow_null=True):
    # 最大深度保护
    if ply >= MAX_PLY:
        return evaluate(board), None

    if board.is_game_over():
        return evaluate(board), None
    if depth <= 0:
        return quiescence(board, alpha, beta, maximizing), None

    # 置换表查询
    orig_alpha = alpha
    tt_result = tt.probe(board, depth, alpha, beta)
    tt_move = None
    if tt_result is not None:
        tt_score, tt_move = tt_result
        if tt_score is not None:
            return tt_score, tt_move

    # ── 空着裁剪 ──
    # 条件：深度足够、不在将军中、允许空着、不是根节点附近
    if allow_null and depth >= 3 and ply > 0 and not board.is_check():
        board.push(chess.Move.null())
        # 零窗口搜索，深度减少 R
        null_score, _ = alpha_beta(board, depth - 1 - NULL_MOVE_REDUCTION,
                                    -beta, -beta + 1, not maximizing,
                                    ply + 1, allow_null=False)
        null_score = -null_score
        board.pop()

        if null_score >= beta:
            return null_score, None

    best_move = None

    if maximizing:
        max_eval = -999999
        moves = _order_moves(board, tt_move)
        for move in moves:
            board.push(move)
            # 将军延伸：走子后对方被将军时不减深度
            ext = 1 if board.is_check() else 0
            eval_score, _ = alpha_beta(board, depth - 1 + ext, alpha, beta,
                                        False, ply + 1)
            board.pop()
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if alpha >= beta:
                break

        # 存入置换表
        if max_eval <= orig_alpha:
            flag = TT_UPPERBOUND
        elif max_eval >= beta:
            flag = TT_LOWERBOUND
        else:
            flag = TT_EXACT
        tt.store(board, depth, max_eval, flag, best_move)
        return max_eval, best_move
    else:
        min_eval = 999999
        moves = _order_moves(board, tt_move)
        for move in moves:
            board.push(move)
            ext = 1 if board.is_check() else 0
            eval_score, _ = alpha_beta(board, depth - 1 + ext, alpha, beta,
                                        True, ply + 1)
            board.pop()
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if alpha >= beta:
                break

        # 存入置换表
        if min_eval >= beta:
            flag = TT_LOWERBOUND
        elif min_eval >= orig_alpha:
            flag = TT_EXACT
        else:
            flag = TT_UPPERBOUND
        tt.store(board, depth, min_eval, flag, best_move)
        return min_eval, best_move


def find_best_move(board, depth=5, time_limit=5.0):
    """迭代加深搜索：从 depth=1 逐步加深，直到达到最大深度或超时。
    每一轮的搜索结果会存入置换表，为下一轮提供更好的走法排序。"""
    start = time.perf_counter()
    best_move = None
    best_score = None

    for current_depth in range(1, depth + 1):
        # 已用时间超过限制则停止加深
        elapsed = time.perf_counter() - start
        if elapsed > time_limit and current_depth > 1:
            break

        score, move = alpha_beta(board, current_depth, -999999, 999999,
                                  board.turn == chess.WHITE)
        if move is not None:
            best_move = move
            best_score = score

        # 如果已用超过一半时间，下一轮大概率超时，提前退出
        elapsed = time.perf_counter() - start
        if elapsed > time_limit * 0.5 and current_depth < depth:
            break

    return best_move
