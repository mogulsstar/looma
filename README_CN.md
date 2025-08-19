# Looma - Python 应用打包与自动更新平台

[![Python 版本](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![许可证](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![平台](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/yourusername/looma)

一个综合性的 Python 打包和自动更新平台，支持 GUI 和 CLI 双模式，具有插件架构和动态配置功能。

## ✨ 特性

- 🎯 **多引擎支持**：PyInstaller、Nuitka、cx_Freeze，采用插件架构
- 🔄 **自动更新系统**：内置更新客户端，支持多种策略（提示/静默/强制）
- 🖥️ **双界面模式**：GUI（wxPython）和 CLI 模式
- 🔐 **安全优先**：所有包使用 Ed25519 签名
- 📦 **多源支持**：GitHub、GitLab、S3、Artifactory、HTTP
- 🚀 **CI/CD 就绪**：完全支持自动化，非交互模式
- 🌍 **跨平台**：支持 Windows、macOS 和 Linux
- 🔧 **插件系统**：可扩展架构，支持自定义引擎和上传器
- 📋 **动态配置**：基于 JSON Schema 的参数验证，GUI 自动生成表单

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install looma

# 包含 GUI 支持
pip install looma[gui]

# 包含所有打包引擎
pip install looma[all]

# 开发安装
pip install -e ".[dev]"
```

### GUI 模式

启动配置向导进行首次设置：

```bash
# 新用户向导模式
looma gui --wizard

# 编辑现有配置
looma gui --config looma.yml
```

### CLI 模式

使用单个命令构建您的应用程序：

```bash
# 基础构建
looma build --config looma.yml

# 指定引擎和平台
looma build --engine nuitka --platform windows

# 并行多平台构建
looma build --platform all --parallel
```

### 配置

初始化新项目：

```bash
# 交互式向导
looma init --wizard

# 从模板创建
looma init --template gui --output myapp.yml
```

## 📖 使用示例

### 基础打包

```bash
# 使用 PyInstaller 构建
looma build --engine pyinstaller --config looma.yml

# 使用 Nuitka 构建
looma build --engine nuitka --source github --channel beta

# CI/CD 模式（非交互式）
looma build --config looma.yml --no-interactive
```

### 更新管理

```bash
# 检查更新
looma check --channel stable

# 强制更新
looma check --force

# 上传到多个目标
looma upload --target github --target s3 --channel stable
```

### 插件管理

```bash
# 列出可用引擎
looma engines

# 显示引擎 Schema
looma schema pyinstaller

# 验证配置
looma validate --schema
```

## 📋 配置

### 基础配置（`looma.yml`）

```yaml
version: "1.0"

app:
  name: "MyApp"
  version: "1.0.0"
  description: "我的应用程序"
  author: "您的名字"
  
packaging:
  engine: "pyinstaller"
  entry_point: "main.py"
  one_file: true
  console: false
  
update:
  source:
    type: "github"
    repo: "owner/repo"
    token: "${GITHUB_TOKEN}"  # 环境变量替换
  channel: "stable"
  strategy: "prompt"  # 提示、静默或强制
  
security:
  signing:
    enabled: true
    private_key_path: "keys/private.key"
    algorithm: "ed25519"
```

### 多环境支持

Looma 支持特定环境的配置：

- `looma.yml` - 默认配置
- `looma-dev.yml` - 开发环境
- `looma-test.yml` - 测试环境
- `looma-prod.yml` - 生产环境
- `looma-win.yml` - Windows 平台
- `looma-mac.yml` - macOS 平台
- `looma-linux.yml` - Linux 平台

### 更新策略

#### 提示策略
```yaml
update:
  strategy: prompt
  ui:
    show_release_notes: true
    allow_skip: true
    allow_remind_later: true
    remind_interval: 86400  # 24 小时
```

#### 强制策略
```yaml
update:
  strategy: force
  ui:
    force_after_days: 3
    show_release_notes: true
```

#### 静默策略
```yaml
update:
  strategy: silent
  ui:
    show_progress: false
    notify_on_success: true
```

## 🏗️ 项目结构

### 您的应用程序结构
```
your-app/
├── src/               # 源代码目录
│   └── your_app/     # 应用程序包
├── looma.yml         # 配置文件
├── main.py          # 应用程序入口点
├── requirements.txt # Python 依赖
├── pyproject.toml   # 项目元数据
└── keys/           # 签名密钥（git 忽略）
    ├── private.key
    └── public.key
```

### Looma 源码结构
```
looma/
├── src/looma/
│   ├── core/         # 核心功能
│   ├── packager/     # 打包引擎
│   │   ├── base.py   # 基础打包器接口
│   │   ├── factory.py # 打包器工厂
│   │   ├── pyinstaller.py
│   │   ├── nuitka.py
│   │   └── cxfreeze.py
│   ├── client/       # 更新客户端
│   ├── sources/      # 更新源
│   │   ├── base.py   # 基础源接口
│   │   ├── factory.py # 源工厂
│   │   ├── github.py
│   │   ├── gitlab.py
│   │   └── s3.py
│   ├── security/     # 安全模块
│   ├── gui/          # GUI 组件
│   │   ├── wizard.py # 配置向导
│   │   ├── editor.py # 配置编辑器
│   │   └── dynamic_config_page.py # 动态表单生成
│   └── cli/          # CLI 命令
│       └── main.py   # CLI 入口点
├── tests/            # 测试套件
├── docs/             # 文档
└── examples/         # 示例项目
```

## 🔧 高级功能

### 增量更新

Looma 支持使用二进制差分的增量更新：

```yaml
update:
  delta:
    enabled: true
    threshold: 5242880  # 5MB - 大于此值的文件使用增量更新
    algorithm: "bsdiff"
```

### 自定义打包器实现

创建您自己的打包引擎：

```python
from looma.packager.base import BasePackager

class CustomPackager(BasePackager):
    """自定义打包引擎。"""
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """返回动态配置的参数架构。"""
        return {
            "custom_option": {
                "type": "string",
                "description": "自定义选项描述",
                "default": "value"
            }
        }
    
    def build(self, entry_point: str, output_dir: Path, **options) -> Path:
        """构建应用程序。"""
        # 实现在这里
        pass
```

### 自定义更新源

注册您自己的更新源：

```python
from looma.sources.base import BaseSource
from looma.sources.factory import SourceFactory

class CustomSource(BaseSource):
    """自定义更新源。"""
    
    async def get_versions(self, channel: str) -> List[Dict[str, Any]]:
        """获取可用版本。"""
        # 实现在这里
        pass
    
    async def download_update(self, version: str, target_path: Path) -> Path:
        """下载更新包。"""
        # 实现在这里
        pass

# 注册源
SourceFactory.register("custom", CustomSource)
```

### CI/CD 集成

GitHub Actions 示例：

```yaml
name: 构建和发布
on:
  push:
    tags:
      - 'v*'
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - run: pip install looma
      - run: looma build --config looma.yml --no-interactive
      - run: looma upload --target github --channel stable
      - uses: actions/upload-artifact@v3
        with:
          name: builds
          path: dist/
```

### 构建钩子

配置构建前/后钩子：

```yaml
build:
  hooks:
    pre_build:
      - "python scripts/prepare.py"
      - "npm run build"
    post_build:
      - "python scripts/cleanup.py"
    on_error:
      - "python scripts/notify.py"
```

## 🌐 环境变量

Looma 支持在配置中使用环境变量替换：

```yaml
update:
  source:
    token: "${GITHUB_TOKEN}"  # 将使用 GITHUB_TOKEN 环境变量
```

通过环境变量覆盖配置：

```bash
export LOOMA_UPDATE_CHANNEL=beta
export LOOMA_SOURCE_TOKEN=your-token
looma build --config looma.yml
```

## 📚 文档

完整文档可用：

- [入门指南](docs/getting-started.md)
- [配置指南](docs/configuration.md)
- [GUI 教程](docs/gui-tutorial.md)
- [CLI 参考](docs/cli-reference.md)
- [插件开发](docs/plugins.md)
- [安全最佳实践](docs/security.md)
- [API 文档](docs/api.md)

## 💡 示例

查看 `examples/` 目录中的完整示例：

- [简单 PyQt 应用](examples/pyqt-app/)
- [带更新的 CLI 工具](examples/cli-tool/)
- [多平台构建](examples/multi-platform/)
- [自定义插件](examples/custom-plugin/)

## 📋 系统要求

- Python 3.8 或更高版本
- wxPython 4.2+（GUI 模式）
- 以下打包引擎之一：
  - PyInstaller 5.0+
  - Nuitka 1.8+
  - cx_Freeze 6.15+

## 🤝 贡献

我们欢迎贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

### 开发设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/looma.git
cd looma

# 开发模式安装
pip install -e ".[dev]"

# 运行测试
pytest

# 运行代码检查
ruff check src/ tests/

# 格式化代码
black src/ tests/
```

## 🆘 支持

- 📖 [文档](https://looma.readthedocs.io)
- 💬 [讨论](https://github.com/yourusername/looma/discussions)
- 🐛 [问题跟踪](https://github.com/yourusername/looma/issues)
- 📧 [邮件支持](mailto:support@looma.dev)

## 📄 许可证

Looma 在 MIT 许可证下发布。详见 [LICENSE](LICENSE)。

## 🙏 致谢

- PyInstaller、Nuitka 和 cx_Freeze 团队提供的优秀打包工具
- wxPython 团队提供的 GUI 框架
- 所有 Looma 的贡献者和用户

---

**Looma** - 让 Python 应用分发变得简单而强大 🚀