# Windows 服务化与启动脚本增强日志

## 1. 需求分析
- 实现 Windows 服务安装/卸载，支持静默启动和全用户自启，提升生产环境稳定性。
- 解决多实例启动导致的端口冲突。

## 2. 技术决策
- **服务包装器**: 参考 `proxy` 项目，使用 C# 编写简单的 Windows 服务包装器（Service Wrapper），在 `OnStart` 时通过 `pythonw.exe` 启动 FastAPI 后端，在 `OnStop` 时杀掉进程。
- **服务管理**: 使用 PowerShell 脚本自动化安装、卸载及清理。
- **静默启动**: 提供 `.vbs` 脚本供非服务模式下的静默运行。
- **端口检测**: 在启动 `uvicorn` 前通过 `socket` 检测端口占用。

## 3. 实现细节
- **服务安装/卸载**:
    - `install_as_service.ps1`: 自动检测 `pythonw.exe`，动态编译 C# 源码为 `bin/MonitorService.exe` 并安装。
    - `uninstall_service.ps1`: 停止、删除服务并清理 `bin/`。
- **自启动脚本**:
    - `install_autostart_all_users.ps1`: 在 `CommonStartup` 创建快捷方式，支持所有用户。
    - 路径优化: 使用 `$PSScriptRoot` 获取脚本所在目录，提高可移植性。
- **多实例预防**:
    - 修改 `backend/main.py`: 启动前检测端口（默认 8000），若占用则记录日志并静默退出。

## 4. 踩坑记录
- **权限问题**: 安装服务需要管理员权限，脚本中已加入权限检查提示。
- **前端路径**: 后端 `main.py` 依赖 `frontend/dist` 提供静态文件服务。若未编译前端，服务虽能启动但界面 404。已在安装脚本中加入检查。
- **乱码问题**: Windows 终端输出 ANSI 颜色代码可能导致乱码。
    - **修复**: 修改 `start.ps1` 显式设置编码为 UTF-8，设置 `$env:PYTHONIOENCODING = "utf-8"`，并为 `uvicorn` 添加 `--no-use-colors` 参数。
- **静默脚本失效**: `start_silent.vbs` 无法启动。
    - **修复**: 在 `backend/main.py` 底部添加 `if __name__ == "__main__":` 块，使其可以直接通过 `python` 启动。

## 5. 验证
- `install_as_service.ps1` 成功安装并启动服务。
- `uninstall_service.ps1` 成功卸载并清理环境。
- `start_silent.vbs` 可成功启动服务 (端口 8000)。
- `stop_monitor.ps1` 可成功关闭服务。

## 6. 日志时间
- 2026-02-24
