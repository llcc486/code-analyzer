"""AST解析器 - 基于Clang和Tree-sitter"""
import subprocess
from pathlib import Path
from typing import Optional
from ..models.code_metadata import FunctionInfo, FunctionParam, TypeDefinition

class ASTParser:
    """抽象语法树解析器"""
    
    def __init__(self):
        self._check_clang()
    
    def _check_clang(self) -> bool:
        """检查Clang是否可用"""
        try:
            result = subprocess.run(
                ["clang", "--version"], 
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def parse_file(self, file_path: Path) -> dict:
        """解析单个文件，提取AST信息"""
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        suffix = file_path.suffix.lower()
        if suffix in ['.c', '.h']:
            return self._parse_c_file(file_path)
        elif suffix in ['.cpp', '.hpp', '.cc', '.cxx']:
            return self._parse_cpp_file(file_path)
        elif suffix == '.py':
            return self._parse_python_file(file_path)
        else:
            return {"error": f"Unsupported file type: {suffix}"}
    
    def _parse_c_file(self, file_path: Path) -> dict:
        """解析C文件"""
        try:
            # 使用clang -ast-dump获取AST
            result = subprocess.run(
                ["clang", "-Xclang", "-ast-dump", "-fsyntax-only", str(file_path)],
                capture_output=True, text=True, timeout=30
            )
            return {
                "success": result.returncode == 0,
                "ast_dump": result.stdout[:10000] if result.stdout else "",
                "errors": result.stderr if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"error": "AST parsing timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_cpp_file(self, file_path: Path) -> dict:
        """解析C++文件"""
        try:
            result = subprocess.run(
                ["clang++", "-Xclang", "-ast-dump", "-fsyntax-only", str(file_path)],
                capture_output=True, text=True, timeout=30
            )
            return {
                "success": result.returncode == 0,
                "ast_dump": result.stdout[:10000] if result.stdout else "",
                "errors": result.stderr if result.stderr else ""
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_python_file(self, file_path: Path) -> dict:
        """解析Python文件"""
        import ast
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
            return {
                "success": True,
                "ast_dump": ast.dump(tree, indent=2)[:10000]
            }
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}
        except Exception as e:
            return {"error": str(e)}
    
    def extract_functions(self, file_path: Path) -> list[FunctionInfo]:
        """从文件中提取函数信息"""
        functions = []
        suffix = file_path.suffix.lower()
        
        if suffix == '.py':
            functions = self._extract_python_functions(file_path)
        elif suffix in ['.c', '.h', '.cpp', '.hpp']:
            functions = self._extract_c_functions(file_path)
        
        return functions
    
    def _extract_python_functions(self, file_path: Path) -> list[FunctionInfo]:
        """提取Python函数"""
        import ast
        functions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    params = []
                    for arg in node.args.args:
                        params.append(FunctionParam(
                            name=arg.arg,
                            type=ast.unparse(arg.annotation) if arg.annotation else "Any"
                        ))
                    
                    docstring = ast.get_docstring(node)
                    functions.append(FunctionInfo(
                        name=node.name,
                        return_type="Any",
                        params=params,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        docstring=docstring,
                        is_public=not node.name.startswith('_')
                    ))
        except Exception:
            pass
        return functions
    
    def _extract_c_functions(self, file_path: Path) -> list[FunctionInfo]:
        """提取C/C++函数 - 简化版本，使用正则匹配"""
        import re
        functions = []
        
        # 标准库函数，需要过滤
        stdlib_funcs = {
            'printf', 'scanf', 'malloc', 'free', 'calloc', 'realloc',
            'strcpy', 'strncpy', 'strcat', 'strlen', 'strcmp', 'strstr',
            'memcpy', 'memset', 'memmove', 'memcmp',
            'atoi', 'atof', 'atol', 'strtol', 'strtod',
            'fopen', 'fclose', 'fread', 'fwrite', 'fprintf', 'fscanf',
            'exit', 'abort', 'assert', 'sizeof'
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 简单的函数签名匹配 - 只匹配函数定义（带花括号的）
            pattern = r'(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*\{'
            matches = re.finditer(pattern, content)
            
            for match in matches:
                return_type = match.group(1).strip()
                func_name = match.group(2).strip()
                params_str = match.group(3).strip()
                
                # 跳过关键字和标准库函数
                if func_name in ['if', 'while', 'for', 'switch', 'return']:
                    continue
                if func_name in stdlib_funcs:
                    continue
                
                params = []
                if params_str and params_str != 'void':
                    for p in params_str.split(','):
                        p = p.strip()
                        if p:
                            parts = p.rsplit(' ', 1)
                            if len(parts) == 2:
                                params.append(FunctionParam(
                                    name=parts[1].replace('*', '').strip(),
                                    type=parts[0].strip(),
                                    is_pointer='*' in p
                                ))
                
                line_num = content[:match.start()].count('\n') + 1
                functions.append(FunctionInfo(
                    name=func_name,
                    return_type=return_type,
                    params=params,
                    file_path=str(file_path),
                    line_number=line_num
                ))
        except Exception:
            pass
        
        return functions
