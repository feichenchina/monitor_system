# 交互体验修复日志：剪贴板、焦点与密码显隐

## 1. 需求分析
- 修复非安全上下文（HTTP IP 访问）下复制失败的问题。
- 解决点击复制按钮、切换密码可见性时触发输入框 `blur` 保存逻辑的冲突。
- 修复点击复制按钮导致意外聚焦和进入编辑模式的问题。

## 2. 技术方案
- **剪贴板降级**: `navigator.clipboard` 不可用时降级使用 `document.execCommand('copy')`。
- **状态标记与拦截**:
    - 引入 `isCopying` 和 `isHoveringCopyBtn` 标记。
    - 引入 `isHoveringPasswordToggle` 标记。
    - 在 `blur` 保存逻辑中拦截。

## 3. 实现细节
- **复制拦截**:
    - 按钮上添加 `@mousedown.prevent` 阻止默认行为。
    - 按钮上添加 `@mouseenter` / `@mouseleave` 更新悬停状态。
    - `handleFocus` 检查 `isHoveringCopyBtn`，若为真则标记 `_skipSave = true` 并强制失去焦点。
- **密码切换拦截**:
    - 在 `handlePasswordBlur` 和 `handleIbmcPasswordBlur` 中添加对 `isHoveringPasswordToggle` 的检查。
- **Fallback 焦点处理**:
    - 在 `copyToClipboard` 中记录 `activeElement`，并在 `finally` 块中恢复焦点，配合 `setTimeout` 延迟重置 `isCopying` 状态。

## 4. 验证
- 重新编译前端 (`npm run build`)。
- 在 IP 访问环境下测试复制成功。
- 在编辑状态下点击复制按钮，Network 面板无 PUT 请求。
- 点击密码切换显隐按钮，不触发 PUT 请求且控制台无报错。

## 5. 日志时间
- 2026-02-25, 2026-03-11
