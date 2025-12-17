"""模糊测试引擎 - 核心调度器"""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from ..config import config
from ..models.code_metadata import CodeMetadata
from ..models.analysis_result import HarnessResult, CoverageInfo, AnalysisResult
from ..agents.generation_agent import GenerationAgent
from ..agents.repair_agent import RepairAgent
from ..agents.mutation_agent import MutationAgent
from .validator import HarnessValidator

class FuzzEngine:
    """模糊测试引擎 - 协调三个智能体的工作"""
    
    def __init__(self):
        self.generation_agent = GenerationAgent()
        self.repair_agent = RepairAgent()
        self.mutation_agent = MutationAgent()
        self.validator = HarnessValidator()
        
        self.tested_combinations: list[list[str]] = []
        self.successful_harnesses: list[HarnessResult] = []
        self.failed_harnesses: list[HarnessResult] = []
        
        self.current_coverage = CoverageInfo()
        self.iteration = 0
    
    async def run(
        self, 
        metadata: CodeMetadata,
        max_iterations: int = None,
        on_progress: Optional[Callable] = None
    ) -> AnalysisResult:
        """运行模糊测试流程"""
        max_iterations = max_iterations or config.fuzzer.max_iterations
        
        print(f"[FuzzEngine] 开始模糊测试，目标项目: {metadata.project_name}")
        print(f"[FuzzEngine] 发现 {len(metadata.functions)} 个函数")
        
        while self.iteration < max_iterations:
            self.iteration += 1
            print(f"\n[Iteration {self.iteration}]")
            
            # 1. 获取新的API组合
            api_combinations = await self.mutation_agent.execute(
                metadata, 
                self.current_coverage,
                self.tested_combinations
            )
            
            if not api_combinations:
                print("  没有新的API组合可测试")
                break
            
            # 2. 为每个组合生成和测试驱动程序
            for combo in api_combinations:
                print(f"  测试组合: {combo}")
                
                # 生成驱动程序
                harness = await self.generation_agent.generate_for_api_combination(
                    metadata, combo
                )
                
                if not harness.harness_code:
                    print(f"    生成失败")
                    continue
                
                # 验证和修复
                harness = await self._validate_and_repair(harness, metadata.language)
                
                # 记录结果
                self.tested_combinations.append(combo)
                
                if harness.compile_success:
                    self.successful_harnesses.append(harness)
                    self._save_harness(harness, "success")
                    print(f"    ✓ 成功")
                    
                    # 运行模糊测试获取覆盖率
                    coverage = await self._run_fuzzing(harness)
                    if coverage:
                        self._update_coverage(coverage)
                else:
                    self.failed_harnesses.append(harness)
                    self._save_harness(harness, "failed")
                    print(f"    ✗ 失败")
            
            # 检查是否达到覆盖率阈值
            if self.current_coverage.line_coverage >= config.fuzzer.coverage_threshold:
                print(f"\n达到覆盖率阈值: {self.current_coverage.line_coverage:.1f}%")
                break
            
            if on_progress:
                on_progress(self.iteration, self.current_coverage)
        
        return self._build_result(metadata)
    
    async def _validate_and_repair(
        self, 
        harness: HarnessResult, 
        language: str
    ) -> HarnessResult:
        """验证并尝试修复驱动程序"""
        # 首先验证语法
        success, error = await self.validator.validate_syntax(
            harness.harness_code, language
        )
        
        if success:
            # 尝试完整编译
            success, error = await self.validator.validate_compile(
                harness.harness_code, language
            )
        
        if success:
            harness.compile_success = True
            return harness
        
        # 尝试修复
        print(f"    尝试修复错误...")
        repaired = await self.repair_agent.execute(harness, error)
        
        # 再次验证
        success, error = await self.validator.validate_compile(
            repaired.harness_code, language
        )
        
        repaired.compile_success = success
        if not success:
            repaired.errors.append(self.repair_agent.classify_error(error))
        
        return repaired
    
    async def _run_fuzzing(self, harness: HarnessResult) -> Optional[CoverageInfo]:
        """运行模糊测试并收集覆盖率"""
        success, output = await self.validator.run_quick_test(harness.harness_code)
        
        # 解析覆盖率信息（简化版）
        coverage = CoverageInfo()
        
        if "cov:" in output.lower():
            # 尝试解析libFuzzer输出
            try:
                for line in output.split('\n'):
                    if 'cov:' in line.lower():
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p.lower() == 'cov:' and i + 1 < len(parts):
                                coverage.covered_lines = int(parts[i + 1])
            except Exception:
                pass
        
        return coverage
    
    def _update_coverage(self, new_coverage: CoverageInfo):
        """更新覆盖率信息"""
        self.current_coverage.covered_lines = max(
            self.current_coverage.covered_lines,
            new_coverage.covered_lines
        )
        self.current_coverage.new_paths += new_coverage.new_paths
    
    def _save_harness(self, harness: HarnessResult, status: str):
        """保存驱动程序到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        func_names = "_".join(harness.target_functions[:2])
        filename = f"harness_{func_names}_{timestamp}.c"
        
        if status == "success":
            path = config.harness_dir / filename
        else:
            path = config.exception_dir / filename
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"// Target functions: {harness.target_functions}\n")
            f.write(f"// Status: {status}\n")
            f.write(f"// Generated: {timestamp}\n\n")
            f.write(harness.harness_code)
    
    def _build_result(self, metadata: CodeMetadata) -> AnalysisResult:
        """构建最终结果"""
        return AnalysisResult(
            success=len(self.successful_harnesses) > 0,
            metadata={
                "project": metadata.project_name,
                "total_functions": len(metadata.functions),
                "tested_combinations": len(self.tested_combinations),
                "iterations": self.iteration
            },
            harnesses=self.successful_harnesses,
            summary=f"生成了 {len(self.successful_harnesses)} 个有效驱动程序，"
                    f"覆盖率: {self.current_coverage.line_coverage:.1f}%"
        )
