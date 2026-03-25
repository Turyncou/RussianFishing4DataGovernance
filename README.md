# Russian Fishing 4 数据统计与活动推荐

完整的 Python 钓鱼数据追踪 + 活动优化推荐桌面应用。

## 项目简介

这是为 **Russian Fishing 4** 制作的综合性数据管理工具，包含两个主要部分：

1. **核心活动调度优化** - 基于贪心算法，根据不同活动类型（A 需要专注 / B 可以并行）给出每日最优收益组合
2. **完整 CustomTkinter GUI 桌面应用** - 提供数据统计、转盘抽奖、窝子计时、桌面悬浮提醒等功能

## 功能特性

### 核心调度优化
- **两种活动类型**:
  - Type A: 单次活动，需要全神贯注，同一时间只能做一个
  - Type B: 可以并行活动，支持用户配置最大并发数
- **两种优化模式**:
  - 最大收益：填满所有可用时间，追求最高收益
  - 均衡模式：留出休息时间，限制 A 类活动占比不超过 60%
- **切换开销** - 自动计算 15-20 分钟切换开销
- **文件监听** - 自动监听数据文件变化，自动重新计算推荐

### GUI 桌面应用
- 📊 **搬砖统计** - 多角色银币/时间统计，每日追踪，目标进度条
- ⏱️ **窝子计时** - 每个钓鱼点累计耗时统计，可随时增减时间
- 🔄 **转盘抽奖** - 可配置奖品转盘，随机抽奖
- 🔗 **友情链接** - 可编辑好友直播链接，一键打开
- 🐱 **三只小猫** - 主窗口右下角三只小猫，眼睛/头部跟随鼠标移动
- 🖼 **自定义背景** - 支持自定义背景图片，透明度调整
- 💬 **桌面悬浮提醒** - 独立悬浮窗，定时提醒休息/喝水/作息，气泡尖端正对模型，点击任意位置关闭
- 📋 **活动推荐** - 集成核心调度算法，展示推荐结果
- 📦 **可打包单文件 exe** - 使用 PyInstaller 打包，可在无 Python 环境运行

## 项目架构

```
RussianFishing4DataGovernance/
├── data/                               # 输出数据目录（程序自动创建）
│   ├── activities.csv                 # 活动定义
│   └── user.json                      # 用户配置
├── main/
│   └── src/
│       ├── core/                     # GUI 业务逻辑层
│       │   ├── __init__.py
│       │   ├── data_manager.py       # 统一 JSON 持久化，自动备份
│       │   ├── lucky_draw.py        # 转盘抽奖业务逻辑
│       │   ├── grinding_stats.py    # 搬砖统计业务逻辑
│       │   ├── storage_tracking.py # 窝子计时业务逻辑
│       │   ├── friend_links.py     # 友情链接业务逻辑
│       │   ├── background.py       # 背景设置业务逻辑
│       │   └── activity_scheduler.py # GUI 集成封装
│       ├── gui/                     # CustomTkinter GUI 界面
│       │   ├── __init__.py
│       │   ├── activity_frame.py    # 活动统计主界面
│       │   └── desktop_reminder.py  # 桌面悬浮气泡提醒
│       └── main.py                  # GUI 应用入口
├── src/
│   └── activity_scheduler/             # 核心调度包（可独立使用）
│       ├── __init__.py
│       ├── api.py                    # 公开 API，支持编程调用
│       ├── types.py                  # 数据类型定义
│       ├── exceptions.py             # 自定义异常
│       ├── data_loader.py            # CSV/JSON 数据加载
│       └── optimizer.py              # 优化算法实现
├── tests/                           # 单元测试（TDD 流程）
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_data_persistence.py
│   ├── test_lucky_draw.py
│   ├── test_grinding_stats.py
│   ├── ... (所有模块都有对应测试)
│   └── test_activity_scheduler.py
├── build.spec                        # PyInstaller 打包 spec
├── requirements.txt                  # pip 依赖列表
├── pyproject.toml                    # Poetry 配置
├── CLAUDE.md                         # 开发指引
└── README.md                         # 本文档
```

## 各文件具体作用

