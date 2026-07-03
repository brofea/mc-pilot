# Docker 数据构建假阳性验收复盘

## 1. Root Cause Category

- **D — Test Coverage Gap**：此前只验证镜像包含脚本、Compose 健康和单元测试，没有执行真实官方 26.2 数据、Qdrant 写入及 DeepSeek 响应解析。
- **E — Implicit Assumption**：错误假设 recipe ingredient 总是字典、Qdrant 接受任意字符串 ID、DeepSeek usage 全部是整数、`scroll` 无记录才表示结束、执行工具返回就等于容器进程结束。
- **B — Cross-Layer Contract**：Mojang JSON、Python logging、DeepSeek JSON 和 Qdrant HTTP 的边界约束未被类型或集成测试表达。

## 2. Why Fixes Failed

1. README 重写验收只检查了脚本存在和健康接口，属于表面验证。
2. 修复 logging 冲突后首次 Wiki 重跑的终端通道超时，曾被误看作命令结束；实际进程继续运行并在 Qdrant ID 处失败。
3. 修复 point ID 后，监控全量构建时才发现末页 `next_offset=None` 会令切换循环从头开始。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
|---|---|---|---|
| P0 | Regression tests | 为 26.2 候选 ingredient、usage 嵌套字段、日志保留字段、Qdrant UUID 和末页 scroll 添加测试 | DONE |
| P0 | Runtime acceptance | 真实运行两条构建命令并请求 recipe、Wiki、LLM 三条 HTTP 链路 | IN PROGRESS |
| P1 | Specs | 在 logging、database、foundation contracts 固化边界和验收要求 | DONE |
| P1 | Documentation | README 写明 Wiki 长耗时、成功标志及产物检查方式 | DONE |

## 4. Systematic Expansion

- **Similar Issues**：所有第三方 JSON 都应在 client/adapter 边界归一化，不能把供应商扩展字段直接塞入窄类型模型。
- **Design Improvement**：业务 ID 与存储 ID 分离；原始 ID 放 payload，存储 ID 使用确定性 UUID。
- **Process Improvement**：交付文档里的命令必须至少在干净或重建后的交付镜像中完整执行一次。

## 5. Knowledge Capture

- [x] 更新 backend logging guidelines。
- [x] 更新 backend database guidelines。
- [x] 更新 foundation runtime contracts。
- [x] 添加自动化回归测试。
- [ ] 完成并记录最终全量 Docker Wiki 构建退出码与 live 查询。
