# SSH 认证失败退避与防锁定修复日志

## 1. 问题背景
- 现网存在密码错误机器被持续刷新检测的情况。
- 监控任务周期执行时，会对同一台机器重复发起 SSH 登录。
- 在目标设备启用失败次数保护策略时，频繁认证失败会触发 SSH 端口或账户锁定。

## 2. 根因分析
- 原逻辑在每轮任务中无条件尝试连接，认证失败仅记录日志并标记离线。
- 认证失败与网络失败未做差异化处理，缺少限流/熔断机制。
- 未引入失败记忆，导致同一凭据错误会在短周期内无限重试。

## 3. 修补方案
- 在 `backend/services/monitor_service.py` 中引入认证失败退避状态：
  - 新增指数退避参数：
    - `AUTH_FAILURE_BASE_COOLDOWN_SECONDS = 300`
    - `AUTH_FAILURE_MAX_COOLDOWN_SECONDS = 3600`
  - 新增线程安全内存状态：`_auth_backoff_state` + `_auth_backoff_lock`。
- 增加连接前判定：
  - 若机器处于认证失败冷却窗口，直接跳过本轮 SSH 登录。
  - 状态更新为 `Offline`，并在 `error_message` 中返回剩余等待秒数和失败次数。
- 增加认证失败识别：
  - 显式捕获 `paramiko.AuthenticationException`。
  - 对部分设备返回的字符串异常进行兜底识别（`authentication failed` / `permission denied`）。
- 增加失败累进与上限控制：
  - 冷却时长按 2 的指数递增，最高封顶 3600 秒。
- 增加自动恢复机制：
  - 连接成功后立即清理该机器失败状态。
  - 机器凭据发生变更后，自动清除历史冷却（通过凭据指纹变化判断）。

## 4. 关键实现点
- 连接结果结构化：`_create_ssh_client_with_error(...) -> (client, error_type, error_message)`。
- 失败状态管理函数：
  - `_get_auth_backoff_info(machine)`
  - `_record_auth_failure(machine)`
  - `_clear_auth_failure(machine)`
- 凭据指纹：
  - `ip + port + username + password` 组成指纹，避免错误密码修正后仍被旧冷却阻塞。

## 5. 风险与边界
- 当前退避状态为内存级：服务重启后状态会重置。
- 该策略针对认证失败场景生效；网络抖动、超时等非认证问题仍按原逻辑执行。
- 若后续需要跨重启持续生效，可扩展为数据库持久化退避状态。

## 6. 验证结果
- 后端静态错误检查：通过（无 errors）。
- 后端语法编译检查：通过（`python -m compileall backend`）。
- 预期行为：
  - 密码错误时，不再按调度周期持续打 SSH。
  - 错误信息可见下一次重试窗口，便于运维定位与修复。
  - 修正密码后可在下一次检测立即恢复正常连接。

## 7. 后续优化建议
- 将退避参数暴露到 `settings` 配置，支持前端可视化调整。
- 增加接口字段用于展示机器当前退避剩余时间。
- 补充自动化测试覆盖认证失败、凭据修改、成功清零三类关键路径。

## 8. 日志时间
- 2026-03-31
