# 智能代码分析与模糊测试驱动生成系统

基于LLM智能体的自动化代码分析与漏洞挖掘框架。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户接口层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web UI    │  │   CLI       │  │   REST API  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      智能体层                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ GenerationAgent │  │  RepairAgent    │  │MutationAgent│ │
│  │ (驱动生成)       │  │  (错误修复)      │  │(覆盖率变异) │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      核心引擎层                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  FuzzEngine     │  │  Validator      │                  │
│  │  (模糊测试调度)  │  │  (编译/运行验证) │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      分析器层                                │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   ASTParser     │  │MetadataExtractor│                  │
│  │   (AST解析)     │  │  (元数据提取)    │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 3. 运行

**启动Web服务:**
```bash
python main.py server
```

**分析项目:**
```bash
python main.py analyze /path/to/project
```

**分析单个文件:**
```bash
python main.py analyze examples/sample_code.c
```

**生成模糊测试驱动:**
```bash
python main.py generate examples/sample_code.c
```

## 功能特性

### 三大智能体

1. **GenerationAgent (指导性程序生成智能体)**
   - 根据代码元数据自动生成模糊测试驱动程序
   - 支持多种API组合策略

2. **RepairAgent (错误修复智能体)**
   - 自动识别和分类编译/运行时错误
   - 迭代修复直到代码可用

3. **MutationAgent (覆盖率指导变异智能体)**
   - 根据覆盖率反馈调整测试策略
   - 智能选择API组合以提高覆盖率

### 代码分析

- 基于Clang的AST解析
- 自动提取函数签名、类型定义
- 支持C/C++/Python

### API接口

- `POST /api/analyze/code` - 分析代码片段
- `POST /api/analyze/project` - 分析整个项目
- `POST /api/generate/harness` - 生成模糊测试驱动

## 项目结构

```
.
├── main.py              # 主入口
├── requirements.txt     # Python依赖
├── Need.txt            # 配置需求说明
├── src/
│   ├── config.py       # 配置管理
│   ├── agents/         # LLM智能体
│   │   ├── base_agent.py
│   │   ├── generation_agent.py
│   │   ├── repair_agent.py
│   │   └── mutation_agent.py
│   ├── analyzers/      # 代码分析器
│   │   ├── ast_parser.py
│   │   └── metadata_extractor.py
│   ├── fuzzer/         # 模糊测试引擎
│   │   ├── engine.py
│   │   └── validator.py
│   ├── api/            # REST API
│   │   └── routes.py
│   └── models/         # 数据模型
├── web/                # 前端界面
│   └── index.html
├── examples/           # 示例代码
│   ├── sample_code.c
│   └── fuzz_config.yaml
└── output/             # 输出目录
    ├── harness/        # 成功的驱动程序
    ├── exception/      # 失败的驱动程序
    └── corpus/         # 测试语料
```

## 配置说明

在项目根目录创建 `fuzz_config.yaml`:

```yaml
name: "my_project"
language: "c"
source_dirs:
  - "src"
target_functions: []  # 留空则自动发现
```

## 技术栈

- **后端**: Python, FastAPI, asyncio
- **LLM**: OpenAI GPT-4 / Anthropic Claude
- **AST解析**: Clang, Tree-sitter
- **模糊测试**: libFuzzer, AFL++
- **前端**: HTML5, CSS3, JavaScript

## License

MIT
