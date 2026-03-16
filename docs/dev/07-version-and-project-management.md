# 项目版本管理与自动化工具日志

## 1. 需求分析
- 在 Web 页面标题旁显示版本号。
- 支持一键同步更新前端 (`package.json`) 和后端 (`main.py`) 的版本。

## 2. 技术方案
- **版本号存储**:
    - 前端: `package.json` 的 `version` 字段。
    - 后端: `backend/main.py` 中的 `__version__` 变量。
- **版本注入**:
    - 前端: 使用 Vite `define` 注入 `__APP_VERSION__` 全局常量。
- **同步更新**: 编写 Python 自动化脚本 `scripts/update_version.py`。

## 3. 实现细节
- **前端显示**:
    - 标题栏右侧添加版本号标签 `v1.0.0`。
    - 悬停显示 "Frontend: v1.0.0 | Backend: v1.0.0"。
    - 异步调用 `GET /version` 获取后端版本。
- **后端 API**:
    - 新增 `GET /version` 接口，返回 `{"version": __version__}`。

## 4. 踩坑记录
- **后端接口报错 (500)**: `backend/main.py` 遗漏了 `__version__` 定义，导致访问 `/version` 抛出 `NameError`。已补全定义并重启服务。

## 5. 验证
- 页面标题旁显示 `v1.0.0`。
- 鼠标悬停显示前后端版本详情。
- 运行 `python scripts/update_version.py 1.0.1` 可正确同步相关文件。

## 6. 日志时间
- 2026-03-11
