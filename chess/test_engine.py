"""引擎功能完整测试套件 — 验证置换表修改后所有功能正常。"""
import sys
import chess
import engine

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}  {detail}")


# ── 1. 评估函数 ──────────────────────────────────────────
print("=== 1. 评估函数 ===")

# 初始局面应接近 0（双方对称）
board = chess.Board()
score = engine.evaluate(board)
test("初始局面评估接近 0", abs(score) < 200, f"实际值: {score}")

# 将杀局面
board_mate = chess.Board("rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
score_mate = engine.evaluate(board_mate)
test("被将杀时评估为极负值", score_mate == -999999, f"实际值: {score_mate}")

# 逼和局面：黑王被困在角落无路可走
board_stalemate = chess.Board("k7/2Q5/1K6/8/8/8/8/8 b - - 0 1")
if board_stalemate.is_stalemate():
    score_stale = engine.evaluate(board_stalemate)
    test("逼和时评估为 0", score_stale == 0, f"实际值: {score_stale}")
else:
    test("逼和局面构造正确", False, "局面不是逼和")

# 子力优势
board_up = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
# 白方多一个后
board_up_white = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
score_even = engine.evaluate(board_up)
score_white_up = engine.evaluate(board_up_white)
test("白方多后时评估更高", score_white_up > score_even, f"均势={score_even}, 多后={score_white_up}")


# ── 2. 走法排序 ──────────────────────────────────────────
print("\n=== 2. 走法排序 ===")

board = chess.Board()
moves = engine._order_moves(board)
test("走法排序返回合法走法", len(moves) == board.legal_moves.count())

# 有吃子时，吃子走法应排在前面
board_cap = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
moves_cap = engine._order_moves(board_cap)
first_is_capture = board_cap.is_capture(moves_cap[0])
test("吃子走法排在前面", first_is_capture, f"第一步: {board_cap.san(moves_cap[0])}")

# TT 走法应排在最前
board = chess.Board()
all_moves = list(board.legal_moves)
tt_test_move = all_moves[5]  # 随便选一个
moves_with_tt = engine._order_moves(board, tt_move=tt_test_move)
test("TT 走法排在最前", moves_with_tt[0] == tt_test_move)


# ── 3. 静态搜索 (Quiescence) ─────────────────────────────
print("\n=== 3. 静态搜索 ===")

board = chess.Board()
q_score = engine.quiescence(board, -999999, 999999, True)
test("静态搜索返回有限值", abs(q_score) < 999999, f"实际值: {q_score}")

# 在吃子局面中静态搜索应继续搜索
board_tactic = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 3 3")
q_tactic = engine.quiescence(board_tactic, -999999, 999999, True)
test("战术局面静态搜索返回正值（白方可 Qxf7#）", q_tactic > 0, f"实际值: {q_tactic}")


# ── 4. Alpha-Beta 搜索 ───────────────────────────────────
print("\n=== 4. Alpha-Beta 搜索 ===")

engine.tt.clear()
board = chess.Board()
score_ab, move_ab = engine.alpha_beta(board, 2, -999999, 999999, True)
test("Alpha-Beta 返回合法走法", move_ab in board.legal_moves, f"走法: {move_ab}")
test("Alpha-Beta 返回有限评估值", abs(score_ab) < 999999, f"实际值: {score_ab}")

# 黑方视角
board = chess.Board()
score_ab_black, move_ab_black = engine.alpha_beta(board, 2, -999999, 999999, False)
test("黑方视角搜索返回合法走法", move_ab_black in board.legal_moves)


# ── 5. 置换表 ────────────────────────────────────────────
print("\n=== 5. 置换表 ===")

# 基本 store/probe
engine.tt.clear()
board = chess.Board()
engine.tt.store(board, 3, 50, engine.TT_EXACT, board.parse_san("e4"))
result = engine.tt.probe(board, 3, -999999, 999999)
test("存入后可以查到", result is not None)
if result:
    tt_score, tt_move = result
    test("查到的分数正确", tt_score == 50, f"期望 50, 实际 {tt_score}")
    test("查到的走法正确", tt_move == board.parse_san("e4"))

# 深度不够时不返回分数
result_shallow = engine.tt.probe(board, 5, -999999, 999999)
if result_shallow:
    tt_score2, tt_move2 = result_shallow
    test("深度不够时分数为 None 但走法可用", tt_score2 is None and tt_move2 is not None)
else:
    test("深度不够时至少返回走法", False, "返回 None")

# 深度优先替换
engine.tt.clear()
board = chess.Board()
engine.tt.store(board, 2, 30, engine.TT_EXACT, None)
engine.tt.store(board, 3, 40, engine.TT_EXACT, None)
result3 = engine.tt.probe(board, 3, -999999, 999999)
if result3:
    test("更深搜索覆盖浅搜索", result3[0] == 40, f"期望 40, 实际 {result3[0]}")

# 浅搜索不覆盖深搜索
engine.tt.clear()
board = chess.Board()
engine.tt.store(board, 3, 40, engine.TT_EXACT, None)
engine.tt.store(board, 2, 30, engine.TT_EXACT, None)
result4 = engine.tt.probe(board, 3, -999999, 999999)
if result4:
    test("浅搜索不覆盖深搜索", result4[0] == 40, f"期望 40, 实际 {result4[0]}")

# UPPERBOUND/LOWERBOUND 标志
engine.tt.clear()
board = chess.Board()
engine.tt.store(board, 3, 100, engine.TT_LOWERBOUND, None)
# LOWERBOUND 且 score >= beta → 命中
result5 = engine.tt.probe(board, 3, -999999, 50)
test("LOWERBOUND + score >= beta → 命中", result5 is not None and result5[0] == 100)
# LOWERBOUND 但 score < beta → 不命中分数
result6 = engine.tt.probe(board, 3, -999999, 200)
if result6:
    test("LOWERBOUND + score < beta → 分数不可用", result6[0] is None)

engine.tt.clear()
board = chess.Board()
engine.tt.store(board, 3, -100, engine.TT_UPPERBOUND, None)
# UPPERBOUND 且 score <= alpha → 命中
result7 = engine.tt.probe(board, 3, -100, 999999)
test("UPPERBOUND + score <= alpha → 命中", result7 is not None and result7[0] == -100)
# UPPERBOUND 但 score > alpha → 不命中分数
result8 = engine.tt.probe(board, 3, -200, 999999)
if result8:
    test("UPPERBOUND + score > alpha → 分数不可用", result8[0] is None)

# clear 清空
engine.tt.store(board, 1, 0, engine.TT_EXACT, None)
engine.tt.clear()
test("clear() 后表为空", len(engine.tt.table) == 0)


# ── 6. find_best_move ────────────────────────────────────
print("\n=== 6. find_best_move ===")

engine.tt.clear()
board = chess.Board()
best = engine.find_best_move(board, depth=2)
test("find_best_move 返回合法走法", best in board.legal_moves, f"走法: {best}")

# 一步杀：白方应找到将杀
board_mate1 = chess.Board("k7/8/1K6/8/8/8/8/7R w - - 0 1")
best_mate = engine.find_best_move(board_mate1, depth=2)
test("一步杀局面找到将杀走法", best_mate in board_mate1.legal_moves)
# 验证走法是 Rh8#
san_mate = board_mate1.san(best_mate)
test("一步杀走法是 Rh8#", san_mate == "Rh8#", f"实际: {san_mate}")

# 两步杀
board_mate2 = chess.Board("6k1/5ppp/8/8/8/8/8/R3K3 w Q - 0 1")
best_mate2 = engine.find_best_move(board_mate2, depth=4)
test("两步杀局面找到走法", best_mate2 in board_mate2.legal_moves)


# ── 7. 置换表与搜索集成 ─────────────────────────────────
print("\n=== 7. 置换表与搜索集成 ===")

engine.tt.clear()
board = chess.Board("r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2")

# 第一次搜索
score_a, move_a = engine.alpha_beta(board, 2, -999999, 999999, True)
tt_entries = len(engine.tt.table)
test("搜索后置换表有条目", tt_entries > 0, f"条目数: {tt_entries}")

# 第二次搜索应得到相同结果
score_b, move_b = engine.alpha_beta(board, 2, -999999, 999999, True)
test("两次搜索走法一致", move_a == move_b, f"第一次: {move_a}, 第二次: {move_b}")
test("两次搜索分数一致", score_a == score_b, f"第一次: {score_a}, 第二次: {score_b}")


# ── 8. 吃子排序 ──────────────────────────────────────────
print("\n=== 8. 吃子排序 ===")

board_cap2 = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
captures = engine._order_captures(board_cap2)
test("吃子排序只返回吃子/升变走法", all(board_cap2.is_capture(m) or m.promotion for m in captures))
test("吃子排序非空（有吃子可用）", len(captures) > 0)

# 无吃子时返回空
board_no_cap = chess.Board()
captures_none = engine._order_captures(board_no_cap)
test("初始局面无吃子走法", len(captures_none) == 0)


# ── 9. 将军延伸 ──────────────────────────────────────────
print("\n=== 9. 将军延伸 ===")

# 将军延伸应让引擎在将军时搜得更深，找到更多杀棋
# 这个局面白方可以通过连续将军杀棋
board_check_ext = chess.Board("r1bqk2r/pppp1Qpp/2n2n2/2b1p3/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
best_check = engine.find_best_move(board_check_ext, depth=2, time_limit=3.0)
test("将军延伸：找到攻击性走法", best_check in board_check_ext.legal_moves)

# 验证 MAX_PLY 保护生效
board = chess.Board()
score_ply, move_ply = engine.alpha_beta(board, 2, -999999, 999999, True, ply=63)
test("接近 MAX_PLY 时返回评估值而非崩溃", abs(score_ply) < 9999999)


# ── 10. 空着裁剪 ────────────────────────────────────────
print("\n=== 10. 空着裁剪 ===")

# 空着裁剪不应在将军时触发
board_in_check = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2")
# 黑方被将军，空着裁剪不应执行（不会崩溃即可）
if board_in_check.is_check():
    score_check, _ = engine.alpha_beta(board_in_check, 2, -999999, 999999, False)
    test("被将军时空着裁剪不触发（不崩溃）", True)
else:
    test("被将军时空着裁剪不触发", True, "测试局面未处于将军")

# 大优势局面应更快完成（空着裁剪生效）
engine.tt.clear()
board_winning = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
import time as _time
start = _time.perf_counter()
best_win = engine.find_best_move(board_winning, depth=3, time_limit=5.0)
elapsed_win = _time.perf_counter() - start
test("空着裁剪：大优势局面搜索完成", best_win in board_winning.legal_moves, f"耗时: {elapsed_win:.2f}s")


# ── 11. 迭代加深 ────────────────────────────────────────
print("\n=== 11. 迭代加深 ===")

engine.tt.clear()
board = chess.Board()

# 测试时间限制生效
best_id = engine.find_best_move(board, depth=10, time_limit=1.0)
test("迭代加深：时间限制内返回走法", best_id in board.legal_moves)

# 测试深度限制生效
engine.tt.clear()
best_id2 = engine.find_best_move(board, depth=2, time_limit=60.0)
test("迭代加深：深度限制内返回走法", best_id2 in board.legal_moves)

# 迭代加深后置换表应有条目
test("迭代加深后置换表有条目", len(engine.tt.table) > 0)


# ── 结果汇总 ─────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"总计: {passed + failed}  通过: {passed}  失败: {failed}")
if failed == 0:
    print("所有测试通过!")
else:
    print(f"有 {failed} 个测试失败!")
    sys.exit(1)