| 层级 | 文件 | 作用 |
|------|------|------|
| **activity_scheduler** | `api.py` | 公开 `ActivityScheduler` API，支持**添加/删除活动**，**更新配置**，**获取推荐**，**启动文件自动监听** |
| **activity_scheduler** | `types.py` | 定义所有核心数据类：`Activity`, `ActivityType`, `UserConfig`, `ScheduleItem`, `ScheduleResult`, `OptimizationResults` |
| **activity_scheduler** | `exceptions.py` | 自定义异常：`NoValidScheduleError`, `InvalidActivityError` 等 |
| **activity_scheduler** | `data_loader.py` | 从 CSV/JSON 加载并验证数据，检查格式错误 |
| **activity_scheduler** | `optimizer.py` | 实现两种贪心优化算法：`_optimize_for_max_gain()` 最大收益，`_optimize_for_balanced()` 均衡 |
| **core** | `data_manager.py` | 集中管理所有 JSON 数据持久化，**自动创建备份**，保证数据安全 |
| **core** | `lucky_draw.py` | 转盘抽奖业务逻辑，概率归一化，奖品管理 |
| **core** | `grinding_stats.py` | 多角色每日银币/时长统计，进度百分比计算 |
| **core** | `storage_tracking.py` | 多钓鱼点时间追踪，支持增减时间 |
| **core** | `friend_links.py` | 好友链接增删改，URL 有效性验证 |
| **core** | `background.py` | 背景图片路径透明度存储 |
| **gui** | `activity_frame.py` | 主界面活动统计，包含标签/进度条/表格/对话框 |
| **gui** | `desktop_reminder.py` | **桌面悬浮提醒窗口** - 圆形占位（未来替换 Live2D），气泡尖端平滑连接圆形，固定距离紧贴模型，定时提醒，右键菜单配置 |
| **main** | `main.py` | GUI 主入口，创建主窗口，整合所有功能 |

## 运行方式

### 核心调度单独使用

```python
from activity_scheduler import ActivityScheduler

scheduler = ActivityScheduler("data/activities.csv", "data/user.json")
results = scheduler.optimize()

# 获取最大收益推荐
print(f"最大收益 总价值: {results.maximum_gain.total_value:.1f}")
for item in results.maximum_gain.schedule:
    print(f"  {item.activity.activity_name} - {item.end_time - item.start_time} min")
```

### 运行完整 GUI 应用

```bash
pip install -r requirements.txt
python main/src/main.py
```

### 打包单文件 exe

```bash
pyinstaller build.spec
```

输出在 `dist/` 文件夹，得到单文件 `RF4DataTracker.exe`，可复制到没有 Python 的 Windows 机器直接运行。

## 算法原理

### 最大收益策略
1. 按 **每分钟价值密度** 降序排序所有活动
2. 优先放入 A 类活动（需要专注，通常价值密度高）
3. 剩余时间用 B 类活动填满（可并行）
4. 自动计算切换活动的时间开销

### 均衡策略
1. 限制 A 类活动总时长不超过可用时间 60%
2. 留出足够休息时间
3. 选择价值密度较高的混合安排

## 约束条件
- A 类活动不能重叠，同一时间只能一个
- B 类活动不能超过用户配置的最大并发数
- 切换不同活动需要 15-20 分钟切换开销
- 总时长不能超过用户配置的每日可用时间

## 桌面悬浮提醒特性

`desktop_reminder.py` 最近重构优化：

✅ **气泡尖端紧贴模型** - 无论气泡内容多少，尖端始终保持固定距离紧贴圆形模型
✅ **气泡尖端平滑融合** - 尖端和气泡框同色，没有突兀边界
✅ **点击任意位置关闭** - 点击气泡任何位置都能关闭
✅ **不显示在任务栏** - 使用 Windows API `WS_EX_TOOLWINDOW` + `~WS_EX_APPWINDOW`，只在主程序图标显示，不单独占用位置
✅ **参数全可配置** - 所有尺寸都提取为类属性，未来替换不同大小模型只需修改几个常数

## 开发

遵循 **测试驱动开发 (TDD)**: 先写测试，再写实现，保证所有功能都有覆盖。
