# 平台与权限

本文规定平台接入时需要核实的条件。实际接入时重新核对当前产品版本、接口文档、账号权限和组织策略。

## GitHub

推荐链路为子仓库 push 事件触发通知，向主仓库发送 `repository_dispatch`，主仓库完成对账并创建或更新 PR。主仓库保留手动入口，可增加定时对账。

### 分支与触发

- 主仓库默认分支中必须存在接收 `repository_dispatch` 的工作流；定时事件也依赖默认分支上的工作流。实际需要更新的主仓库目标分支应单独明确。
- 通知可以覆盖全部子仓库分支，由主仓库 `.gitmodules` 判定版本；收窄 push 分支过滤时，核对其覆盖所有依赖方声明的分支。
- `repository_dispatch` 的通知类型应固定并由主仓库明确接收。主仓库不得直接信任通知给出的 SHA 或仓库地址。
- 定时任务明确使用的 UTC 时间、对应本地时区与周期。GitHub 的计划执行可能延迟或受仓库规则停用，需保留手动恢复入口。
- 主仓库跟踪配置生效后重新对账，并检查子仓库通知配置是否需要调整。

### 身份与权限

| 用途 | GitHub 接入条件 |
| --- | --- |
| 跨仓库通知 | 向目标主仓库发送 repository_dispatch；fine-grained token 或 GitHub App installation token 需目标主仓库 Contents: write |
| 读取私有子模块 | 对每个子仓库授予 Contents: read 或相应 Git 读取权限；主仓库的默认令牌通常不能跨仓库读取 |
| 推送机器人分支 | 主仓库 Contents: write，且机器人分支保护规则允许该身份执行所需更新 |
| 创建或更新 PR | 主仓库 Pull requests: write；查询权限也应可用 |
| 使用 GITHUB_TOKEN 创建 PR | 除工作流权限外，核对仓库或组织是否允许 Actions 创建 PR |
| 配置工作流与 Secret | 接入者拥有相应配置权限；修改工作流文件可能要求额外授权，不应自动扩大日常令牌范围 |
| 人工合并 | 合并者满足目标分支保护、评审和状态检查规则 |

子仓库自带的 `GITHUB_TOKEN` 受源仓库授权范围约束，不能将其当作已获得主仓库的跨仓库触发权限。使用 GitHub App 时，区分应用私钥与实际用于接口请求的短期 installation token，并核对应用安装到了哪些仓库。

日常运行可根据组织策略使用 GITHUB_TOKEN、专用 fine-grained PAT 或 GitHub App。选择身份时，同时验证该身份推送和开 PR 后，项目要求的后续工作流是否会触发、是否需要批准。不能看到 PR 创建成功就认定构建检查已运行。

### PR 对应关系

查询开放 PR 时匹配完整 head（所属 owner 与机器人分支）和 base（主仓库目标分支），处理分页。推送到同一 head 更新已有 PR 的提交内容，PR 标题和正文另行更新。创建请求失败或超时后先重新查询，防止产生重复项。

## Gitee

先明确使用社区版 Gitee Go、企业流水线还是私有化实例。它们的配置和可用接口应分别核实。

### 分支与触发

按实际环境选择可用链路：

- 能由子仓库 push 触发的流水线或执行器，取得主仓库目标分支后执行对账；不能沿用子仓库工作目录作为主仓库基线。
- 子仓库 Webhook 通知经过校验的接收端，再启动已确认可用的主仓库侧执行流程。
- 缺少事件执行条件时，使用已有调度器定时对账，并明确周期与延迟。

Gitee 企业流水线支持代码源 push 触发并提供分支过滤；社区 Gitee Go 也有自身的触发配置。按实际产品确认是否能从所选子仓库事件启动所需流程、能否访问主仓库，以及是否提供适用的手动和定时入口。

Webhook 的配置存在不代表主仓库侧已有可运行的接收入口。接入时确认事件类型、目标地址、密码或签名校验方式、请求结果、重试行为和执行记录。流水线执行 API 尚未核实时保留这一缺口，选择已确认的执行器或定时方案，不根据 PR API 推断存在流水线触发能力。

### 身份与权限

| 用途 | Gitee 接入条件 |
| --- | --- |
| 管理子仓库事件通知 | 接入者具有对应 Webhook 或流水线配置权限 |
| 接收通知并启动流程 | 按实际 Gitee 产品或外部执行器核实触发凭证及允许事件来源 |
| 读取主仓库及子仓库 | 对各仓库具有 Git 读取权限；逐个核对私有仓库访问 |
| 推送机器人分支 | 对主仓库具有分支写入权限，且满足保护规则 |
| 查询、创建和更新 PR | 主仓库对应的 PR API 权限及机器人身份访问权 |
| 配置令牌和变量 | 接入者具有实际流水线或执行器的 Secret 管理权限 |
| 人工合并 | 合并者满足主仓库目标分支的保护与评审要求 |

