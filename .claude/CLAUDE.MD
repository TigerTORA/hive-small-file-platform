1,YOU MUST prioritize simple, readable code with minimal abstraction：强调简单、可读、最小化抽象。这是为了对抗 Claude 的过度设计倾向。
2,avoid premature optimization：避免过早优化。明确告诉它，性能和完美的架构暂时不是第一位的。
3,DO NOT use preserve backward compatibility：明确禁止保留向后兼容。这是一条非常关键的规则，强制 Claude 在修改时要大胆地删除和重构旧代码。
4,每次宣告任务结束时都比如给出让我验证的链接
5,遇到技术困难时，MUST尝试至少2个替代方案再放弃。同时必须验证创建的工具/测试实际可用。
6,开发任何功能后，MUST进行端到端验证，包括用户界面的实际显示效果和数据完整性，不允许仅验证API层面就宣告完成。必须提供用户可见的验证证据。
7,引用数据库字段前，MUST确认字段存在，避免运行时AttributeError。API代码与数据库模型必须保持一致。
8,UI功能异常时MUST先检查后端API和数据库架构，再分析前端代码
9,开发完成时MUST提供端到端验证链接，确保用户界面实际可用