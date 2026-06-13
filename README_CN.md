# Chess Guider - 国际象棋 AI 走棋顾问

[English](./README.md) | 中文

一个基于 Alpha-Beta 搜索的国际象棋 AI 引擎，提供命令行和浏览器两种界面，以**顾问模式**运行——AI 帮你走你执的颜色，你负责在棋盘上同步对手的走法。

## 项目结构

```
├── engine.py        # 搜索引擎核心（评估、搜索、置换表）
├── chess_ai.py      # 命令行界面
├── chess_web.py     # 浏览器网页界面（零外部依赖）
├── test_engine.py   # 引擎测试套件（40 项测试）
└── test_tt.py       # 置换表验证测试
```

## 快速开始

### 安装依赖

```bash
pip install chess
```

### 命令行模式

```bash
python chess_ai.py
```

选择执白 (w) 或执黑 (b)，AI 会建议你的每一步走法，你输入对手的走法即可。

### 浏览器模式

```bash
python chess_web.py
```

打开浏览器访问 `http://127.0.0.1:8080`，点击"执白"或"执黑"开始对弈。

## 顾问模式说明

与传统"人机对弈"不同，本程序以**顾问模式**运行：

| 场景 | 流程 |
|------|------|
| 执白 | AI 自动帮你走白方第一步 → 你输入黑方对手走法 → AI 建议白方下一步 → 循环 |
| 执黑 | 你输入白方对手走法 → AI 建议黑方下一步 → 你输入白方对手走法 → 循环 |

在浏览器界面中，你只需点击对手的棋子并拖到目标位置来输入对手走法，AI 会自动计算并执行你执颜色的走法。

---

## 算法详解

### 1. Alpha-Beta 剪枝搜索

核心搜索算法采用 Negamax 风格的 Alpha-Beta 剪枝。通过维护搜索窗口 `[alpha, beta]`，当某条分支的评估值超出窗口时直接剪掉，避免搜索明显劣于已有选择的分支。

```
alpha_beta(board, depth, alpha, beta, maximizing):
    if depth == 0: return quiescence(...)
    for move in ordered_moves:
        score = -alpha_beta(board, depth-1, -beta, -alpha, ...)
        if score >= beta: return beta  // beta 剪枝
        alpha = max(alpha, score)
    return alpha
```

### 2. 迭代加深 (Iterative Deepening)

从 depth=1 开始逐步加深搜索深度，直到达到最大深度或时间用完。

**优势：**
- 任何时刻都有可用走法，不会超时
- 上一轮的最佳走法存入置换表，为下一轮提供 PV move，大幅提升剪枝效率
- 浅层搜索的时间开销相比深层搜索可忽略不计

```python
for current_depth in range(1, max_depth + 1):
    score, move = alpha_beta(board, current_depth, ...)
    best_move = move  # 始终保留最新结果
    if elapsed > time_limit:
        break
```

默认参数：最大深度 5 层，时间限制 5 秒。

### 3. 静态搜索 (Quiescence Search)

当主搜索到达 depth=0 时，不直接返回静态评估，而是继续搜索所有吃子走法，直到局面"安静"（无更多吃子）。

**解决的问题：** 水平线效应 (Horizon Effect)——如果搜索刚好停在战术交换中间，评估值会严重失真。例如，白后吃黑车后搜索停止，但黑方可以回吃白后，实际是白方亏损。

```
quiescence(board, alpha, beta):
    stand_pat = evaluate(board)  // 不走子的静态评估
    if stand_pat >= beta: return beta
    for capture_move in ordered_captures:
        score = -quiescence(board after capture)
        if score >= beta: return beta
    return best_score
```

吃子走法按 **MVV-LVA** (Most Valuable Victim - Least Valuable Aggressor) 排序：优先搜索"小子吃大子"的走法。

### 4. 置换表 (Transposition Table)

基于 **Zobrist 哈希** 的置换表，存储已搜索局面的结果。同一局面可通过不同走法顺序到达（转置），置换表避免重复搜索。

**存储内容：** `(depth, score, flag, best_move)`

