# 开发日志

## 2026-02-11
- **任务**: 项目重构初始化与代码分析
- **现状分析**:
    - **monitor-system**: 基于 FastAPI + Vue 3 的服务器监控系统。当前后端代码集中在 `backend/`，缺乏完善的日志系统（使用 print），启动脚本较为基础。
    - **参考项目 (proxy)**: 具有良好的目录结构（src, config, logs），实现了按日期+大小分割的日志系统，以及静默启动/自启脚本。
- **重构计划**:
    1.  **文档规范**: 建立 `DEV.md` 记录开发过程（已完成）。
    2.  **日志系统升级**: 参考 `proxy` 移植日志模块，替代 `print` 输出，支持日志轮转和持久化（已完成）。
    3.  **目录结构优化**: 规范化 `backend` 目录，区分代码、配置和日志（已完成初步结构调整）。
    4.  **启动脚本增强**: 参考 `proxy` 增加静默启动 (`.vbs`) 和优化 PowerShell 脚本。

## 2026-02-11
- **任务**: 移植日志系统
- **变更**:
    - 新增 `backend/logger.py`: 实现按大小(10MB)和日期(每天)轮转的日志系统。
    - 新增 `backend/logs/`: 存放日志文件。
    - 修改 `backend/main.py` & `backend/monitor.py`: 替换 `print` 为 `logger.info/error`，并在应用启动时初始化日志。
- **验证**:
    - 运行测试脚本，确认日志文件 `backend/logs/monitor_YYYY-MM-DD.log` 成功生成并写入日志。

- **任务**: 启动脚本增强
- **变更**:
    - 修正 `backend/main.py` 端口配置: 优先读取 `PORT` 环境变量，默认改为 `8000` (因 6000 端口被 X11 Server 占用)。
    - 新增 `start_silent.vbs`: 使用 `pythonw` 静默启动后端服务，适合生产环境后台运行。
    - 新增 `stop_monitor.ps1`: 自动查找并关闭后台运行的监控进程。
    - 编译前端: 执行 `npm run build` 生成 `frontend/dist`，确保后端可静态服务前端页面。
- **验证**:
    - `start_silent.vbs` 可成功启动服务 (端口 8000)。
    - `stop_monitor.ps1` 可成功关闭服务。

- **任务**: 前端数据刷新与界面优化
- **变更**:
    - 重构数据刷新逻辑: 引入 "Smart Merge" 机制，后台静默刷新时仅更新字段，避免全量替换导致的 DOM 闪烁。
    - 修复备注编辑冲突: 当用户聚焦备注输入框时 (`isEditingRemark=true`)，后台刷新将跳过该行备注字段的更新，防止用户输入被覆盖。
    - 优化 UI/UX:
        - 移除后台刷新时的表格 Loading 遮罩，提供丝滑的实时更新体验。
        - 重新设计表格样式 (Card 阴影、更清晰的表头、更好的间距)。
        - 优化备注输入框样式 (默认无边框，聚焦时显示边框)。
        - 优化密码显示和 Badge 样式。
        - **布局优化**: 移除主体宽度限制，使内容自适应占满屏幕宽度。
        - **细节美化**: 增加圆角 (Card/Button/Input)，优化阴影层次，统一色调 (Inter 字体)。
- **验证**:
    - 编译前端 (`npm run build`) 成功。
    - 验证逻辑：在刷新周期内编辑备注，输入内容未被重置；表格无闪烁。

- **任务**: 修复表单头部按钮布局
- **变更**:
    - 修改 `frontend/src/App.vue`: 恢复 `.card-header` 及相关 CSS 样式（Flex 布局），解决全屏优化后按钮垂直堆叠的问题。
    - 重新编译前端以应用修复。

- **任务**: 表格样式与分页优化
- **变更**:
    - 增加行距: 在 `.el-table .el-table__cell` 中增加 `padding: 12px 0`，解决行距过小的问题。
    - 优化卡状态列: 将“卡状态”列的 `width="220"` 改为 `min-width="250"`，防止内容在小屏幕或多状态下被截断。
    - 调整分页: 默认每页显示条数从 10 改为 20。
    - 修复卡状态高度截断: 新增 `.card-status-row` 样式，使用 `flex-wrap` 和 `padding` 确保 Badge 及其上标数字能完整显示。
    - 重新编译前端以应用更新。

