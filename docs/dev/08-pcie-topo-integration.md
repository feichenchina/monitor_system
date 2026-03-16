# PCIe 拓扑可视化集成日志

## 1. 需求分析
- 集成 `PCIETopoPainter` 工具，实现机器 PCIe 拓扑图的自动化生成与可视化。
- 支持在前端详情页沉浸式展示拓扑图。
- 实现启动自动刷新与数据持久化。

## 2. 技术方案
- **远程采集**: `topo_service.py` 负责打包工具、远程执行并解析结果。
- **数据持久化**: `Machine` 模型新增 `pci_topo_json` (Text) 字段，存储 JSON 数据。
- **前端渲染**: 基于 `Cytoscape.js` + `cytoscape-dagre` 渲染拓扑图。

## 3. 实现细节
- **后端拓扑服务**:
    - 实现 `update_all_machines_topo` 全量刷新。
    - 使用 `python3 -m zipfile` 远程解压。
    - 增加 `--all` 参数，防止 `lspci` 输出兼容性导致节点过度过滤。
- **前端组件**:
    - `PCIeTopo.vue`: 实现节点样式优化（水平文字、白色描边）。
    - 独立弹窗展示: `App.vue` 新增 `topoDialogVisible`。
    - **沉浸式 UI**: 弹窗设为无标题栏、无背景、灰色灰显背景 (`#e5e7eb`)，移除默认边框和阴影。

## 4. 踩坑记录
- **数据库迁移**: SQLite 不支持 `ALTER TABLE ... ADD COLUMN` 添加非空约束，需谨慎处理默认值。
- **远程执行**: 初始使用 `unzip`，但部分环境缺失。已改为 `python3 -m zipfile`。
- **lspci 兼容性**: 在部分机器上 `prune_tree` 逻辑误杀所有节点。通过强制开启 `--all` 参数解决。
- **Cytoscape**: `width: label` 已弃用。连线文字默认跟随路径旋转，阅读困难。通过 `text-rotation: none` 强制水平。
- **构建错误**: `App.vue` 添加 CSS 时引入语法错误（未正确闭合）。已修复。

## 5. 验证
- 数据库字段成功添加。
- 远程脚本成功执行。
- 前端成功渲染拓扑图。

## 6. 日志时间
- 2026-03-11, 2026-03-12
