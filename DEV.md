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
    - 修正 `backend/main.py` 端口配置: 优先读取 `PORT` 环境变量，默认改为 `9000` (因 6000 端口被 X11 Server 占用)。
    - 新增 `start_silent.vbs`: 使用 `pythonw` 静默启动后端服务，适合生产环境后台运行。
    - 新增 `stop_monitor.ps1`: 自动查找并关闭后台运行的监控进程。
    - 编译前端: 执行 `npm run build` 生成 `frontend/dist`，确保后端可静态服务前端页面。
- **验证**:
    - `start_silent.vbs` 可成功启动服务 (端口 9000)。
    - `stop_monitor.ps1` 可成功关闭服务。

