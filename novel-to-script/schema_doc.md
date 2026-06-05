# 剧本 YAML Schema 设计文档

## 1. 为什么选择 YAML

| 需求 | YAML 表现 |
|------|-----------|
| **人类可读写** | 缩进语法直观，无需编辑工具即可修改，作者可以直接在文本编辑器中打磨剧本 |
| **支持注释** | `# 这是注释` — 作者和 AI 可以在文件中留下思考痕迹，不影响结构 |
| **层次化结构** | 天然支持幕→场→节拍的三级嵌套，比 JSON 的可读性高一个数量级 |
| **多行文本** | `|` 和 `>` 运算符让大段对白和动作描述保持整洁，无需转义换行符 |
| **生态兼容** | Python / JavaScript / 各类剧本工具原生支持，可无缝对接后续分镜、拍摄排期工具 |
| **版本管理友好** | 纯文本、按行 diff，适合 Git 协作；作者和编剧可以并行修改不同场次 |

YAML 的劣势是复杂嵌套时缩进容易出错，但剧本结构本身就是严格的树形结构，天然适配 YAML。

---

## 2. 顶层结构总览

```
Screenplay
├── meta                元信息：标题、来源、作者、类型、版本
├── characters[]        全局角色档案：所有角色在此定义一次
└── structure           
    └── acts[]          
        └── scenes[]    
            └── beats[] 动作 / 对白 / 转场（按时间顺序交错）
```

每个层级都附带 `notes` 字段，供 AI 标记不确定之处、作者做批注。

---

## 3. Meta（元信息）

```yaml
meta:
  title: "流浪地球"
  source: "小说《流浪地球》"
  author: "刘慈欣"
  adapted_by: "AI 辅助改编"
  genre:
    - 科幻
  format: feature
  version: "0.1.0"
  created_at: "2026-06-05T10:00:00"
  notes: "初稿，第三幕需要加强冲突"
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 剧本标题 |
| `source` | string | | 原著小说名称 |
| `author` | string | | 原作者 |
| `adapted_by` | string | | 改编者（可以是 "AI 辅助" 或具体人名） |
| `genre` | list[enum] | | 类型标签：动作、喜剧、科幻 等 |
| `format` | enum | | `feature`（电影）/ `short`（短片）/ `episode`（剧集）/ `stage`（舞台剧） |
| `version` | string | | 语义化版本号，支持迭代打磨 |
| `created_at` | datetime | | ISO8601 时间戳 |
| `notes` | string | | 自由批注 |

### 设计考量

**为什么 `genre` 是枚举而非自由文本？**
剧本类型影响后续分镜、节奏、预算估算等工具链。使用枚举确保下游工具可以稳定解析。枚举值覆盖了主流影视类型，如果某个小说类型未覆盖，可以通过 `notes` 补充。

**为什么 `format` 不默认留空？**
剧本格式（电影/剧集/舞台剧）决定了结构差异：剧集有 "集" 的概念，舞台剧对白密度不同。默认 `feature` 覆盖最常见场景，减少 AI 输出的缺失值。

---

## 4. Character（角色档案）

```yaml
characters:
  - id: "liu_pei_qiang"
    name: "刘培强"
    aliases: ["培强", "老刘"]
    age: "中年"
    gender: "男"
    role: protagonist
    archetype: "英雄"
    traits: ["坚韧", "沉默寡言", "父爱深沉"]
    description: "航天员，在空间站服役多年，与儿子刘启关系疏远"
    relationships:
      - character: "liu_qi"
        type: "父子"
        description: "因长期分离关系紧张，但彼此深爱"
      - character: "han_duo_duo"
        type: "养父女"
        description: "收养了孤女韩朵朵"
    notes: "在第三幕有一段关键独白，需要演员有很强的眼神戏"
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 全局唯一标识，建议用拼音或英文 |
| `name` | string | ✅ | 角色中文名 |
| `aliases` | list | | 别名、绰号，便于在原文中匹配 |
| `age` | string | | 年龄描述（**不建议用数字**，因为剧本选角需要弹性） |
| `gender` | string | | 性别 |
| `role` | enum | | protagonist / antagonist / supporting / minor / cameo |
| `archetype` | string | | 原型标签：英雄、导师、阴影、骗子 等 |
| `traits` | list | | 性格特征关键词 |
| `description` | string | | 角色概要描述 |
| `relationships` | list | | 角色关系列表 |
| `notes` | string | | 角色相关批注 |

### 设计考量

**为什么角色用 ID 引用而非姓名直接引用？**

姓名存在四个问题：
1. **别名** — "刘培强" 在原文中可能被称作 "培强"、"老刘"、"爸爸"
2. **重名** — 长篇作品中可能出现同姓角色
3. **改名** — 作者可能在改编过程中调整角色名
4. **国际化** — ID 作为程序标识，名称作为显示文本，职责分离

**为什么 `age` 不用数字而用描述？**

剧本选角阶段，"中年" 比 "42 岁" 更符合行业惯例。选角导演需要的是一个年龄区间，而非精确年龄。

**为什么要设计 `archetype` 字段？**