- **任务**: 备注列宽与卡状态高度修复
- **变更**:
    - 备注列宽: 将 `width="200"` 改为 `min-width="300"`。
    - 卡状态高度修复: 增加 `padding: 8px 0` 到 `.card-status-row`，并设置 `.el-table .cell { overflow: visible !important; }` 以允许 Badge 溢出显示，彻底解决截断问题。
    - 重新编译前端。

- **任务**: 字体、输入框与性能优化
- **变更**:
    - **字体优化**: 将表格和全局字体大小调整为 `15px`，提升可读性。
    - **输入框美化**: 为搜索框和表单输入框增加明显的边框 (`box-shadow` inset)，并增强 Focus/Hover 状态，解决“输入框不明显”的问题。
    - **性能优化**: 
        - 为 `<el-table>` 增加 `row-key="id"`，帮助 Vue 更高效地复用 DOM 元素。
        - 优化 `fetchMachines` 的 Smart Merge 逻辑，在合并数据时直接更新现有对象属性并推入新列表，确保对象引用稳定且符合服务器排序，减少不必要的 DOM 重绘，解决“响应略有卡顿”的问题。
    - 重新编译前端。

- **任务**: 新增 IBMC 配置列 (IBMC IP / 密码)
- **变更**:
    - **后端**:
        - 修改 `Machine` 模型 (SQLModel)，新增 `ibmc_ip` 和 `ibmc_password` 字段。
        - 编写并执行 SQLite 迁移脚本 (`migrate_add_ibmc.py`) 更新数据库结构。
        - 更新 API (`main.py`) 支持新字段的接收与更新。
    - **前端**:
        - 在机器列表表格中新增 "IBMC IP" 和 "IBMC 密码" 列。
        - 实现 IBMC 密码的显隐切换功能。
        - 实现 IBMC 字段的即时保存逻辑 (`handleIbmcIpBlur`, `handleIbmcPasswordBlur`)，并集成到 Smart Merge 防止编辑冲突。
        - 更新 "新增机器" 和 "编辑机器" 对话框，加入 IBMC 相关输入框。
        - 更新 "导入/导出" 功能，支持 IBMC 字段的 CSV 处理。
    - 重新编译前端。

- **任务**: 用户名与密码列改为可编辑
- **变更**:
    - **前端**:
        - 将表格中的“用户名”列从文本展示改为 `el-input`，支持即时编辑与保存。
        - 将表格中的“密码”列改为 `el-input`，保留显/隐切换和复制功能，支持即时编辑与保存。
        - 实现 `handleUsernameBlur` 和 `handlePasswordBlur`，在输入框失焦时自动调用后端更新接口。
        - 更新 **Smart Merge** 逻辑，增加 `isEditingUsername` 和 `isEditingPassword` 状态判断，防止在后台刷新数据时覆盖用户正在编辑的内容。
    - 重新编译前端。

- **任务**: IBMC 密码列增加复制功能
- **变更**:
    - **前端**:
        - 在机器列表表格的 "IBMC 密码" 列中新增复制按钮，复用 `copyToClipboard` 方法。
    - 重新编译前端。

- **任务**: 增加全用户（All Users）自启动脚本
- **变更**:
    - **脚本**: 创建 `c:\monitor-system\install_autostart_all_users.ps1`。
        - 自动在 Windows **所有用户** 启动文件夹 (`CommonStartup`) 创建名为 `MonitorSystem.lnk` 的快捷方式。
        - 需要管理员权限运行。

- **任务**: 防止多实例启动（端口占用检测）
- **变更**:
    - **后端**: 修改 `backend/main.py` 的启动逻辑。
        - 在启动 `uvicorn` 前检测目标端口（默认 8000）是否已被占用。
        - 如果端口已被占用，则打印提示信息并静默退出（Exit Code 0），防止产生端口冲突错误或启动多余进程。

- **任务**: 端口占用检测日志化 & 自启动脚本路径优化
- **变更**:
    - **后端**: 修改 `backend/main.py`，在检测到端口占用退出前，将警告信息写入 `backend/logs/startup_error.log`（如果日志系统未就绪）或通过 `logger` 记录。
    - **脚本**: 优化 `install_autostart.ps1` 和 `install_autostart_all_users.ps1`。
        - 移除硬编码的 `c:\monitor-system` 路径。
        - 使用 `$PSScriptRoot` 获取脚本当前所在目录，作为快捷方式的目标路径和工作目录。这使得项目可以在任意目录下运行注册脚本，提高了可移植性。
        
