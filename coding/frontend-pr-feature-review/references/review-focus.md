# Frontend Feature Review Focus

## 规模

- `Small`：一个局部入口和用户路径；不改变共享状态、公共契约、路由或持久化。
- `Medium`：跨多个组件/hooks，修改共享状态、查询缓存、API 使用或通用组件。
- `Large`：跨页面、前端包或多个用户流程；修改公共契约、路由、持久化、权限或渲染架构。

认证、敏感数据、不可逆操作、异步竞态、缓存一致性、SSR/水合、外部输入、生产依赖和性能关键路径至少提升一级审查深度。

## Feature Add

核心问题：新前端能力是否完整且正确接入用户流程？

- 目标用户能否发现并进入功能？
- 未启用、未配置、无权限或不支持环境下，旧 UI 是否保持正确？
- loading、empty、success、error、disabled、取消、重复和恢复状态是否完整？
- UI 状态、查询缓存、API 契约和持久化是否一致？
- 正常路径与至少一个关键边界是否有用户行为测试？
- 埋点、i18n、可访问性和响应式布局是否随入口一起落地？

## Feature Change

核心问题：新行为是否正确，同时没有意外破坏旧用户路径？

- Before、After 和行为不变量是否明确？
- 所有入口、页面、调用方和共享组件是否迁移完整？
- 旧 URL、旧缓存、旧持久化数据和旧响应是否兼容？
- feature flag 的开/关、降级、回滚和恢复是否正确？
- 新旧组件或请求路径并存时是否产生状态分叉？
- 测试是否同时覆盖旧场景、新场景和迁移边界？

## 通用状态矩阵

对每个适用维度记录 `covered | not applicable | not verified`：

- 用户：匿名、已登录、不同角色/租户、首次与返回用户。
- 数据：loading、empty、正常、部分、过期、错误、重试。
- 交互：disabled、重复点击、取消、切换、卸载、恢复。
- 环境：窄屏、长文本、RTL、SSR/CSR、目标浏览器、离线/慢网。
- 发布：flag off/on、旧数据、旧客户端契约、回滚。

不要机械要求所有组合；选择真实可达且影响行为的组合。

## 风险叠加项

只选择最相关的最多两个：

- React 状态与副作用：闭包、依赖数组、清理、remount 和 render 更新。
- 数据请求与缓存：query key、失效、分页、重试、乐观更新和陈旧结果。
- SSR 与浏览器：水合、server/client 边界、window API 和浏览器差异。
- 可访问性：键盘、焦点、ARIA、语义、缩放和屏幕阅读器。
- 国际化与布局：长文本、复数、RTL、溢出、窄屏和动态高度。
- 契约：可空字段、旧响应、错误码、序列化和运行时校验。
- 安全与隐私：XSS、Markdown、URL、文件、凭据、日志和敏感状态。
- 性能：重复渲染、大列表、流式更新、重型依赖和尾延迟。

## Small 功能卡片

```markdown
# <id> — <功能名称>

- Type: <Feature Add | Feature Change>
- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- User journey: <入口到结果>
- State coverage: <关键状态>
- Compatibility: <旧路径/数据/flag>
- Frontend code: <关键代码链接>
- Verification: <已检查与已运行验证>
- Findings: <数量或 No actionable findings>
```
