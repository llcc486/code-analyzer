"""指导性程序生成智能体 - 对应论文3.3节"""
from typing import Optional
from .base_agent import BaseAgent
from ..models.code_metadata import CodeMetadata, FunctionInfo
from ..models.analysis_result import HarnessResult

SYSTEM_PROMPT = """你是一个专业的模糊测试驱动程序生成专家。
你的任务是根据提供的函数信息，生成高质量的模糊测试驱动程序(harness)。

生成规则:
1. 驱动程序必须能够编译通过
2. 正确处理函数参数，特别是指针类型需要正确初始化
3. 使用libFuzzer的标准入口函数 LLVMFuzzerTestOneInput
4. 添加必要的边界检查和错误处理
5. 尽量覆盖函数的不同执行路径

输出格式: 只输出代码，不要解释。代码用```c或```cpp包裹。
"""

class GenerationAgent(BaseAgent):
    """指导性程序生成智能体"""
    
    def __init__(self):
        super().__init__("GenerationAgent")
    
    async def execute(self, metadata: CodeMetadata, target_functions: list[FunctionInfo]) -> HarnessResult:
        """生成模糊测试驱动程序"""
        prompt = self._build_prompt(metadata, target_functions)
        response = await self.call_llm(prompt, SYSTEM_PROMPT)
        
        # 提取代码
        harness_code = self._extract_code(response)
        
        return HarnessResult(
            harness_code=harness_code,
            target_functions=[f.name for f in target_functions]
        )
    
    def _build_prompt(self, metadata: CodeMetadata, functions: list[FunctionInfo]) -> str:
        """构建提示词 - 对应论文3.2节"""
        lines = [
            f"请为以下{metadata.language.upper()}函数生成模糊测试驱动程序:",
            ""
        ]
        
        # 添加头文件信息
        if metadata.includes:
            lines.append("需要包含的头文件:")
            for inc in metadata.includes[:10]:
                lines.append(f"  #include <{inc}>")
            lines.append("")
        
        # 添加目标函数信息
        lines.append("目标函数:")
        for func in functions:
            params_str = ", ".join([
                f"{p.type}{' *' if p.is_pointer else ''} {p.name}" 
                for p in func.params
            ])
            lines.append(f"  {func.return_type} {func.name}({params_str})")
            
            if func.docstring:
                lines.append(f"    // {func.docstring[:200]}")
            
            # 添加参数约束提示
            for p in func.params:
                if p.is_pointer:
                    lines.append(f"    // 注意: {p.name} 是指针类型，需要正确初始化")
        
        lines.extend([
            "",
            "要求:",
            "1. 使用 LLVMFuzzerTestOneInput 作为入口函数",
            "2. 从模糊输入数据中提取参数值",
            "3. 添加必要的边界检查",
            "4. 处理可能的异常情况"
        ])
        
        return "\n".join(lines)
    
    def _extract_code(self, response: str) -> str:
        """从LLM响应中提取代码"""
        # 尝试提取代码块
        if "```c" in response:
            start = response.find("```c") + 4
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```cpp" in response:
            start = response.find("```cpp") + 6
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        return response.strip()
    
    async def generate_for_api_combination(
        self, 
        metadata: CodeMetadata, 
        api_names: list[str]
    ) -> HarnessResult:
        """为指定的API组合生成驱动程序"""
        # 查找对应的函数信息
        target_functions = [
            f for f in metadata.functions 
            if f.name in api_names
        ]
        
        if not target_functions:
            return HarnessResult(
                harness_code="",
                target_functions=api_names,
                compile_success=False,
                errors=[{"message": "No matching functions found"}]
            )
        
        return await self.execute(metadata, target_functions)
