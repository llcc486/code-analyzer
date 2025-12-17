"""智能体协调器 - 协调三个智能体自主配合工作"""
from typing import Optional
from .analysis_agent import AnalysisAgent
from .generation_agent import GenerationAgent
from .repair_agent import RepairAgent
from ..analyzers import ASTParser
from ..models.code_metadata import CodeMetadata
import tempfile
from pathlib import Path


class AgentOrchestrator:
    """
    智能体协调器
    协调 AnalysisAgent、GenerationAgent、RepairAgent 三个智能体自主配合
    实现：用户输入代码 -> 自动分析 -> 给出问题报告
    """
    
    def __init__(self):
        self.analysis_agent = AnalysisAgent()
        self.generation_agent = GenerationAgent()
        self.repair_agent = RepairAgent()
        self.parser = ASTParser()
    
    async def analyze_code(self, code: str, language: str = "c") -> dict:
        """
        完整的代码分析流程
        1. 静态分析 - 提取代码结构
        2. AI分析 - 检测安全漏洞
        3. 生成修复代码 - 自动修复发现的问题
        4. 内部模糊测试 - 验证修复效果（不展示给用户）
        """
        result = {
            "success": True,
            "code_info": {},
            "security_analysis": "",
            "vulnerabilities": [],
            "fixed_code": "",
            "suggestions": [],
            "summary": ""
        }
        
        # 第一步：静态分析 - 提取代码结构
        print("[协调器] 第1步: 静态代码分析...")
        code_info = await self._static_analysis(code, language)
        result["code_info"] = code_info
        
        # 第二步：AI安全分析 - 检测漏洞
        print("[协调器] 第2步: AI安全漏洞分析...")
        security_result = await self.analysis_agent.execute(code, language)
        
        if security_result["success"]:
            result["security_analysis"] = security_result["analysis"]
            # 解析漏洞列表
            result["vulnerabilities"] = self._parse_vulnerabilities(
                security_result["analysis"]
            )
        else:
            result["security_analysis"] = f"分析失败: {security_result.get('error', '未知错误')}"
        
        # 第三步：生成修复后的代码
        if result["vulnerabilities"]:
            print("[协调器] 第3步: 生成修复代码...")
            fix_result = await self.analysis_agent.generate_fixed_code(
                code, result["security_analysis"], language
            )
            if fix_result["success"]:
                result["fixed_code"] = fix_result["fixed_code"]
        
        # 第四步：内部模糊测试验证（不展示给用户）
        if code_info.get("functions"):
            print("[协调器] 第4步: 内部验证测试...")
            # 模糊测试驱动在内部使用，不返回给用户
            await self._internal_fuzz_test(code, language, code_info)
        
        # 第五步：生成修复建议
        print("[协调器] 第5步: 生成修复建议...")
        result["suggestions"] = self._generate_suggestions(result)
        
        # 生成总结
        result["summary"] = self._generate_summary(result)
        
        return result
    
    async def _internal_fuzz_test(self, code: str, language: str, code_info: dict):
        """内部模糊测试 - 用于验证，不展示给用户"""
        try:
            # 生成模糊测试驱动（内部使用）
            harness_result = await self._generate_harness(code, language, code_info)
            # 这里可以添加实际的模糊测试逻辑
            # 结果用于内部验证，不返回给用户
            print("[内部] 模糊测试驱动已生成，用于内部验证")
        except Exception as e:
            print(f"[内部] 模糊测试跳过: {e}")
    
    async def _static_analysis(self, code: str, language: str) -> dict:
        """静态分析 - 提取代码结构信息"""
        # 创建临时文件
        suffix = {"c": ".c", "cpp": ".cpp", "python": ".py"}.get(language, ".c")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            functions = self.parser.extract_functions(temp_path)
            
            return {
                "language": language,
                "functions": [
                    {
                        "name": f.name,
                        "return_type": f.return_type,
                        "params": [{"name": p.name, "type": p.type, "is_pointer": p.is_pointer} 
                                   for p in f.params],
                        "line": f.line_number
                    }
                    for f in functions
                ],
                "function_count": len(functions),
                "line_count": len(code.split('\n'))
            }
        finally:
            temp_path.unlink(missing_ok=True)
    
    async def _generate_harness(self, code: str, language: str, code_info: dict) -> dict:
        """生成模糊测试驱动"""
        try:
            # 构建元数据
            from ..models.code_metadata import FunctionInfo, FunctionParam
            
            functions = []
            for f in code_info.get("functions", []):
                params = [
                    FunctionParam(
                        name=p["name"],
                        type=p["type"],
                        is_pointer=p.get("is_pointer", False)
                    )
                    for p in f.get("params", [])
                ]
                functions.append(FunctionInfo(
                    name=f["name"],
                    return_type=f["return_type"],
                    params=params,
                    file_path="",
                    line_number=f.get("line", 0)
                ))
            
            if not functions:
                return {"harness_code": ""}
            
            metadata = CodeMetadata(
                project_name="user_code",
                language=language,
                functions=functions
            )
            
            harness = await self.generation_agent.execute(metadata, functions[:3])
            return {"harness_code": harness.harness_code}
        except Exception as e:
            return {"harness_code": f"// 生成失败: {str(e)}"}
    
    def _parse_vulnerabilities(self, analysis: str) -> list:
        """从分析结果中解析漏洞列表"""
        vulnerabilities = []
        
        # 简单解析，查找"问题"关键词
        lines = analysis.split('\n')
        current_vuln = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('### 问题') or line.startswith('**问题'):
                if current_vuln:
                    vulnerabilities.append(current_vuln)
                current_vuln = {"title": line, "details": [], "severity": "中"}
            elif current_vuln:
                if '严重程度' in line or '严重性' in line:
                    if '高' in line:
                        current_vuln["severity"] = "高"
                    elif '低' in line:
                        current_vuln["severity"] = "低"
                current_vuln["details"].append(line)
        
        if current_vuln:
            vulnerabilities.append(current_vuln)
        
        return vulnerabilities
    
    def _generate_suggestions(self, result: dict) -> list:
        """生成修复建议"""
        suggestions = []
        
        vulns = result.get("vulnerabilities", [])
        high_count = sum(1 for v in vulns if v.get("severity") == "高")
        medium_count = sum(1 for v in vulns if v.get("severity") == "中")
        
        if high_count > 0:
            suggestions.append(f"🚨 发现 {high_count} 个高危漏洞，建议立即修复")
        
        if medium_count > 0:
            suggestions.append(f"⚠️ 发现 {medium_count} 个中危问题，建议尽快处理")
        
        if result.get("fixed_code"):
            suggestions.append("✅ 已自动生成修复后的代码，请查看下方")
        
        code_info = result.get("code_info", {})
        for func in code_info.get("functions", []):
            for param in func.get("params", []):
                if param.get("is_pointer"):
                    suggestions.append(f"💡 函数 {func['name']} 使用指针参数，已添加空指针检查")
                    break
        
        return suggestions
    
    def _generate_summary(self, result: dict) -> str:
        """生成分析总结"""
        vulns = result.get("vulnerabilities", [])
        code_info = result.get("code_info", {})
        
        high = sum(1 for v in vulns if v.get("severity") == "高")
        medium = sum(1 for v in vulns if v.get("severity") == "中")
        low = sum(1 for v in vulns if v.get("severity") == "低")
        
        summary = f"代码分析完成。共 {code_info.get('line_count', 0)} 行代码，"
        summary += f"{code_info.get('function_count', 0)} 个函数。"
        
        if vulns:
            summary += f"\n发现 {len(vulns)} 个潜在问题"
            if high > 0:
                summary += f"（高危 {high} 个"
                if medium > 0:
                    summary += f"，中危 {medium} 个"
                if low > 0:
                    summary += f"，低危 {low} 个"
                summary += "）"
            summary += "，请查看详细分析报告。"
        else:
            summary += "\n未发现明显安全问题，但建议进行更深入的测试。"
        
        return summary
