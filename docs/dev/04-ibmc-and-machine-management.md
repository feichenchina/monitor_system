# IBMC 配置与机器管理功能增强日志

## 1. 需求分析
- 完善 IBMC 管理功能（IP、账号、密码、一键跳转）。
- 支持标记机器“自有”状态。
- 提供机器列表排序和导入/导出功能。

## 2. 技术方案
- **数据库扩展**: 使用 SQLModel 修改 `Machine` 模型。
- **SQLite 迁移**: 编写并执行 SQLite 迁移脚本 (`migrate_add_ibmc.py`, `migrate_add_is_own.py`, `migrate_add_ibmc_username.py`)。
- **前端实时编辑**: 使用 `@blur` 事件监听输入框失焦，自动调用 `PUT /machines/{id}` 接口。

## 3. 实现细节
- **IBMC 支持**:
    - 新增字段: `ibmc_ip`, `ibmc_username`, `ibmc_password`.
    - 前端新增对应的列和输入框。
    - **IBMC IP 跳转**: 在输入有效 IP 后显示蓝色跳转图标，点击打开 `https://<IP>/`。
- **“自有”机器标记**:
    - `is_own` (Boolean) 字段。
    - 前端展示: “状态”列显示“自有”绿色标签 (`el-tag`)。
- **导入/导出**:
    - 实现 CSV 导入导出逻辑，支持所有新增字段。
- **排序优化**:
    - 修改后端 `read_machines` 接口，增加 `.order_by(Machine.ip)`，确保按 IP 字符串升序排列。

## 4. 踩坑记录
- **SQLite 迁移约束**: SQLite 不支持 `ALTER TABLE ... ADD COLUMN` 添加非空约束，需谨慎处理默认值。
- **Smart Merge 漏掉 is_own**: 最初未在刷新逻辑中更新 `is_own`，导致前端数据未刷新。已补全。
- **编辑保存失败 (405)**: 后端路由缺少 `PUT /machines/{id}`。已补全 `MachineUpdate` 模型及路由。

## 5. 验证
- 数据库迁移成功。
- 前端页面正确显示各列。
- 列表页直接编辑 IBMC 账号/密码/IP 可自动保存。
- 排序效果符合预期。

## 6. 日志时间
- 2026-02-24, 2026-03-11
