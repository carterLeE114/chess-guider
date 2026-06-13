import chess
import engine
import random


WHITE_OPENINGS = [
    ("e4", "王兵开局 (King's Pawn) — 最经典开局，控制中心，打开后和象的线路"),
    ("d4", "后兵开局 (Queen's Pawn) — 稳健占据中心，限制黑方兵推进"),
    ("Nf3", "列蒂开局 (Réti) — 灵活开局，保留多种兵型选择"),
    ("c4", "英国式开局 (English) — 侧翼控制中心，局面型选手首选"),
    ("g3", "王翼堡垒象开局 — 让白格象从侧翼控制大斜线"),
    ("e3", "反中心开局 — 先稳固中心再展开进攻"),
    ("b3", "拉尔森开局 (Larsen) — 用白格象控制长斜线和中心"),
    ("Nc3", "邓斯特开局 (Dunst) — 把选择权留给后续推进"),
]


def random_opening():
    opening = random.choice(WHITE_OPENINGS)
    return opening[0], opening[1]


def print_board(board):
    print()
    print("  +------------------------+")
    rank_labels = ["8", "7", "6", "5", "4", "3", "2", "1"]
    for rank in range(7, -1, -1):
        line = f"{rank_labels[7 - rank]} |"
        for file in range(8):
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            if piece:
                symbol = piece.symbol()
                line += f" {symbol} "
            else:
                line += " . "
        line += "|"
        print(line)
    print("  +------------------------+")
    print("    a  b  c  d  e  f  g  h")
    print()


def get_user_move(board):
    while True:
        try:
            user_input = input("请输入对手走法 (如 e4, Nf3, O-O, e8=Q，输入 'quit' 退出): ").strip()
            if user_input.lower() == "quit":
                return None
            move = board.parse_san(user_input)
            if move in board.legal_moves:
                return move
            else:
                print("非法走法，请重新输入。")
        except ValueError:
            print("格式错误，请使用标准代数记谱法 (如 e4, Nf3, O-O)。")


def game_result_message(board):
    if board.is_checkmate():
        winner = "黑方" if board.turn == chess.WHITE else "白方"
        return f"将杀！{winner}获胜！"
    if board.is_stalemate():
        return "逼和！"
    if board.is_insufficient_material():
        return "子力不足，和棋。"
    return None


def main():
    print("=" * 40)
    print("      国际象棋 AI 走棋顾问")
    print("=" * 40)
    print()

    while True:
        choice = input("请选择执子颜色 — 白方输入 w，黑方输入 b: ").strip().lower()
        if choice in ("w", "b"):
            break
        print("请输入 w 或 b。")

    user_color = chess.WHITE if choice == "w" else chess.BLACK
    color_name = "白方" if user_color == chess.WHITE else "黑方"
    print(f"\n你执{color_name}，AI 将为你提供走法建议。\n")

    board = chess.Board()

    if user_color == chess.WHITE:
        print("你执白方，先手。")
        print()
        print("可选开局方式：")
        print("  1 — 随机选一个好用的白方开局（推荐）")
        print("  2 — 让 AI 自动选择第一步")
        while True:
            opening_choice = input("请选择 (1 或 2): ").strip()
            if opening_choice == "1":
                san, desc = random_opening()
                print(f"\n随机开局: {san}")
                print(f"名称: {desc}")
                move = board.parse_san(san)
                board.push(move)
                print(f"第一步走: {san}")
                print_board(board)
                break
            elif opening_choice == "2":
                print("AI 正在思考...")
                move = engine.find_best_move(board, depth=3)
                san = board.san(move)
                board.push(move)
                print(f"AI 建议第一步: {san}")
                print_board(board)
                break
            else:
                print("请输入 1 或 2。")
    else:
        print_board(board)

    while not board.is_game_over():
        if board.turn == user_color:
            print("AI 正在思考你的下一步...")
            best_move = engine.find_best_move(board, depth=3)
            if best_move is None:
                print("无合法走法。")
                break
            san = board.san(best_move)
            board.push(best_move)
            print(f"建议你走: {san}")
            print_board(board)
        else:
            move = get_user_move(board)
            if move is None:
                print("游戏结束。")
                break
            san = board.san(move)
            board.push(move)
            print(f"对手走法: {san}")
            print_board(board)

    result = game_result_message(board)
    if result:
        print(result)

    print("感谢对弈！")


if __name__ == "__main__":
    main()