令牌 scope 的名称、授权方式和 API 域名按公共平台或实际私有化实例核实，不沿用 GitHub 的权限名称。分别检查 Git 读写认证与 PR API 认证；其中一项成功不能证明另一项已授权。

### PR 对应关系

使用实例实际提供的 PR 查询、创建、编辑接口，按开放状态和准确源/目标分支复用 PR，处理分页。核对 API 返回的 PR 与远端机器人分支内容一致。公共 Gitee API 文档若需动态加载，应获取实际参数定义后再接入，不把文档入口存在当作接口参数已验证。

## 跨平台仓库

子模块可以与主仓库位于不同平台。分别确认源平台通知、执行器启动、子模块读取、主仓库写入和主平台 PR 创建权限；整个流程最终使用主仓库所在平台的 PR 规则。网络连通性和凭证不能因其中一段成功而省略核对。

### 免费推送触发：Gitee → Hookdeck → Cloudflare Workers → GitHub Actions

这条链路无需启用 Gitee Go。Gitee 仓库的 Push Webhook 先发送到 Hookdeck 的公网接收地址，再转发到 Cloudflare Worker；Worker 验证通知后调用 GitHub 的 `repository_dispatch`，公开执行仓库中的 GitHub Actions 对账并在主仓库所在平台创建或更新 PR。Gitee 原始事件与 GitHub 的认证和请求格式不同，由 Worker 完成转换。

如果 Gitee 到 `workers.dev` 的投递出现连接超时，不能把 Worker 健康检查成功误认为 Gitee 链路可用。应将故障边界拆成三段分别验证：Gitee → Hookdeck、Hookdeck → Worker、Worker → GitHub。Hookdeck 的免费额度、事件留存、重试和数据处理范围必须在启用前核对；若该服务不可用，再评估其他公网入口。

公网入口只承担接收和转发，不决定仓库、分支或目标 PR。Gitee Webhook 的密码用于验证来源；入口到 Worker 之间使用另一枚独立密钥。若入口会保存请求正文，应在接入清单中明确其留存期限和可见范围；不能把 GitHub 或 Gitee 访问令牌放进 Webhook URL、请求正文或日志。

开始部署前，一次性主动列出以下清单，填写本次已核实值并标记缺口，供维护者直接配置：

| 清单 | 应列出的内容 |
| --- | --- |
| 仓库与分支 | Gitee 主仓库及 PR 目标分支、子仓库及每个挂载路径的跟踪分支、机器人分支、GitHub 公开执行仓库及默认分支、Cloudflare 目标账号和 Worker 名称。 |
| Gitee 接入权限 | 各子仓库的 Webhook 配置权限；使用 API 管理时列出 `hook` 权限与具体仓库范围，使用页面配置时列出维护者需要完成的动作。 |
| Gitee 运行权限 | 主仓库读取与机器人分支写入、各子仓库读取、主仓库 PR 查询/创建/更新。说明所选令牌界面的实际 scope、所选仓库清单、有效期、轮换责任人；不默认授权全部仓库或无关 Issue 权限。 |
| GitHub 权限 | 接入者配置工作流和 Actions Secrets 的权限；Worker 触发令牌仅授权所选执行仓库的 `Contents: write`；工作流 `GITHUB_TOKEN` 按实际操作最小授权。 |
| Cloudflare 权限 | 目标账号的 Worker 部署与 Secret 管理权限；列出使用登录授权还是专用 API Token，说明授权范围和保管位置。 |
| Secret 映射 | 分别列出 Gitee 访问令牌、Webhook 验证密钥、GitHub dispatch 凭证、私有仓库配置及其他运行密钥的名称、用途、存放平台、输入方式和轮换位置；不同用途使用独立凭证。 |
| 触发与允许范围 | Webhook 地址、Push 事件及分支过滤、密码或签名模式、Worker 来源允许列表、固定 GitHub 目标和事件类型、Actions 手动入口、并发及失败恢复方式。 |
| 免费条件及信息流 | 当前核实的 Cloudflare 免费额度及超限行为、GitHub 公开仓库与标准运行器条件、各平台可接触的数据、公开日志规则及可能收费的功能。 |
| Hookdeck | 项目、接收 URL、转发目标、入口到 Worker 的独立验证密钥、免费额度、重试和日志留存策略、停用方式。 |
| 验收与维护 | 首次真实推送、重复/非目标/未授权通知、无更新、权限过期、PR 复用、人工合并、停用和恢复的检查动作及完成标准。 |

接入权限与运行权限分别说明。配置 Webhook 的权限通常只在接入或变更时需要；进入日常运行前，确定是否仍需保留。凭证需要维护者操作时，提前告知配置入口、具体授权范围和安全输入位置，直到实际输入环节再交接，不要求在聊天中发送凭证值。

