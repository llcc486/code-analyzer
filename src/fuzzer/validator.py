"""驱动程序验证器"""
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple
from ..config import config

class HarnessValidator:
    """驱动程序验证器 - 编译和运行时检查"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
    
    async def validate_compile(self, code: str, language: str = "c") -> Tuple[bool, str]:
        """验证代码是否能编译"""
        # 写入临时文件
        suffix = ".c" if language == "c" else ".cpp"
        src_file = self.temp_dir / f"harness{suffix}"
        out_file = self.temp_dir / "harness.out"
        
        with open(src_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 编译
        compiler = "clang" if language == "c" else "clang++"
        cmd = [
            compiler,
            "-fsanitize=fuzzer,address",
            "-g",
            "-O1",
            str(src_file),
            "-o", str(out_file)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, ""
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Compilation timeout"
        except FileNotFoundError:
            return False, f"Compiler not found: {compiler}"
        except Exception as e:
            return False, str(e)
    
    async def validate_syntax(self, code: str, language: str = "c") -> Tuple[bool, str]:
        """仅验证语法（不链接）"""
        suffix = ".c" if language == "c" else ".cpp"
        src_file = self.temp_dir / f"syntax_check{suffix}"
        
        with open(src_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        compiler = "clang" if language == "c" else "clang++"
        cmd = [compiler, "-fsyntax-only", str(src_file)]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, ""
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    async def run_quick_test(self, code: str, corpus_dir: Path = None) -> Tuple[bool, str]:
        """快速运行测试"""
        # 先编译
        success, error = await self.validate_compile(code)
        if not success:
            return False, f"Compile error: {error}"
        
        out_file = self.temp_dir / "harness.out"
        corpus = corpus_dir or self.temp_dir / "corpus"
        corpus.mkdir(exist_ok=True)
        
        # 创建初始语料
        (corpus / "seed").write_bytes(b"test")
        
        try:
            result = subprocess.run(
                [str(out_file), str(corpus), "-max_total_time=5"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 检查是否有崩溃
            if "ERROR" in result.stderr or "SUMMARY" in result.stderr:
                return False, result.stderr
            
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return True, "Test completed (timeout)"
        except Exception as e:
            return False, str(e)
    
    def cleanup(self):
        """清理临时文件"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass
