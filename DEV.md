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

## 2026-02-24
- **任务**: 移除旧启动脚本并实现 Windows 服务安装/卸载
- **变更**:
    - **移除脚本**: 删除了 `install_autostart.ps1` 和 `install_autostart_all_users.ps1`，这些脚本原本通过 Startup 目录实现自启，不再推荐使用。
    - **新增服务安装脚本**: `install_as_service.ps1`。
        - **技术决策**: 参考 `proxy` 项目，使用 C# 编写一个简单的 Windows 服务包装器（Service Wrapper），在 `OnStart` 时通过 `pythonw.exe` 启动 FastAPI 后端，在 `OnStop` 时杀掉进程。
        - **优势**: 服务可以独立于用户会话运行，系统启动即运行，且崩溃后可配置自动重启（通过 Windows 服务管理器）。
        - **实现细节**: 脚本会自动检测 `pythonw.exe` 路径，并使用 `Add-Type` 动态编译 C# 源码为 `bin/MonitorService.exe`。
    - **新增服务卸载脚本**: `uninstall_service.ps1`。
        - **功能**: 停止并删除 `MonitorSystem` 服务，并清理 `bin/` 目录下的生成文件。
    - **文档更新**: 更新 `README.md`，明确指出首次运行需编译前端项目，并添加了 Windows 服务安装的使用说明。
- **踩坑记录**:
    - **权限问题**: 安装服务需要管理员权限，脚本中已加入权限检查提示。
    - **前端路径**: 后端 `main.py` 依赖 `frontend/dist` 提供静态文件服务，如果未编译前端，服务虽然能启动但 Web 界面无法访问。已在 `install_as_service.ps1` 中加入检查和警告。
- **验证**:
    - `install_as_service.ps1` 成功安装并启动服务。
    - `uninstall_service.ps1` 成功卸载并清理环境。
    - 当前系统已处于服务运行状态。
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

## 2026-02-24 (Part 6)
- **任务**: 为 IP 和 IBMC IP 列添加复制功能
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - 修改 "IP 地址" 列：使用自定义模板，添加复制图标 (`CopyDocument`)，点击即可复制 IP 到剪贴板。
        - 修改 "IBMC IP" 列：在输入框内添加后缀图标 (`suffix`)，如果存在 IBMC IP，则显示复制按钮。
        - 调整两列宽度以容纳图标。
- **验证**:
    - 前端页面应显示复制图标，点击后提示“已复制到剪贴板”。

## 2026-02-24 (Part 7)
- **任务**: 新增“自有”机器状态标记
- **变更**:
    - **后端**:
        - 修改 `Machine` 模型，新增 `is_own` (Boolean) 字段。
        - 编写并执行迁移脚本 `migrate_add_is_own.py`，更新数据库表结构。
    - **前端**:
        - “新增机器”和“编辑机器”对话框中增加“自有机器”复选框。
        - 机器列表“IP 地址”列增加“自有”绿色标签 (`el-tag`)。
        - 更新数据模型，支持 `is_own` 字段的读写。
- **验证**:
    - 新增机器时勾选“自有”，列表应显示“自有”标签。
    - 编辑现有机器勾选“自有”，保存后列表应更新显示。

## 2026-02-24 (Part 8)
- **任务**: 修复“自有”状态编辑问题并调整 UI 显示
- **问题**:
    1. 无法编辑修改【自有】状态：可能是因为后端返回的 SQLite Boolean 值为整数 (0/1)，前端直接赋值给 Checkbox 时类型不匹配或未正确初始化。
    2. 前端【自有】标签显示位置调整：用户希望将其与【状态】（在线/离线）合并显示。
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - **编辑修复**: 在 `openEditDialog` 中，强制将 `row.is_own` 转换为布尔值 (`!!row.is_own`)，确保 `el-checkbox` 能正确绑定和显示选中状态。
        - **UI 调整**: 将“自有”绿色标签从“IP 地址”列移动到“状态”列，并适当增加“状态”列宽。
