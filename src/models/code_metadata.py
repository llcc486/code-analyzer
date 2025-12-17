"""代码元数据模型"""
from typing import Optional
from pydantic import BaseModel

class FunctionParam(BaseModel):
    """函数参数"""
    name: str
    type: str
    is_pointer: bool = False
    default_value: Optional[str] = None

class FunctionInfo(BaseModel):
    """函数信息"""
    name: str
    return_type: str
    params: list[FunctionParam] = []
    namespace: Optional[str] = None
    file_path: str = ""
    line_number: int = 0
    docstring: Optional[str] = None
    is_public: bool = True

class TypeDefinition(BaseModel):
    """类型定义"""
    name: str
    kind: str  # struct, class, enum, typedef
    members: list[dict] = []
    file_path: str = ""

class CodeMetadata(BaseModel):
    """代码库元数据"""
    project_name: str
    language: str = "c"
    functions: list[FunctionInfo] = []
    types: list[TypeDefinition] = []
    includes: list[str] = []
    source_files: list[str] = []
