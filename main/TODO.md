# TODO - 从 qt 同步功能

这个文件记录 PySide6 版本 (qt/) 已经新增但 CustomTkinter 版本 (main/) 还未实现的功能，需要后续同步。

---

## 功能列表

### ✅ 已同步

- 暂无

### ⏳ 待同步

1. **饵料/钓具库存统计** - `qt/src/gui/bait_frame.py`
   - 功能：追踪饵料/钓具的购买、使用、剩余库存
   - 需要：在 main 中新增对应的界面和业务逻辑

2. **账号密码加密管理** - `qt/src/gui/credentials_frame.py`
   - 功能：加密存储账号密码，一键复制
   - 需要：在 main 中新增对应的界面和业务逻辑
   - 注意：加密逻辑可以复用 qt 中的 persistence

3. **数据分析增强** - `qt/src/gui/statistics_frame.py`
   - 原有 main 只有基础的三张图，qt 增强为四张图：
     - 每日收益：同时显示当日收益和累计收益两条线
     - 新增：按角色时长分布饼图
   - 需要：同步新的数据分析逻辑到 main

4. **安全增强 - 密码框固定显示****** ** - `qt/src/gui/credentials_frame.py`
   - 当前 main 显示 `*` 长度和密码实际长度一致，会暴露密码长度
   - qt 改为固定显示 6 个星号，更加安全
   - 需要：同步到 main

5. **输入验证和异常处理增强**
   - qt 中添加了更多输入验证，空值、非数字提示更友好
   - 需要：同步这些验证到 main

6. **活动统计增强** - `qt/src/gui/activity_frame.py`
   - 新增功能：查看历史记录（带日期筛选）、导出记录到CSV、从CSV导入历史数据
   - 也包括 `ActivityPersistence` 中新增的 `export_to_csv` 和 `import_from_csv` 方法
   - 需要：同步这些功能到 main

---

## 同步完成后请移走到 ✅ 已同步 区域