| 环节 | 接入条件与最小权限 |
| --- | --- |
| Gitee 子仓库 | 维护者有权配置 Push Webhook。为入口配置独立的验证凭证，按 Gitee 文档验证通知；只允许已配置的子仓库及分支组合。 |
| Hookdeck | 维护者有权创建接收端和转发连接。Hookdeck 只保存独立转发密钥，不保存 Gitee 或 GitHub 访问令牌；需要核对免费额度、重试和日志留存策略。 |
| Cloudflare Worker | 部署者有权管理目标 Cloudflare 账号的 Worker。把入口验证凭证与 GitHub 触发凭证放在 Worker Secrets。触发凭证仅授权指定执行仓库；`repository_dispatch` 要求该仓库的 GitHub App 安装令牌或细粒度令牌具备 `Contents: write`。 |
| GitHub Actions | 在执行仓库的默认分支配置固定的 `repository_dispatch` 事件类型。将私有目标配置与跨平台凭证放在 Actions Secrets；执行身份只需读主仓库及所需子仓库、写主仓库机器人分支、创建或更新 PR。工作流本身的 `GITHUB_TOKEN` 按需授权，不用于 Gitee 认证。 |

1. **先确定跟踪关系。** 从主仓库目标分支读取 `.gitmodules`，明确挂载路径、子仓库地址、跟踪分支及 PR 目标分支。Worker 的允许列表与这些配置保持一致；变更后核对订阅和允许列表。Runner 从可信配置读取实际目标，不能用事件决定访问哪座仓库或推送到哪个分支。
2. **先验证网络分段。** 分别记录 Gitee Webhook 投递结果、入口到 Worker 的转发结果和 Worker 到 GitHub 的 dispatch 结果。出现连接超时、TLS 错误或 4xx/5xx 时，只重试对应分段；不能用下游成功推断上游已成功。
3. **只转发触发信号。** Worker 校验 Gitee 通知，过滤非目标仓库或分支，向固定 GitHub 仓库发送固定事件类型。无需把 Gitee 原始请求、仓库名、分支、SHA、提交信息或人员数据转发到 GitHub。Actions 再从配置的跟踪分支读取实际版本，对账后只更新 gitlink，提交到机器人分支，由维护者合并 PR。
4. **核对免费条件。** Cloudflare Workers Free 当前为每日 100,000 次请求、每次 10 毫秒 CPU 时间；部署前复核额度和超限行为，并控制重复投递。公开 GitHub 仓库使用标准 GitHub 托管运行器时，Actions 运行时间免费；大型运行器另行计费。公网入口的免费额度、重试、日志留存和超限行为必须单独核对。无需为此上传产物。公开执行仓库采用团队明确授权的账号，凭证不得出现在 URL、仓库文件或可查看的运行输出中。
5. **检查数据暴露。** Hookdeck 和 Cloudflare 都可能接收原始 Gitee 事件，公开 GitHub 执行记录可能暴露触发时间。入口和 Worker 日志不记录请求头或正文；公开工作流不记录私有仓库 URL、分支、SHA、PR 链接或凭证，也不上传工作目录。GitHub 的密钥遮蔽不能替代日志检查。限制谁能修改执行仓库的默认分支和工作流；持有私有凭证的任务只运行可信代码，不执行外部 PR 或子模块提交带入的脚本。详细结果保留在主仓库的私有 PR 或受控渠道；若项目不允许 Hookdeck 或 Cloudflare 接触相应数据，改用受控接收端或执行器。
6. **端到端验收。** 用已授权的测试推送确认指定分支触发并创建或更新一个 PR，未授权通知和其他分支不启动流程；重复通知不会重复开 PR，公开日志和产物不包含私有信息。保留手动对账和定时对账入口，以便 Webhook 投递失败、服务限流或凭证过期后补做。

## 官方核验入口

- Git `.gitmodules`：https://git-scm.com/docs/gitmodules
- Git 子模块更新：https://git-scm.com/docs/git-submodule
- GitHub 触发事件：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- GitHub 跨工作流触发与令牌规则：https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
- GitHub repository_dispatch：https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event
- GitHub Actions 计费：https://docs.github.com/en/billing/concepts/product-billing/github-actions
- GitHub Actions 安全用法：https://docs.github.com/en/actions/reference/security/secure-use
- GitHub PR API：https://docs.github.com/en/rest/pulls/pulls
- Gitee Go 触发配置：https://help.gitee.com/gitee-go/pipeline/trigger/
- Gitee 企业流水线代码提交触发：https://help.gitee.com/enterprise/pipeline/source/trigger/
- Gitee 帮助中心（Webhook 管理）：https://help.gitee.com
- Gitee Webhook 验证：https://help.gitee.com/webhook/how-to-verify-webhook-keys
- Gitee 公共 OpenAPI：https://gitee.com/api/v5/swagger
- Hookdeck 文档：https://hookdeck.com/docs
- Cloudflare Workers 额度：https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare Workers Secrets：https://developers.cloudflare.com/workers/configuration/secrets/
