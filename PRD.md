
## Key Differences between Claude Code  and Codex
这个是我收集的部分Claude Code 和 Codex之间的部分差异:
| Feature | Claude Code | Codex CLI |
|---------|------------|-----------|
| Hooks | 8+ event types | Not yet supported |
| Context file | CLAUDE.md + AGENTS.md | AGENTS.md only |
| Skills | Skills loaded via plugin or project `.claude/skills/` | `.agents/skills/` directory |
| Commands | `/slash` commands | Instruction-based |
| Agents | Subagent Task tool | Single agent model |
| Security | Hook-based enforcement | Instruction + sandbox |
| MCP | Full support | Command-based only |

## 需求
1. 深度调研(从官网收集)不同AI平台(目前仅Claude Code和Codex)支持哪些Feature, 以及这些Feature在不同平台支持的差异性(包括是否支持, 路径位置灯), 深度了解每个Feature用于给AI加持哪方面的能力.
2. 目前这个项目需要我手动修改各个平台要下发的内容, 以便下发各个功能到不同的AI平台. 这对我来说太麻烦了. 我希望有一个SKILL, 在我提出需要添加什么功能时, 能够深刻了解不同平台的差异, 并帮我完成这些事情. 比如: "增加一个Hook: 在提交前使用sync-add-ios-loc 这个skill进行本地化校验", 他就可以在最终要下发的平台中添加对应的内容. 比如这条指令对应在用户端的效果:
    1. 如果用户选择Claude Code平台下发配置, 就会修改用户的hook.json中增加配置, 
    2. 如果用户选择在Codex, 只是修改对应的AGENTS.md增加一条指令(即Instruction, 可以看一下上面的不同之处)
 诸如此类, 能够将我的指令抽象为一条AI配置(可能是Hook ,可能是skill, 也可能就是一条Instruction, 也可以是MCP等), 然后下发时, 下发到用户的正确目录或者修改正确文件.
 你可能需要修改整个项目的架构以及创建这样的SKILL来实现.
3. 将现有ios文件夹下的 codex和 claude code的已有的配置, 重新按照2中的框架, 重新生成.
4. 先脑暴一个架构, 我确定了再执行.

## 架构决议追踪（2026-03-02）

- 官方能力矩阵：`docs/research/2026-03-02-claude-codex-feature-matrix.md`
- 架构设计文档：`docs/plans/2026-03-02-cross-platform-dispatch-design.md`
- 当前决议：采用“能力矩阵 + Intent Schema + 分发编译器”方案。