## 2026-02-24
- **任务**: 项目重构与性能优化
- **变更**:
    - **后端重构**:
        - 拆分单体 `main.py` 为模块化结构：
            - `backend/database.py`: 数据库连接与会话管理。
            - `backend/routers/`: 路由模块化 (`machines.py`, `settings.py`)。
            - `backend/services/`: 业务逻辑层 (`monitor_service.py`)。
            - `backend/scheduler.py`: 调度器实例。
        - 移除 `backend/monitor.py`，相关逻辑迁移至 `monitor_service.py` 并优化。
    - **性能优化**:
        - 在 `monitor_service.py` 中引入 `ThreadPoolExecutor`，实现多线程并行检测机器状态，大幅缩短全量刷新时间。
        - 优化 `parse_nvidia_output` 和 `parse_huawei_output` 解析逻辑，提高代码可读性与健壮性。
- **验证**:
    - 通过 `python -m py_compile` 验证重构后的代码语法正确性。
    - 验证新目录结构下的模块导入正常。

## 2026-02-24 (Part 2)
- **任务**: 修复前端资源托管问题 (404 Not Found)
- **问题**: 用户启动服务后访问 `http://localhost:8000/` 出现 404 错误，原因是后端未配置静态文件托管，且前端未构建。
- **变更**:
    - **前端构建**: 执行 `npm run build` 生成 `frontend/dist` 目录。
    - **后端更新**: 修改 `backend/main.py`，增加 `StaticFiles` 挂载逻辑：
        - 将 `/assets` 路径映射到 `frontend/dist/assets`。
        - 将根路径 `/` 及其他未匹配路径映射到 `frontend/dist/index.html` (支持 SPA 路由)。
    - **启动脚本增强**: 更新 `start.ps1`，增加自动检测逻辑：如果 `frontend/dist` 不存在且环境中有 `npm`，则自动执行构建。
- **验证**:
    - 手动构建前端成功。
    - 验证 `backend/main.py` 代码逻辑正确。
    - 预期结果：重启服务后，访问 `http://localhost:8000/` 将正常显示前端页面。

## 2026-02-24 (Part 3)
- **任务**: 修复静默启动脚本并完善入口逻辑
- **变更**:
    - **后端入口**: 在 `backend/main.py` 底部添加 `if __name__ == "__main__":` 块，使其可以直接通过 `python backend/main.py` 启动，修复了 `start_silent.vbs` 无法启动服务的问题。
- **验证**:
    - 检查 `backend/main.py` 代码，确认入口逻辑正确。
    - 确认 `start_silent.vbs` 调用方式与入口逻辑匹配。
    
## 2026-02-24 (Part 4)
- **任务**: 修复控制台输出乱码问题
- **问题**: 在部分 Windows 终端环境中，Uvicorn 输出的 ANSI 颜色代码显示为 `?[32m` 等乱码字符。
- **变更**:
    - **启动脚本更新**: 修改 `start.ps1`。
        - 显式设置控制台输出编码为 UTF-8 (`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`)。
        - 设置环境变量 `$env:PYTHONIOENCODING = "utf-8"`。
        - 为 `uvicorn` 命令添加 `--no-use-colors` 参数，禁用 ANSI 颜色输出以彻底解决乱码问题。
- **验证**:
    - 重启服务后，控制台输出应为纯文本，无乱码字符。

## 2026-02-24 (Part 5)
- **任务**: 修复备注、IBMC IP 和 IBMC 密码保存失败的问题
- **问题**: 前端尝试调用 `PUT /machines/{id}` 接口更新字段，但后端缺少对应的 API 路由，导致请求失败 (405/404)。
- **变更**:
    - **后端模型 (`backend/models.py`)**: 新增 `MachineUpdate` 模型，定义允许更新的字段（ip, port, username, password, remark, ibmc_ip, ibmc_password）。
    - **后端路由 (`backend/routers/machines.py`)**: 新增 `PUT /machines/{machine_id}` 接口，支持增量更新机器信息。
- **验证**:
    - 检查代码逻辑，确认 `PUT` 请求能正确映射到数据库更新操作。
    - 前端无需修改，重试保存操作应成功。
