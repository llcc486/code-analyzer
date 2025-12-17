"""分析器测试"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzers.ast_parser import ASTParser
from src.analyzers.metadata_extractor import MetadataExtractor

class TestASTParser:
    """AST解析器测试"""
    
    def setup_method(self):
        self.parser = ASTParser()
    
    def test_extract_python_functions(self, tmp_path):
        """测试Python函数提取"""
        code = '''
def hello(name: str) -> str:
    """Say hello"""
    return f"Hello, {name}"

def add(a: int, b: int) -> int:
    return a + b
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)
        
        functions = self.parser.extract_functions(file_path)
        
        assert len(functions) == 2
        assert functions[0].name == "hello"
        assert functions[1].name == "add"
    
    def test_extract_c_functions(self, tmp_path):
        """测试C函数提取"""
        code = '''
int add(int a, int b) {
    return a + b;
}

void print_message(const char *msg) {
    printf("%s", msg);
}
'''
        file_path = tmp_path / "test.c"
        file_path.write_text(code)
        
        functions = self.parser.extract_functions(file_path)
        
        assert len(functions) >= 2
        func_names = [f.name for f in functions]
        assert "add" in func_names
        assert "print_message" in func_names

class TestMetadataExtractor:
    """元数据提取器测试"""
    
    def setup_method(self):
        self.extractor = MetadataExtractor()
    
    def test_extract_includes(self, tmp_path):
        """测试include提取"""
        code = '''
#include <stdio.h>
#include <stdlib.h>
#include "myheader.h"

int main() { return 0; }
'''
        file_path = tmp_path / "test.c"
        file_path.write_text(code)
        
        includes = self.extractor._extract_includes(file_path)
        
        assert "stdio.h" in includes
        assert "stdlib.h" in includes
        assert "myheader.h" in includes
    
    def test_to_prompt_context(self):
        """测试提示词上下文生成"""
        from src.models.code_metadata import CodeMetadata, FunctionInfo, FunctionParam
        
        metadata = CodeMetadata(
            project_name="test_project",
            language="c",
            functions=[
                FunctionInfo(
                    name="test_func",
                    return_type="int",
                    params=[
                        FunctionParam(name="a", type="int"),
                        FunctionParam(name="b", type="int")
                    ],
                    file_path="test.c",
                    line_number=1
                )
            ]
        )
        
        context = self.extractor.to_prompt_context(metadata)
        
        assert "test_project" in context
        assert "test_func" in context
        assert "int a" in context

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
