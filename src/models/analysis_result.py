"""分析结果模型"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class ErrorType(str, Enum):
    SYNTAX = "syntax"
    LOGIC = "logic"
    MEMORY = "memory"
    TYPE_MISMATCH = "type_mismatch"
    UNDEFINED_SYMBOL = "undefined_symbol"
    RUNTIME = "runtime"

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class CodeError(BaseModel):
    """代码错误"""
    type: ErrorType
    severity: Severity
    message: str
    file_path: str
    line: int
    column: int = 0
    suggestion: Optional[str] = None
    fixed_code: Optional[str] = None

class CoverageInfo(BaseModel):
    """覆盖率信息"""
    total_lines: int = 0
    covered_lines: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    new_paths: int = 0
    
    @property
    def line_coverage(self) -> float:
        return (self.covered_lines / self.total_lines * 100) if self.total_lines > 0 else 0
    
    @property
    def branch_coverage(self) -> float:
        return (self.covered_branches / self.total_branches * 100) if self.total_branches > 0 else 0

class HarnessResult(BaseModel):
    """驱动程序生成结果"""
    harness_code: str
    target_functions: list[str]
    compile_success: bool = False
    run_success: bool = False
    errors: list[CodeError] = []
    coverage: Optional[CoverageInfo] = None

class AnalysisResult(BaseModel):
    """完整分析结果"""
    success: bool
    metadata: Optional[dict] = None
    errors: list[CodeError] = []
    harnesses: list[HarnessResult] = []
    summary: str = ""