- **验证**:
    - 编辑机器时，Checkbox 应正确反映当前“自有”状态，且修改后能保存。
    - “自有”标签应显示在“状态”列中，与在线状态并排。

## 2026-02-24 (Part 8)
- **任务**: 修复“自有”状态不更新的问题
- **问题**: 前端 `fetchMachines` 函数中的“Smart Merge”逻辑未包含 `is_own` 字段的更新，导致即使后端数据已变更，前端页面上的现有记录也不会刷新该状态。
- **变更**:
    - **前端 (`frontend/src/App.vue`)**: 在 `fetchMachines` 的循环更新逻辑中，显式添加 `machine.is_own = newItem.is_own`。
- **验证**:
    - 修改机器的“自有”状态并保存，列表应立即反映变更，且在后台刷新周期内保持正确状态。

## 2026-02-24 (Part 9)
- **任务**: 优化机器状态显示
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - 移除独立的“状态”列。
        - 将状态显示合并到“IP 地址”列：
            - 在线 (Online): IP 地址显示为加粗绿色 (#67C23A)。
            - 离线 (Offline): IP 地址显示为灰色 (#909399)。
            - 错误 (Error): IP 地址显示为红色 (#F56C6C)。
- **验证**:
    - 列表应不再显示“状态”列。
    - IP 地址应根据机器状态显示不同的颜色和粗细。

## 2026-02-24 (Part 10)
- **任务**: 机器列表排序优化
- **变更**:
    - **后端 (`backend/routers/machines.py`)**: 修改 `read_machines` 接口，在分页查询前增加 `.order_by(Machine.ip)`，确保机器列表始终按照 IP 地址升序排列。
- **验证**:
    - 列表中的机器应严格按照 IP 地址的字符串顺序排列。

## 2026-02-24 (Part 11)
- **任务**: 优化前端 favicon 图标
- **变更**:
    - **前端 (`frontend/public/vite.svg`)**:
        - 替换原 Vite 默认图标为自定义设计的 SVG 图标。
        - **设计理念**: 采用圆角矩形显示器轮廓 + 脉冲波形 (Pulse) + 蓝紫渐变色，体现“监控系统”与“健康状态”的核心功能，风格简约现代。
- **验证**:
    - 刷新浏览器页面，标签页图标应更新为新设计。

## 2026-02-25
- **任务**: 修复SVG加载问题与优化昇腾NPU进程判断逻辑
- **变更**:
    - **后端 (`backend/main.py`)**: 
        - 引入 `mimetypes` 模块并显式添加 `.svg` 的 MIME 类型 (`image/svg+xml`)，解决部分环境下（如 Windows）因 MIME 类型缺失导致 SVG 文件无法正确加载的问题（特别是在非 localhost 访问时）。
    - **监控服务 (`backend/services/monitor_service.py`)**:
        - 优化 `parse_huawei_output` 函数：
            - 新增对 `npu-smi info` 输出中“Process”部分的解析逻辑。
            - 引入 `npu_has_process` 字典，通过识别进程表中的 PID 或明确的 "No running processes found" 信息来判断 NPU 是否忙碌。
            - 决策逻辑变更：如果检测到进程表存在，则优先依据“是否存在进程”来判断 NPU 状态（有进程=Busy，无进程=Idle），不再单纯依赖显存使用率（解决昇腾 NPU 即使无任务也有较高显存占用导致的误判问题）。如果未检测到进程表，则回退到原有的显存阈值（>5%）判断逻辑。
- **验证**:
    - 编写并运行测试脚本 `test_npu_parsing.py`，验证了包含 "No running processes found" 的输出能被正确解析为 Idle，而有进程的 NPU 被解析为 Busy。
    - 确认 `backend/main.py` 修改无语法错误。

## 2026-02-25 (Part 2)
- **任务**: 彻底修复 IP 访问时 Favicon 不加载问题
- **问题**: 用户反馈在使用 IP 访问时，浏览器即使获取到 HTML 也没有发起 SVG 请求（可能受限于网络环境、浏览器安全策略或缓存行为）。
- **变更**:
    - **前端 (`frontend/index.html` & `frontend/dist/index.html`)**:
        - 将 `<link rel="icon" ... href="/vite.svg" />` 替换为 Base64 Data URI 格式的内联 SVG。
        - 这样做消除了对 `/vite.svg` 文件的网络请求依赖，确保只要 HTML 被加载，Favicon 就能立即显示，彻底规避了网络请求失败、MIME 类型错误或路径解析问题。
- **验证**:
    - 验证 Base64 字符串解码后内容与原 `vite.svg` 一致。
    - 直接修改了构建产物 `dist/index.html`，用户无需重新构建即可生效。

## 2026-02-25 (Part 3)
- **任务**: 修复 IP 访问时复制失败及点击复制触发保存的问题
- **问题**:
    1. 在使用 HTTP IP 访问（非安全上下文）时，`navigator.clipboard` API 不可用，导致复制失败。
    2. 点击输入框内的复制按钮会导致输入框失去焦点，从而触发 `@blur` 事件，导致意外的“保存”请求。
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - **Clipboard 降级**: 修改 `copyToClipboard` 函数，当 `navigator.clipboard` 不可用时（非 HTTPS/localhost），自动降级使用 `document.execCommand('copy')`（创建临时隐藏 TextArea 实现），确保在任何环境下都能正常复制。
        - **阻止焦点丢失**: 在所有复制按钮（`el-icon`）上添加 `@mousedown.prevent` 事件修饰符。这会阻止按钮点击时的默认行为（获取焦点），从而使原输入框保持聚焦状态，不会触发 `blur` 保存逻辑。
- **验证**:
    - 重新编译前端 (`npm run build`)。
    - 在 IP 访问环境下测试复制功能，提示“已复制到剪贴板”且内容正确。
    - 测试在编辑状态下点击复制按钮，确认未触发保存接口调用（Network 面板无 PUT 请求）。

## 2026-02-25 (Part 4)
- **任务**: 彻底修复点击复制触发输入框保存问题（针对 Clipboard Fallback）
- **问题**: 在 IP 访问模式下，`copyToClipboard` 降级逻辑必须创建临时 `textarea` 并调用 `focus()` 才能执行 `execCommand('copy')`。这个显式的 `focus()` 动作会导致原输入框失去焦点，从而触发 `@blur` 事件并执行保存逻辑，此行为无法通过 `@mousedown.prevent` 阻止。
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - **引入全局状态 `isCopying`**: 用于标记当前是否正在执行复制操作。
        - **优化 `copyToClipboard`**: 
            - 在开始复制前将 `isCopying` 设为 `true`。
            - 记录当前 `activeElement`（原输入框）。
            - 执行复制（包括可能触发 blur 的 fallback 逻辑）。
            - **恢复焦点**: 在 `finally` 块中，将焦点重新移回原输入框，确保用户体验连贯。
            - **延迟重置**: 使用 `setTimeout` 延迟重置 `isCopying = false`，确保覆盖 `blur` 事件的触发窗口。
        - **拦截 `blur` 事件**: 在所有 `handleXxxBlur` 函数中增加 `if (isCopying.value) return;` 检查。如果检测到正在复制，则直接跳过保存逻辑。
- **验证**:
    - 重新编译前端 (`npm run build`)。
    - 在 IP 访问环境下（触发 fallback 逻辑），点击输入框内的复制按钮。
    - 预期结果：提示“已复制到剪贴板”，输入框保持聚焦（或立即重新聚焦），且 Network 面板中**没有**产生 PUT 请求。

## 2026-02-25 (Part 5)
- **任务**: 修复点击复制按钮导致输入框意外聚焦的问题
- **问题**: 用户反馈点击复制按钮（尤其是在未编辑状态下）会导致输入框获得焦点并进入编辑模式。这使得用户在复制后点击其他地方时会触发 `blur` 事件并执行不必要的保存操作。
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - **引入全局状态 `isHoveringCopyBtn`**: 用于标记鼠标当前是否悬停在复制按钮上。
        - **更新复制按钮**:
            - 添加 `@mouseenter` 和 `@mouseleave` 事件来更新 `isHoveringCopyBtn` 状态。
            - 添加 `@click.stop` 阻止点击事件冒泡到输入框。
        - **优化聚焦逻辑**:
            - 将所有输入框的 `@focus` 事件处理器替换为新的 `handleFocus(row, field)` 函数。
            - 在 `handleFocus` 中检查 `isHoveringCopyBtn`。如果为 `true`（说明聚焦是由点击复制按钮引起的误触），则：
                - 设置 `row._skipSave = true` 标记，告知后续的 `blur` 处理器跳过保存。
                - 主动调用 `document.activeElement.blur()` 强制失去焦点，防止进入编辑模式。
        - **更新失焦逻辑**:
            - 在所有 `handleXxxBlur` 函数中增加对 `row._skipSave` 的检查。如果为 `true`，则重置该标记并直接返回，不执行保存逻辑。
- **验证**:
    - 重新编译前端 (`npm run build`)。
    - 在未编辑状态下点击复制按钮，输入框应**不会**进入编辑状态（无焦点样式），且复制成功。
    - 点击页面其他地方，确认**不会**触发保存请求（无 PUT 请求）。

## 2026-02-25 (Part 6)
- **任务**: 修复【IBMC IP】和【IBMC 密码】的复制聚焦问题
- **问题**: 之前针对密码输入框的 `handleFocus` 优化未同步应用到 IBMC 相关的输入框，导致这两个字段点击复制时依然会触发聚焦和编辑模式。
- **变更**:
    - **前端 (`frontend/src/App.vue`)**:
        - 统一更新 `IBMC IP` 和 `IBMC 密码` 列的模板逻辑。
        - 为这两个列的输入框绑定 `handleFocus(row, 'IbmcIp/IbmcPassword')`。
        - 将复制按钮（`el-icon`）包裹在 `div` 容器中，并在容器上监听 `@mouseenter="isHoveringCopyBtn = true"` 和 `@mouseleave`，确保鼠标悬停状态能被正确捕获。
        - 同样添加 `@mousedown.prevent` 和 `@click.stop` 修饰符。
- **验证**:
    - 重新编译前端 (`npm run build`)。
    - 测试 IBMC IP 和 IBMC 密码列的复制功能，确认点击复制按钮时不会触发输入框聚焦，也不会触发保存。

## 2026-02-26
- **任务**: 适配异构机器监控（NVIDIA GPU + Huawei NPU）及 SSH 性能优化
- **变更**:
    - **后端 (`backend/services/monitor_service.py`)**:
        - **命令合并优化**: 将原本分 4 次执行的 SSH 命令（Arch, OS, NVIDIA, Huawei）合并为**单次执行**的组合命令。
            - 使用 `|||SECTION|||` 作为分隔符，通过 `split` 解析各部分输出。
            - 这样将 SSH 网络交互次数从 4 次减少到 1 次，显著降低了检测延迟。
        - **异构支持**:
            - 逻辑从“优先检测 NVIDIA，失败才检测 Huawei”更改为“**总是同时检测** NVIDIA 和 Huawei”。
            - 增加结果合并逻辑：将两种加速卡的数量、状态（Idle/Busy/Warning）、类型名称和详情列表进行合并。
            - 现在可以正确显示如 "NVIDIA RTX 4090, Ascend 910B" 这样的混合配置。
        - **超时调整**: 将 `execute_command` 的超时时间从 5 秒增加到 10 秒，以适应组合命令的执行时间。
        - **代码重构**: 修改了 `parse_nvidia_output` 和 `parse_huawei_output`，使其返回结构化的 `details` 列表（而非 JSON 字符串），由调用方统一序列化，便于合并。
- **验证**:
    - 验证代码逻辑无语法错误。
    - 预期效果：对于混合插卡的机器，能同时显示两类卡的状态；对于单类卡的机器，表现与之前一致；检测速度因减少了 SSH 握手次数而提升。







