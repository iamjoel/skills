# Frontend Chore Review Focus

## 规模

- `Small`：单包、单工具、局部配置或文档更新，不影响生产构建和公共工具链。
- `Medium`：跨多个脚本/config，修改共享测试、codegen、CI cache 或开发/构建流程。
- `Large`：跨 workspace、升级 Node/包管理器/bundler、修改发布链路、浏览器目标或生产依赖。

生产依赖、lockfile 大幅变化、供应链安全、构建产物、环境变量、codegen 和发布配置至少提升一级审查深度。

## 依赖与 Lockfile

- manifest、workspace 声明和 lockfile 是否由同一包管理器一致生成？
- production、development、peer 和 optional 分类是否正确？
- direct 与 transitive 版本变化是否符合声明范围？
- Node、包管理器、框架、bundler 和浏览器目标是否兼容？
- 是否意外引入重复版本、原生模块、postinstall、bundle 体积或许可证风险？
- 安全更新是否真正覆盖受影响路径，而非只改变顶层版本？

## 构建与配置

- clean checkout 是否能使用仓库声明命令完成 install 之后的 build/test/codegen？
- 本地、CI、SSR 和 production 是否读取同一配置源和环境变量语义？
- 配置合并、路径解析、条件分支和默认值在所有目标环境下是否成立？
- tree-shaking、chunk、dynamic import、source map 和浏览器目标是否意外变化？
- cache key 是否包含所有会改变输出的输入？

## 测试与开发工具

- lint/test/typecheck 命令是否仍覆盖预期目录和文件类型？
- glob、ignore、project reference、transform 和环境选择是否漏掉真实代码？
- 测试是否仍能在错误实现下失败，而不是被 mock、snapshot 或缓存掩盖？
- watch、fake timer、DOM 清理、并行度和 CI 非交互模式是否稳定？
- 工具版本或规则升级是否产生未处理的行为变化？

## Codegen 与生成产物

- source of truth 是否唯一且明确？
- 生成命令是否确定、可重复并使用锁定版本？
- checked-in 产物是否与输入和生成器同步？
- 删除/重命名 schema 后是否残留旧类型、客户端或索引？
- 生成差异是否包含时间戳、绝对路径或环境相关噪音？

## CI、文档与发布

- CI job、依赖关系、权限、artifact 和 cache restore/save 顺序是否正确？
- 文档中的命令、路径、版本和默认值是否与仓库一致？
- 发布/回滚步骤是否仍可用，失败是否可诊断？
- secret 和环境变量是否只在所需范围暴露，日志是否可能泄露敏感值？

## 风险叠加项

只选择最相关的最多两个：

- 供应链：registry、integrity、postinstall、许可证和漏洞修复。
- 环境一致性：Node、包管理器、OS、shell、浏览器和 CI image。
- 构建产物：tree-shaking、chunk、source map、SSR 和部署 artifact。
- 缓存：key、restore、invalidation、跨分支污染和陈旧生成物。
- Codegen：schema、生成器版本、确定性和 source-of-truth。
- 测试可信度：glob、mock、snapshot、coverage 和错误实现下失败能力。
- 配置安全：secret、public env、日志、权限和发布 token。
- Monorepo：workspace 边界、affected 计算、project graph 和版本联动。

## Small Chore 卡片

```markdown
# <id> — <Chore 单元>

- Type: <Dependency | Build | Test tooling | Codegen | CI | Config | Docs>
- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Engineering contract: <目标与不变量>
- Reproducibility: <clean checkout/CI/production>
- Compatibility: <版本和环境>
- Frontend config/code: <关键链接>
- Verification: <已检查与已运行验证>
- Findings: <数量或 No actionable findings>
```
