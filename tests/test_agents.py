"""智能体测试"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.code_metadata import CodeMetadata, FunctionInfo, FunctionParam
from src.models.analysis_result import HarnessResult, CoverageInfo, ErrorType
from src.agents.repair_agent import RepairAgent
from src.agents.mutation_agent import MutationAgent

class TestRepairAgent:
    """修复智能体测试"""
    
    def setup_method(self):
        self.agent = RepairAgent()
    
    def test_classify_undefined_symbol(self):
        """测试未定义符号错误分类"""
        error = self.agent.classify_error("undefined reference to 'foo'")
        assert error.type == ErrorType.UNDEFINED_SYMBOL
    
    def test_classify_type_mismatch(self):
        """测试类型不匹配错误分类"""
        error = self.agent.classify_error("incompatible type for argument")
        assert error.type == ErrorType.TYPE_MISMATCH
    
    def test_classify_syntax_error(self):
        """测试语法错误分类"""
        error = self.agent.classify_error("syntax error: expected ';'")
        assert error.type == ErrorType.SYNTAX
    
    def test_classify_memory_error(self):
        """测试内存错误分类"""
        error = self.agent.classify_error("segmentation fault")
        assert error.type == ErrorType.MEMORY

class TestMutationAgent:
    """变异智能体测试"""
    
    def setup_method(self):
        self.agent = MutationAgent()
        self.metadata = CodeMetadata(
            project_name="test",
            language="c",
            functions=[
                FunctionInfo(name="func_a", return_type="int", file_path="a.c", line_number=1),
                FunctionInfo(name="func_b", return_type="void", file_path="b.c", line_number=1),
                FunctionInfo(name="func_c", return_type="char*", file_path="c.c", line_number=1),
            ]
        )
    
    def test_heuristic_combinations(self):
        """测试启发式组合生成"""
        tested = [["func_a"]]
        combinations = self.agent._heuristic_combinations(self.metadata, tested)
        
        assert len(combinations) > 0
        # 不应该重复已测试的组合
        for combo in combinations:
            if len(combo) == 1:
                assert combo != ["func_a"]
    
    def test_update_api_weights(self):
        """测试API权重更新"""
        self.agent.update_api_weights("func_a", 10.0)
        assert self.agent.api_weights["func_a"] > 1.0
    
    def test_get_priority_apis(self):
        """测试优先级API获取"""
        self.agent.api_weights = {
            "func_a": 5.0,
            "func_b": 1.0,
            "func_c": 3.0
        }
        
        priority = self.agent.get_priority_apis(self.metadata, top_k=2)
        
        assert priority[0] == "func_a"
        assert priority[1] == "func_c"
    
    def test_calculate_coverage_gain(self):
        """测试覆盖率增益计算"""
        self.agent.coverage_history = [
            CoverageInfo(total_lines=100, covered_lines=50),
            CoverageInfo(total_lines=100, covered_lines=60)
        ]
        
        gain = self.agent._calculate_coverage_gain()
        assert gain == 10.0  # 60% - 50% = 10%

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
