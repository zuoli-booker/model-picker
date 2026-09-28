# model-picker

**回答几个问题，生成一份可解释的大模型使用策略 + 一份可直接使用的 LiteLLM 配置。**

LiteLLM 解决"怎么接"，OpenRouter 解决"替你接"，model-picker 解决**"接哪个 + 帮我配好"**。

为「轻开发者」设计：用过 WorkBuddy / Trae / 豆包等 AI 应用、手头有 2-5 家模型 API Key、
不知道该怎么搭配用的非程序员上班族。**零第三方依赖、完全离线、BYOK 模式不接触你的任何 API Key。**

---

## 30 秒看懂它能干什么

```
$ python -m model_picker

第 1 步 / 共 4 步：你手头有哪些模型的 API？
    1. DeepSeek V4（深度求索）  ¥3.5/百万tok混价  128k 上下文
    ...
你的选择：1,7

第 2 步 / 共 4 步：你主要用 AI 干什么？（多选）
你的选择：1,6

第 3 步 / 共 4 步：你更看重什么？（单选）  A 省钱 / B 质量 / C 快 / D 均衡
你的选择：A

第 4 步 / 共 4 步：确认生成？[回车]=生成，输入 1/2/3 回退修改，q=退出
```

回车之后，你得到三样东西：

1. **终端策略报告**：每个任务的首选 + 备选 + 每条推荐的**理由**（无黑盒）
2. **model-picker-config.yaml**：可直接喂给 LiteLLM 的配置（主备自动降级）
3. **my-strategy.md**：人话版策略说明，含月成本估算表，可直接分享

> 演示 GIF / 录屏待补（验收清单项）。

## 安装三步

```bash
# 1. 克隆仓库
git clone https://github.com/<你的账号>/model-picker.git
cd model-picker

# 2. 确认 Python ≥ 3.10（零第三方依赖，无需 pip install）
python3 --version

# 3. 跑
python -m model_picker
```

macOS / Windows 均可（路径处理用 pathlib，无平台依赖）。

## 用法

```bash
# 交互问答（主流程，4 步，每步可回退）
python -m model_picker

# 预设场景快速生成（跳过任务/偏好问答，为演示和内容创作服务）
python -m model_picker --preset weekly_report
python -m model_picker --list-presets     # 查看全部预设
```

四步问答：**手头有哪些模型**（20 个内置清单多选，也支持手动输入清单外模型）→
**主要用 AI 干什么**（6 类任务多选）→ **更看重什么**（省钱/质量/快/均衡）→ **确认生成**。

## 接上 LiteLLM（三步）

```bash
# 1. 填入你已有的各家 Key（环境变量名见 yaml 内注释）
export DASHSCOPE_API_KEY=sk-xxx
export DEEPSEEK_API_KEY=sk-xxx

# 2. 启动 LiteLLM
litellm --config model-picker-config.yaml

# 3. 你的应用把 model 换成任务别名，即按本策略路由
#    model: "writing"   # 写文案/周报 → 自动路由到首选，失败自动降级到备选
```

## 推荐是怎么算出来的（可解释，无黑盒）

规则式引擎，全部逻辑公开在 [model_picker/engine.py](model_picker/engine.py)：

1. **任务类型 → 7 维度权重表**（写作/代码/长文本/推理/中文/速度/价格）
2. **你的偏好调整权重**（省钱→价格、质量→五项能力、快→速度，各 ×1.5 后归一化）
3. **各维度打分**：能力分来自公开测评整理；速度分 = 每 10 tokens/秒 1 分（封顶 10）；
   价格分以你清单里的最低混合价为 10 分基准
4. **每个任务输出首选（综合分最高）+ 备选（够用线以上最便宜）**，并各附 2-3 句理由

## 模型数据

- `data/models.json`：20 个模型（国内 13 + 国际 7），分数 0-10 分制，价格折合人民币
- ⚠ **当前为占位数据**（开发联调用），正式发布前会完成数据整理并更新 `updated_at` 与来源标注
- 数据整理规范见文件头部 `meta` 段

## 设计原则

- **BYOK**：不接触、不中转、不存储任何 API Key；配置里 Key 一律走环境变量
- **可解释**：每条推荐附理由，规则表公开可查，不做学习式路由
- **零依赖**：只用 Python 标准库，git clone 即可跑；完全离线（MVP 不调任何外部 API）
- **最小维护**：MVP 明确不做 Web 界面、API 拉取、速度实测、用户系统（见路线图）

## 路线图（简述）

| 阶段 | 内容 |
|---|---|
| 阶段 0（当前） | CLI MVP 开源验证（GitHub star / issue 反馈） |
| 阶段 2 | 数据管道（榜单 API 自动更新）、Web 版配置器 |

## 项目结构

```
model_picker/          # 包源码（零第三方依赖）
  __main__.py          # 入口：参数解析 + 流程编排
  quiz.py              # F1 四步交互问答（可回退）
  engine.py            # F2 推荐引擎（权重表 + 打分 + 首选/备选 + 理由）
  data.py              # F3 数据层（加载 models.json）
  report.py            # F4-1 终端报告
  cost.py              # P1 月成本估算
  yaml_gen.py          # F4-2 LiteLLM 配置生成
  markdown_report.py   # P1 Markdown 策略报告
  presets.py           # P1 预设场景
data/models.json       # 20 个模型数据（MVP 手动维护）
```

## 许可证

[MIT](LICENSE) © 2026 model-picker contributors

> 本项目为个人副业开源项目：内容运营（小红书/B站）+ 开源策略生成器 + 可下载的 BYOK 路由应用。
> 协作文档见 `AGENTS.md` 与 `docs/`。