原型概念（英雄、导师、阴影、变形者等）是编剧理论的基础。有这个字段后，AI 可以在改编时根据原型自动调整角色弧线。例如 "英雄" 原型必须有 "拒绝召唤 → 接受使命" 的转折。

**为什么 `relationships` 嵌在 `Character` 里而非独立成表？**

关系是角色视角的：A 对 B 的关系描述可能与 B 对 A 的不同（"暗恋" vs "不知道"）。嵌入角色内部保留了这种不对称性。校验器会在加载时检查关系引用的目标角色是否存在。

---

## 5. Structure（剧本结构）

### 5.1 Act（幕）

```yaml
acts:
  - act_number: 1
    title: "建立"
    summary: "介绍末日背景，刘培强与刘启的父子矛盾，地球面临木星危机"
    notes: "节奏偏慢，可能需要压缩前置铺垫"
    scenes: [...]
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `act_number` | int | ✅ | 幕序号（从 1 开始） |
| `title` | string | | 幕标题（"建立" / "对抗" / "解决"） |
| `summary` | string | | 本幕内容摘要 |
| `scenes` | list | | 场次列表 |
| `notes` | string | | 批注 |

### 5.2 Scene（场次）

```yaml
scenes:
  - scene_number: 1
    heading:
      location_type: INT
      location: "空间站控制室"
      time: "夜晚"
    summary: "刘培强在空间站接到紧急通知"
    characters_in_scene:
      - "liu_pei_qiang"
      - "moss"
    beats:
      - type: action
        description: "警报声刺耳地响起，红色灯光在控制室中旋转"
      - type: dialogue
        character: "moss"
        line: "刘培强中校，木星引力异常，地球偏离轨道。"
        parenthetical: "(冷静的合成音)"
      - type: dialogue
        character: "liu_pei_qiang"
        line: "启动应急方案，快！"
      - type: transition
        transition: "CUT TO:"
    notes: "开场需要强烈的紧迫感"
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scene_number` | int | ✅ | 全场次编号（跨幕递增，用于制片排期） |
| `heading` | object | ✅ | 场次标题（slug line） |
| `summary` | string | | 本场内容摘要 |
| `characters_in_scene` | list | | 本场出现角色 ID 列表（可用于分场通告单） |
| `beats` | list | | 节拍序列，按时间顺序 |
| `notes` | string | | 批注 |

**Scene Heading 子字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `location_type` | enum | `INT`（内景）/ `EXT`（外景）/ `INT/EXT` |
| `location` | string | 地点名称 |
| `time` | string | 时间："白天" / "夜晚" / "黄昏" / "黎明" / "连续" 等 |

**为什么场景编号全局递增？**

好莱坞标准中，每个场景有唯一的编号，贯穿全片。制片部门据此安排拍摄日程、预算、通告单。如果不全局编号，同一场景编号在不同幕中重复，会造成排片混乱。

**为什么需要 `characters_in_scene`？**

这是冗余但有用的字段。它让制片人员无需扫描全部 beats 就能知道需要通知哪些演员到场。同时也供 AI 在分幕时做角色出场的全局平衡检查。

**为什么场景不包含 "页码" 或 "时长"？**

页码是渲染层的概念，取决于排版（字体、边距）。时长需要实际拍摄后才能确定。Schema 只存储结构和内容，不存储排版信息。

### 5.3 Beat（节拍）

节拍是场景内最小的结构单元，通过 `type` 字段（discriminated union）区分三种类型：

#### Action（动作 / 舞台指示）

```yaml
- type: action
  description: "巨大发动机的火焰照亮半个天空，大地在轰鸣中震颤"
  notes: ""
```

所有非对白的叙事内容都归为 Action。包括：环境描写、角色动作、情绪状态、特殊效果说明。

#### Dialogue（对白）

```yaml
- type: dialogue
  character: "liu_qi"
  line: "北京第三区交通委提醒您：道路千万条，安全第一条。"
  parenthetical: "(一本正经)"
  notes: "这句是笑点，注意节奏"
```

| 字段 | 说明 |
|------|------|
| `character` | 说话者角色 ID |
| `line` | 台词正文 |
| `parenthetical` | 括弧指示（声音语调、动作提示），放在角色名和台词之间 |

**为什么 `parenthetical` 不是独立 beat 类型？**

在标准剧本格式中，括弧指示（如 `(低语)`、`(停顿)`）紧贴在角色名下方、台词上方，是对白的一部分。单独成 beat 会割裂角色名和台词，破坏排版连续性。

#### Transition（转场）

```yaml
- type: transition
  transition: "CUT TO:"
```

标准转场标记：`CUT TO:`、`FADE IN:`、`FADE OUT:`、`DISSOLVE TO:`、`SMASH CUT:` 等。

### 设计考量：为什么 beats 是单一有序列表而非分类存储？

直觉上可能想把 Action 和 Dialogue 分开管理：

```yaml
# ❌ 不采用这种设计
actions:
  - ...
dialogues:
  - ...
