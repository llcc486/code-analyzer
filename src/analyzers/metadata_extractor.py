"""代码库元数据提取器"""
import yaml
from pathlib import Path
from typing import Optional
from .ast_parser import ASTParser
from ..models.code_metadata import CodeMetadata, FunctionInfo, TypeDefinition

class MetadataExtractor:
    """代码库元数据提取器 - 对应论文3.1节"""
    
    def __init__(self):
        self.parser = ASTParser()
    
    def extract_from_project(self, project_path: Path, config_path: Optional[Path] = None) -> CodeMetadata:
        """从项目中提取元数据"""
        project_path = Path(project_path)
        
        # 加载项目配置
        project_config = self._load_config(config_path or project_path / "fuzz_config.yaml")
        
        # 收集源文件
        source_files = self._collect_source_files(project_path, project_config)
        
        # 提取函数和类型信息
        all_functions = []
        all_types = []
        all_includes = set()
        
        for src_file in source_files:
            functions = self.parser.extract_functions(src_file)
            all_functions.extend(functions)
            
            # 提取include
            includes = self._extract_includes(src_file)
            all_includes.update(includes)
        
        return CodeMetadata(
            project_name=project_config.get("name", project_path.name),
            language=project_config.get("language", "c"),
            functions=all_functions,
            types=all_types,
            includes=list(all_includes),
            source_files=[str(f) for f in source_files]
        )
    
    def _load_config(self, config_path: Path) -> dict:
        """加载项目配置文件"""
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _collect_source_files(self, project_path: Path, config: dict) -> list[Path]:
        """收集源代码文件"""
        language = config.get("language", "c")
        src_dirs = config.get("source_dirs", ["."])
        
        extensions = {
            "c": [".c", ".h"],
            "cpp": [".cpp", ".hpp", ".cc", ".cxx", ".h"],
            "python": [".py"]
        }.get(language, [".c", ".h"])
        
        files = []
        
        # 首先尝试配置的目录
        for src_dir in src_dirs:
            dir_path = project_path / src_dir
            if dir_path.exists() and dir_path.is_dir():
                for ext in extensions:
                    files.extend(dir_path.rglob(f"*{ext}"))
        
        # 如果没找到，直接搜索项目目录
        if not files:
            for ext in extensions:
                files.extend(project_path.rglob(f"*{ext}"))
        
        return files[:100]  # 限制文件数量
    
    def _extract_includes(self, file_path: Path) -> list[str]:
        """提取include语句"""
        includes = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#include'):
                        # 提取头文件名
                        if '<' in line:
                            inc = line.split('<')[1].split('>')[0]
                        elif '"' in line:
                            inc = line.split('"')[1]
                        else:
                            continue
                        includes.append(inc)
        except Exception:
            pass
        return includes
    
    def to_prompt_context(self, metadata: CodeMetadata) -> str:
        """将元数据转换为提示词上下文"""
        lines = [
            f"# 项目: {metadata.project_name}",
            f"# 语言: {metadata.language}",
            f"# 函数数量: {len(metadata.functions)}",
            "",
            "## 可用函数列表:",
        ]
        
        for func in metadata.functions[:50]:  # 限制数量
            params_str = ", ".join([f"{p.type} {p.name}" for p in func.params])
            lines.append(f"- {func.return_type} {func.name}({params_str})")
            if func.docstring:
                lines.append(f"  说明: {func.docstring[:100]}")
        
        return "\n".join(lines)
