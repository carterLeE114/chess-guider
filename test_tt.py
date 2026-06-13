"""测试置换表是否生效：对同一局面搜索两次，对比耗时和命中情况。"""
import time
import chess
import engine

# 经典中局局面，有丰富的战术变化
FEN = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"

board = chess.Board(FEN)
print(f"测试局面 FEN: {FEN}")
print(f"当前置换表大小: {len(engine.tt.table)}")
print()

# 第一次搜索（冷启动，置换表为空）
engine.tt.clear()
start = time.perf_counter()
score1, move1 = engine.alpha_beta(board, 3, -999999, 999999, board.turn == chess.WHITE)
elapsed1 = time.perf_counter() - start
tt_size_after_first = len(engine.tt.table)
print(f"第 1 次搜索 (冷启动):")
print(f"  最佳走法: {board.san(move1)}  评估值: {score1}")
print(f"  耗时: {elapsed1:.4f}s")
print(f"  置换表条目数: {tt_size_after_first}")
print()

# 第二次搜索（置换表已填充）
start = time.perf_counter()
score2, move2 = engine.alpha_beta(board, 3, -999999, 999999, board.turn == chess.WHITE)
elapsed2 = time.perf_counter() - start
tt_size_after_second = len(engine.tt.table)
print(f"第 2 次搜索 (置换表命中):")
print(f"  最佳走法: {board.san(move2)}  评估值: {score2}")
print(f"  耗时: {elapsed2:.4f}s")
print(f"  置换表条目数: {tt_size_after_second}")
print()

# 结果对比
speedup = elapsed1 / elapsed2 if elapsed2 > 0 else float("inf")
print("=" * 50)
print(f"加速比: {speedup:.2f}x")
print(f"走法一致: {move1 == move2}")
print(f"评估值一致: {score1 == score2}")
print()

# 验证：手动查询置换表根节点
root_result = engine.tt.probe(board, 3, -999999, 999999)
if root_result:
    tt_score, tt_move = root_result
    print(f"根节点置换表命中: 分数={tt_score}, 走法={board.san(tt_move) if tt_move else None}")
else:
    print("根节点置换表未命中（不应发生）")