```

**不采用的原因**：剧本是时间序列。对白和动作在时间线上交错进行——角色说完话 → 起身离开 → 另一个人说话。分开存储会丢失这种时序关系，导致：
1. 自动排版时需要复杂的时间重排逻辑
2. 人类阅读时无法直观感受节奏
3. 对 AI 而言，时序信息对于理解场景张力至关重要（"在他说出那句话之前，沉默了三秒"）

单一列表保留真实的叙事节奏。

---

## 6. 校验规则

校验分两层：

### 6.1 结构校验（Pydantic）

- 类型检查：字符串不能是数字，枚举值必须在预定义集合内
- 必填字段检查：`title`、角色 `id`、`name`、场次 `heading` 等不可缺失
- 嵌套深度和数据类型校验

### 6.2 语义校验（自定义规则）

| 规则 | 说明 |
|------|------|
| 角色引用的完整性 | 关系、对白、`characters_in_scene` 中引用的角色 ID 必须在角色列表中定义 |
| 场景编号唯一性与递增性 | 场景编号不能重复，且必须递增 |
| 结构非空检查 | 至少有一幕、至少有一个节拍 |
| 孤儿对白检查 | 有角色说了话但未在角色列表中定义（warning，非 error） |

语义校验区分 error（阻止发布）和 warning（提示注意）。

---

## 7. 扩展性设计

Schema 预留了以下扩展点：

| 扩展点 | 说明 |
|--------|------|
| `notes` | 每层都有，AI 可以在此写入置信度、备选方案 |
| `tags` | 未来可加入标签字段，支持关键字搜索和分类 |
| `genre` 枚举可扩充 | 新增类型不影响现有数据 |
| `Beat` 的 discriminated union | 未来可新增 `shot`（镜头指示）、`montage`（蒙太奇）等类型 |
| 角色 `traits` 自由列表 | 不对性格特征做枚举约束，保持灵活性 |

---

## 8. 与行业工具的对齐

| 行业标准 / 工具 | 与本 Schema 的对应关系 |
|------------------|------------------------|
| **Final Draft (.fdx)** | `heading` + `beats` 可直接渲染为标准 .fdx 格式 |
| **Fountain (.fountain)** | Action / Dialogue / Transition 的 beat 类型一一对应 |
| ** Celtx** | `meta` + `characters` + `structure` 涵盖 Celtx 的核心数据模型 |
| **Movie Magic Scheduling** | `scene_number` + `characters_in_scene` + `location` 可直接用于排期 |

这意味着本 Schema 不仅是内部存储格式，还可以作为多种行业标准格式的**中间表示**。

---

## 9. 完整示例

```yaml
meta:
  title: "最后的守望者"
  source: "小说《守望》"
  author: "张三"
  adapted_by: "AI 辅助改编"
  genre:
    - 科幻
    - 剧情
  format: feature
  version: "0.1.0"
  created_at: "2026-06-05T10:00:00"
  notes: "试改编前三章，后续章节待处理"

characters:
  - id: "wang_li"
    name: "王立"
    age: "中年"
    gender: "男"
    role: protagonist
    archetype: "反英雄"
    traits: ["颓废", "机智", "内心挣扎"]
    description: "前科学家，因实验事故被开除，独自生活在废弃研究所"
    relationships:
      - character: "ai_x"
        type: "创造者与被造物"
      - character: "lin_yue"
        type: "旧情人"
    notes: ""

  - id: "ai_x"
    name: "X"
    aliases: ["X-7", "X系统"]
    age: "无"
    gender: "无"
    role: antagonist
    archetype: "阴影"
    traits: ["冷漠", "逻辑至上"]
    description: "王立创造的AI，失控后控制了整个研究所"

  - id: "lin_yue"
    name: "林月"
    age: "中年"
    gender: "女"
    role: supporting
    archetype: "盟友"
    traits: ["坚韧", "善良"]
    description: "王立的前女友，现任安全局探员"

structure:
  acts:
    - act_number: 1
      title: "建立"
      summary: "王立在废弃研究所的日常被打破，AI X 的威胁浮现"
      scenes:
        - scene_number: 1
          heading:
            location_type: INT
            location: "废弃研究所 - 王立的房间"
            time: "夜晚"
          summary: "王立被异常信号惊醒"
          characters_in_scene:
            - "wang_li"
          beats:
            - type: action
              description: "黑暗中，老旧显示屏突然亮起，一串绿色代码自动滚动"
            - type: dialogue
              character: "wang_li"
              line: "你又来了。"
              parenthetical: "(疲倦地)"
            - type: action
              description: "他伸手去够桌上的酒瓶，却在半空中停住"
          notes: ""

        - scene_number: 2
          heading:
            location_type: EXT
            location: "研究所外围 - 公路"
            time: "黎明"
          summary: "林月驱车抵达研究所"
          characters_in_scene:
            - "lin_yue"
          beats:
            - type: action
              description: "一辆黑色越野车停在锈迹斑斑的铁门前"
            - type: action
              description: "林月下车，仰望这座被遗忘的建筑，神情复杂"
            - type: dialogue
              character: "lin_yue"
              line: "五年了。"
              parenthetical: "(自言自语)"
          notes: ""
      notes: ""
  notes: ""
notes: ""
```
