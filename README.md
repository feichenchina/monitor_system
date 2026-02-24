# Server Monitor System

这是一个基于 Vue 3 (前端) 和 FastAPI (后端) 的AI服务器监控系统。

## 功能

1.  **机器管理**：
    *   新增、删除、编辑服务器信息（IP、账号、密码）。
    *   支持批量导入/导出机器列表 (CSV)。
    *   支持标记“自有”机器。
    *   支持 IBMC IP 和密码管理。
2.  **状态监控**：
    *   **实时状态**：通过 IP 颜色直观显示在线（绿色）、离线（灰色）或错误（红色）状态。
    *   **硬件信息**：操作系统 (OS)、架构 (x86_64/aarch64)。
    *   **加速卡监控**：实时监控 NVIDIA/Huawei/AMD 加速卡状态（显存、温度、健康状况）。
    *   **卡状态概览**：直观展示闲置、忙碌、异常的卡数量。
3.  **便捷操作**：
    *   支持一键复制 IP、密码、IBMC 信息。
    *   支持直接在表格中编辑备注、用户名、密码等字段。
    *   支持按 IP、用户、卡型号搜索，以及按架构、状态、卡类型筛选。
4.  **系统特性**：
    *   **定时检测**：可自定义检测频率。
    *   **数据持久化**：使用 SQLite 数据库。
    *   **高性能**：后端使用线程池并发检测，前端使用智能合并策略减少重绘。

## 快速开始

### 前置要求

*   Windows 系统
*   已安装 Python (推荐 3.8+)
*   已安装 Node.js (用于编译前端)

### 1. 编译前端 (首次运行必做)

在运行系统之前，需要先编译前端项目：

```powershell
cd frontend
npm install
npm run build
cd ..
```

### 2. 启动服务 (手动)

双击运行 `start.ps1` 脚本，或者在 PowerShell 中运行：

```powershell
.\start.ps1
```

脚本会自动：
1.  检查 Python 环境。
2.  安装所需依赖 (`fastapi`, `uvicorn`, `paramiko` 等)。
3.  启动后端服务。
4.  自动打开浏览器访问 `http://127.0.0.1:8000`。

### 3. 安装为 Windows 服务 (推荐生产环境)

为了让系统在开机时自动后台运行（无需登录），可以将其安装为 Windows 服务。

**以管理员权限运行 PowerShell**，然后执行：

```powershell
.\install_as_service.ps1
```

安装成功后，系统将以 `MonitorSystem` 服务名在后台运行。

**卸载服务：**

```powershell
.\uninstall_service.ps1
```

## 其他操作

*   **静默启动 (临时)**: 使用 `start_silent.vbs` 在后台运行而不显示控制台。
*   **停止服务**: 运行 `stop_monitor.ps1`。

## 项目结构

*   `backend/`: 后端代码 (FastAPI)
    *   `main.py`: 入口文件
    *   `models.py`: 数据库模型
    *   `routers/`: API 路由模块
    *   `services/`: 业务逻辑服务
    *   `monitor_service.py`: 核心监控逻辑 (SSH/Paramiko)
*   `frontend/`: 前端代码
    *   `src/`: Vue 源代码
*   `start.ps1`: 启动脚本
*   `DEV.md`: 开发日志

## 注意事项

*   请确保运行脚本的机器可以 SSH 连接到目标服务器。
*   默认端口为 8000，如果被占用请修改 `start.ps1` 中的端口。
*   如需重新编译前端代码：
    ```bash
    cd frontend
    npm run build
    ```
