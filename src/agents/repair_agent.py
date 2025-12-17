"""错误驱动程序验证修复智能体 - 对应论文3.4节"""
from typing import Optional
from .base_agent import BaseAgent
from ..models.analysis_result import HarnessResult, CodeError, ErrorType, Severity

SYSTEM_PROMPT = """你是一个专业的代码修复专家。
你的任务是分析编译或运行时错误，并修复模糊测试驱动程序。

修复原则:
1. 保持原有的测试意图不变
2. 只修复导致错误的具体问题
3. 不要大幅重构代码
4. 确保修复后的代码能够编译通过
5. 添加必要的错误处理

输出格式: 只输出修复后的完整代码，用```c或```cpp包裹。
"""

class RepairAgent(BaseAgent):
    """错误驱动程序验证修复智能体"""
    
    def __init__(self):
        super().__init__("RepairAgent")
        self.max_repair_attempts = 3
    
    async def execute(
        self, 
        harness: HarnessResult, 
        error_info: str
    ) -> HarnessResult:
        """修复错误的驱动程序"""
        prompt = self._build_repair_prompt(harness.harness_code, error_info)
        response = await self.call_llm(prompt, SYSTEM_PROMPT)
        
        fixed_code = self._extract_code(response)
        
        return HarnessResult(
            harness_code=fixed_code,
            target_functions=harness.target_functions,
            compile_success=False,  # 需要重新验证
            run_success=False
        )
    
    def _build_repair_prompt(self, code: str, error_info: str) -> str:
        """构建修复提示词"""
        return f"""请修复以下模糊测试驱动程序中的错误。

原始代码:
```c
{code}
```

错误信息:
{error_info}

请分析错误原因并提供修复后的完整代码。
"""
    
    def _extract_code(self, response: str) -> str:
        """从响应中提取代码"""
        for marker in ["```c", "```cpp", "```"]:
            if marker in response:
                start = response.find(marker) + len(marker)
                end = response.find("```", start)
                if end > start:
                    return response[start:end].strip()
        return response.strip()
    
    def classify_error(self, error_message: str) -> CodeError:
        """分类错误类型"""
        error_lower = error_message.lower()
        
        if "undefined reference" in error_lower or "undeclared" in error_lower:
            return CodeError(
                type=ErrorType.UNDEFINED_SYMBOL,
                severity=Severity.ERROR,
                message=error_message,
                file_path="",
                line=0,
                suggestion="检查是否缺少头文件或链接库"
            )
        
        if "type" in error_lower and ("mismatch" in error_lower or "incompatible" in error_lower):
            return CodeError(
                type=ErrorType.TYPE_MISMATCH,
                severity=Severity.ERROR,
                message=error_message,
                file_path="",
                line=0,
                suggestion="检查参数类型是否正确"
            )
        
        if "syntax error" in error_lower or "expected" in error_lower:
            return CodeError(
                type=ErrorType.SYNTAX,
                severity=Severity.ERROR,
                message=error_message,
                file_path="",
                line=0,
                suggestion="检查语法错误"
            )
        
        if "segmentation fault" in error_lower or "null pointer" in error_lower:
            return CodeError(
                type=ErrorType.MEMORY,
                severity=Severity.CRITICAL,
                message=error_message,
                file_path="",
                line=0,
                suggestion="检查指针是否正确初始化"
            )
        
        return CodeError(
            type=ErrorType.RUNTIME,
            severity=Severity.ERROR,
            message=error_message,
            file_path="",
            line=0
        )
    
    async def iterative_repair(
        self, 
        harness: HarnessResult, 
        validator_func
    ) -> HarnessResult:
        """迭代修复直到成功或达到最大尝试次数"""
        current_harness = harness
        
        for attempt in range(self.max_repair_attempts):
            # 验证当前代码
            is_valid, error_info = await validator_func(current_harness.harness_code)
            
            if is_valid:
                current_harness.compile_success = True
                return current_harness
            
            # 尝试修复
            current_harness = await self.execute(current_harness, error_info)
            current_harness.errors.append(
                self.classify_error(error_info)
            )
        
        return current_harness
