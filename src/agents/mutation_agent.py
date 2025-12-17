"""覆盖率指导变异智能体 - 对应论文3.5节"""
import random
from typing import Optional
from .base_agent import BaseAgent
from ..models.code_metadata import CodeMetadata, FunctionInfo
from ..models.analysis_result import CoverageInfo, HarnessResult

SYSTEM_PROMPT = """你是一个模糊测试优化专家。
你的任务是根据覆盖率反馈，建议新的API组合和测试策略。

优化目标:
1. 提高代码覆盖率
2. 探索未触及的代码路径
3. 发现边界条件和异常情况
4. 生成更有效的测试输入

输出格式: JSON格式，包含建议的API组合和变异策略。
"""

class MutationAgent(BaseAgent):
    """覆盖率指导变异智能体"""
    
    def __init__(self):
        super().__init__("MutationAgent")
        self.api_weights: dict[str, float] = {}  # API权重
        self.coverage_history: list[CoverageInfo] = []
    
    async def execute(
        self, 
        metadata: CodeMetadata, 
        current_coverage: CoverageInfo,
        tested_combinations: list[list[str]]
    ) -> list[list[str]]:
        """根据覆盖率反馈生成新的API组合"""
        # 更新覆盖率历史
        self.coverage_history.append(current_coverage)
        
        # 计算覆盖率增益
        coverage_gain = self._calculate_coverage_gain()
        
        # 使用LLM建议新组合
        if coverage_gain < 5 and len(self.coverage_history) > 3:
            # 覆盖率增长缓慢，请求LLM建议
            new_combinations = await self._llm_suggest_combinations(
                metadata, current_coverage, tested_combinations
            )
        else:
            # 使用启发式方法生成组合
            new_combinations = self._heuristic_combinations(
                metadata, tested_combinations
            )
        
        return new_combinations
    
    def _calculate_coverage_gain(self) -> float:
        """计算最近的覆盖率增益"""
        if len(self.coverage_history) < 2:
            return 100.0
        
        recent = self.coverage_history[-1]
        previous = self.coverage_history[-2]
        
        if previous.line_coverage == 0:
            return 100.0
        
        return recent.line_coverage - previous.line_coverage
    
    async def _llm_suggest_combinations(
        self,
        metadata: CodeMetadata,
        coverage: CoverageInfo,
        tested: list[list[str]]
    ) -> list[list[str]]:
        """使用LLM建议新的API组合"""
        prompt = self._build_suggestion_prompt(metadata, coverage, tested)
        response = await self.call_llm(prompt, SYSTEM_PROMPT)
        
        # 解析响应
        return self._parse_combinations(response, metadata)
    
    def _build_suggestion_prompt(
        self,
        metadata: CodeMetadata,
        coverage: CoverageInfo,
        tested: list[list[str]]
    ) -> str:
        """构建建议提示词"""
        available_apis = [f.name for f in metadata.functions]
        
        return f"""当前模糊测试状态:
- 行覆盖率: {coverage.line_coverage:.1f}%
- 分支覆盖率: {coverage.branch_coverage:.1f}%
- 新路径数: {coverage.new_paths}

已测试的API组合:
{tested[-10:] if len(tested) > 10 else tested}

可用的API列表:
{available_apis[:30]}

请建议3-5个新的API组合，以提高覆盖率。
每个组合包含1-3个API。
输出格式: 每行一个组合，API用逗号分隔。
"""
    
    def _parse_combinations(
        self, 
        response: str, 
        metadata: CodeMetadata
    ) -> list[list[str]]:
        """解析LLM响应中的API组合"""
        valid_apis = {f.name for f in metadata.functions}
        combinations = []
        
        for line in response.strip().split('\n'):
            line = line.strip().strip('-').strip('*').strip()
            if not line:
                continue
            
            apis = [a.strip() for a in line.split(',')]
            valid_combo = [a for a in apis if a in valid_apis]
            
            if valid_combo:
                combinations.append(valid_combo)
        
        return combinations[:5]  # 最多返回5个组合
    
    def _heuristic_combinations(
        self,
        metadata: CodeMetadata,
        tested: list[list[str]]
    ) -> list[list[str]]:
        """启发式生成API组合"""
        tested_set = {tuple(sorted(c)) for c in tested}
        all_apis = [f.name for f in metadata.functions if f.is_public]
        
        combinations = []
        
        # 策略1: 单API测试
        for api in all_apis:
            if tuple([api]) not in tested_set:
                combinations.append([api])
                if len(combinations) >= 2:
                    break
        
        # 策略2: 随机组合
        for _ in range(3):
            size = random.randint(2, min(3, len(all_apis)))
            combo = random.sample(all_apis, size)
            if tuple(sorted(combo)) not in tested_set:
                combinations.append(combo)
        
        return combinations[:5]
    
    def update_api_weights(self, api_name: str, coverage_delta: float):
        """更新API权重"""
        current = self.api_weights.get(api_name, 1.0)
        # 覆盖率增益越大，权重越高
        self.api_weights[api_name] = current + coverage_delta * 0.1
    
    def get_priority_apis(self, metadata: CodeMetadata, top_k: int = 10) -> list[str]:
        """获取优先级最高的API"""
        apis_with_weights = [
            (f.name, self.api_weights.get(f.name, 1.0))
            for f in metadata.functions
        ]
        apis_with_weights.sort(key=lambda x: x[1], reverse=True)
        return [a[0] for a in apis_with_weights[:top_k]]
