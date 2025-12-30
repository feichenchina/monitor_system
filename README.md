# Server Monitor System

这是一个基于 Vue 3 (前端) 和 FastAPI (后端) 的AI服务器监控系统。

## 功能

1.  **机器管理**：新增、删除、查看服务器信息（IP、账号、密码）。
2.  **状态监控**：
    *   在线状态
    *   操作系统 (OS)
    *   架构 (x86_64/aarch64)
    *   加速卡信息 (NVIDIA/Huawei/AMD)
3.  **定时检测**：可设置检测频率。
4.  **数据持久化**：使用 SQLite 数据库。

## 快速开始

### 前置要求

*   Windows 系统
*   已安装 Python (推荐 3.8+)

### 启动

双击运行 `start.ps1` 脚本，或者在 PowerShell 中运行：

```powershell
.\start.ps1
```

脚本会自动：
1.  检查 Python 环境。
2.  安装所需依赖 (`fastapi`, `uvicorn`, `paramiko` 等)。
3.  启动后端服务。
4.  自动打开浏览器访问 `http://127.0.0.1:8000`。

## 项目结构

*   `backend/`: 后端代码 (FastAPI)
    *   `main.py`: 入口文件
    *   `models.py`: 数据库模型
    *   `monitor.py`: 监控逻辑 (SSH)
*   `frontend/`: 前端代码
    *   `index.html`: 单页应用 (Vue + Element Plus)
*   `start.ps1`: 启动脚本

## 注意事项

*   请确保运行脚本的机器可以 SSH 连接到目标服务器。
*   默认端口为 8000，如果被占用请修改 `start.ps1` 中的端口。