**三种标志：**
| 标志 | 含义 |
|------|------|
| `TT_EXACT` | 精确值（alpha < score < beta） |
| `TT_LOWERBOUND` | 下界（beta 剪枝，实际值 >= score） |
| `TT_UPPERBOUND` | 上界（未超过 alpha，实际值 <= score） |

**替换策略：** 深度优先——更深的搜索结果不会被浅结果覆盖。容量上限 100 万条目，超出时清空。

**双重用途：**
1. 深度足够时直接返回缓存分数（剪枝）
2. 深度不够时仍返回 `best_move` 用于走法排序（PV move）

### 5. 将军延伸 (Check Extension)

当走子后对方被将军时，搜索深度不减（等效于 +1 深度延伸）。

**原理：** 将军局面是强制性的（对方必须应将），信息密度高。不延伸容易漏算杀棋序列。同时由于应将选择很少，延伸不会显著增加搜索量。

**安全机制：** `ply` 参数追踪总搜索深度，`MAX_PLY=64` 防止连续将军导致无限递归。

### 6. 空着裁剪 (Null Move Pruning)

假设"跳过一步"（让对方连走两步），如果局面仍然 >= beta，说明当前优势巨大，直接剪掉该分支。

```
if allow_null and depth >= 3 and not in_check:
    board.push(null_move)
    null_score = -alpha_beta(board, depth-1-R, -beta, -beta+1, ...)
    board.pop()
    if null_score >= beta:
        return null_score  // 剪枝
```

**关键参数：**
- `NULL_MOVE_REDUCTION = 2`：空着搜索减少的深度
- 零窗口搜索 `(-beta, -beta+1)`：只验证是否 >= beta
- `allow_null=False`：防止连续空着
- 不在被将军时使用（被将时必须应将，空着无意义）

### 7. 走法排序 (Move Ordering)

走法排序质量直接决定 Alpha-Beta 剪枝效率。排序优先级从高到低：

| 优先级 | 走法类型 | 分数 |
|--------|----------|------|
| 1 | 置换表最佳走法 (TT move) | 1,000,000 |
| 2 | 吃子走法 (MVV-LVA) | 10 × 被吃子价值 - 攻击子价值 |
| 3 | 升变走法 | 后的价值 (900) |
| 4 | 其余走法 | 0 |

### 8. 评估函数

评估函数由三部分组成：

**子力价值：**
| 棋子 | 兵 | 马 | 象 | 车 | 后 | 王 |
|------|----|----|----|----|----|----|
| 分值 | 100 | 320 | 330 | 500 | 900 | 20000 |

**位置表 (Piece-Square Tables)：** 每种棋子在不同格子上有位置加成。例如：
- 兵在中心 (d4/e5) 有加成，在边线 (a2/h2) 无加成
- 马在中心有加成，在边角有大惩罚
- 王在中局待在王翼有加成

**机动性 (Mobility)：** 合法走法数 × 2，鼓励展开子力。

---

## 估算 Elo

基于引擎特征，估算约 **1000-1300 Elo**：

- Alpha-Beta depth=5 + Quiescence：不会一眼送子，但算不到 3 步以上的战术
- 置换表 + 迭代加深：搜索效率高，但评估函数缺少王安全和通路兵
- 无杀手走法 / LMR：搜索效率仍有提升空间

## 可能的改进方向

| 优先级 | 改进项 | 预期效果 |
|--------|--------|----------|
| 1 | 王安全评估 | 避免主动暴露王 |
| 2 | 杀手走法 (Killer Moves) | 提升走法排序质量 |
| 3 | 延迟走法缩减 (LMR) | 搜索效率翻倍 |
| 4 | 通路兵评估 | 残局更强 |
| 5 | 开局库 | 避免开局烧时间 |

## 技术栈

- **语言：** Python 3
- **棋局逻辑：** [python-chess](https://github.com/niklasf/python-chess)
- **前端：** 纯 HTML/CSS/JS + Unicode 棋子，零外部依赖
- **后端：** Python 内置 `http.server`

## 许可

MIT
