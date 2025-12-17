"""代码分析智能体 - 检测代码问题并生成修复代码"""
from typing import Optional
from .base_agent import BaseAgent

SYSTEM_PROMPT = """你是一个专业的代码安全分析专家。
你的任务是分析用户提供的代码，找出其中的安全漏洞、逻辑错误和潜在问题。

分析维度：
1. 安全漏洞：缓冲区溢出、SQL注入、XSS、命令注入、整数溢出等
2. 内存问题：内存泄漏、空指针解引用、野指针、双重释放等
3. 逻辑错误：边界条件错误、死循环、竞态条件等
4. 代码质量：未初始化变量、未检查返回值、资源未释放等

输出格式（使用中文）：
## 发现的问题

### 问题1: [问题类型]
- 严重程度: 高/中/低
- 位置: 第X行
- 描述: 具体问题描述
- 修复建议: 如何修复

### 问题2: ...

## 总结
总共发现X个问题，其中高危X个，中危X个，低危X个。

如果代码没有明显问题，也要说明代码的优点和可能的改进建议。
"""

FIX_SYSTEM_PROMPT = """你是一个专业的代码修复专家。
你的任务是根据发现的安全问题，生成修复后的完整代码。

修复原则：
1. 保持原有功能不变
2. 修复所有发现的安全漏洞
3. 添加必要的边界检查和错误处理
4. 添加注释说明修复了什么问题
5. 代码风格保持一致

输出格式：只输出修复后的完整代码，用```包裹。在关键修复处添加注释说明。
"""

class AnalysisAgent(BaseAgent):
    """代码分析智能体 - 检测安全漏洞和代码问题，并生成修复代码"""
    
    def __init__(self):
        super().__init__("AnalysisAgent")
    
    async def execute(self, code: str, language: str = "c") -> dict:
        """分析代码，返回问题列表"""
        prompt = self._build_prompt(code, language)
        
        try:
            response = await self.call_llm(prompt, SYSTEM_PROMPT)
            return {
                "success": True,
                "analysis": response,
                "language": language
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": ""
            }
    
    async def generate_fixed_code(self, code: str, analysis: str, language: str = "c") -> dict:
        """根据分析结果生成修复后的代码"""
        prompt = self._build_fix_prompt(code, analysis, language)
        
        try:
            response = await self.call_llm(prompt, FIX_SYSTEM_PROMPT)
            fixed_code = self._extract_code(response)
            return {
                "success": True,
                "fixed_code": fixed_code
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fixed_code": ""
            }
    
    def _build_prompt(self, code: str, language: str) -> str:
        """构建分析提示词"""
        lang_name = {"c": "C", "cpp": "C++", "python": "Python"}.get(language, language)
        
        return f"""请分析以下{lang_name}代码，找出其中的安全漏洞、逻辑错误和潜在问题：

```{language}
{code}
```

请仔细检查：
1. 是否存在缓冲区溢出风险
2. 是否有空指针解引用
3. 是否有内存泄漏
4. 是否有整数溢出
5. 输入验证是否充分
6. 边界条件是否正确处理
7. 是否有其他安全隐患

请用中文详细说明每个问题及修复建议。
"""
    
    def _build_fix_prompt(self, code: str, analysis: str, language: str) -> str:
        """构建修复提示词"""
        lang_name = {"c": "C", "cpp": "C++", "python": "Python"}.get(language, language)
        
        return f"""以下是原始{lang_name}代码：

```{language}
{code}
```

发现的问题：
{analysis}

请生成修复后的完整代码，修复上述所有问题。在修复的关键位置添加注释说明修复了什么。
"""
    
    def _extract_code(self, response: str) -> str:
        """从响应中提取代码"""
        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 1:  # 代码块内容
                    # 去掉语言标识
                    lines = part.split('\n')
                    if lines[0].strip() in ['c', 'cpp', 'python', 'C', 'C++', 'Python', '']:
                        return '\n'.join(lines[1:]).strip()
                    return part.strip()
        return response.strip()
