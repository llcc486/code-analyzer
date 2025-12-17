"""API路由"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import tempfile
import shutil

from ..analyzers import MetadataExtractor, ASTParser
from ..fuzzer import FuzzEngine
from ..models.analysis_result import AnalysisResult

router = APIRouter()

class AnalyzeRequest(BaseModel):
    project_path: str
    max_iterations: int = 100
    target_functions: Optional[list[str]] = None

class CodeAnalyzeRequest(BaseModel):
    code: str
    language: str = "c"
    filename: str = "code.c"

@router.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能代码分析系统 API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": [
            "GET /api/health - 健康检查",
            "POST /api/analyze/code - 分析代码结构",
            "POST /api/analyze/security - 🔥 一键安全分析（推荐）",
            "POST /api/analyze/project - 分析项目",
            "POST /api/generate/harness - 生成驱动"
        ]
    }


@router.post("/analyze/security")
async def analyze_security(request: CodeAnalyzeRequest) -> dict:
    """
    🔥 一键代码安全分析（三个智能体协作）
    
    输入代码，自动：
    1. 静态分析 - 提取代码结构
    2. AI安全分析 - 检测漏洞和问题
    3. 生成测试驱动 - 用于进一步测试
    4. 给出修复建议
    """
    from ..agents import AgentOrchestrator
    
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="代码不能为空")
    
    orchestrator = AgentOrchestrator()
    
    try:
        result = await orchestrator.analyze_code(request.code, request.language)
        return result
    except Exception as e:
        error_msg = str(e)
        if "余额不足" in error_msg:
            raise HTTPException(status_code=402, detail="API账户余额不足，请充值后重试")
        elif "密钥无效" in error_msg:
            raise HTTPException(status_code=401, detail="API密钥无效，请检查.env配置")
        else:
            raise HTTPException(status_code=500, detail=f"分析失败: {error_msg}")

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "code-analyzer"}

@router.post("/analyze/project")
async def analyze_project(request: AnalyzeRequest) -> dict:
    """分析整个项目"""
    project_path = Path(request.project_path)
    
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project path not found")
    
    # 提取元数据
    extractor = MetadataExtractor()
    metadata = extractor.extract_from_project(project_path)
    
    if not metadata.functions:
        raise HTTPException(status_code=400, detail="No functions found in project")
    
    # 运行模糊测试引擎
    engine = FuzzEngine()
    result = await engine.run(metadata, max_iterations=request.max_iterations)
    
    return {
        "success": result.success,
        "summary": result.summary,
        "metadata": result.metadata,
        "harness_count": len(result.harnesses),
        "errors": [e.model_dump() for h in result.harnesses for e in h.errors]
    }

@router.post("/analyze/code")
async def analyze_code(request: CodeAnalyzeRequest) -> dict:
    """分析单个代码片段"""
    parser = ASTParser()
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix=f".{request.language}",
        delete=False
    ) as f:
        f.write(request.code)
        temp_path = Path(f.name)
    
    try:
        # 解析AST
        ast_result = parser.parse_file(temp_path)
        
        # 提取函数
        functions = parser.extract_functions(temp_path)
        
        return {
            "success": ast_result.get("success", False),
            "functions": [f.model_dump() for f in functions],
            "errors": ast_result.get("errors", ""),
            "ast_preview": ast_result.get("ast_dump", "")[:2000]
        }
    finally:
        temp_path.unlink(missing_ok=True)

@router.post("/analyze/upload")
async def analyze_uploaded_file(file: UploadFile = File(...)) -> dict:
    """分析上传的文件"""
    # 保存上传的文件
    temp_dir = Path(tempfile.mkdtemp())
    file_path = temp_dir / file.filename
    
    try:
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        parser = ASTParser()
        ast_result = parser.parse_file(file_path)
        functions = parser.extract_functions(file_path)
        
        return {
            "filename": file.filename,
            "success": ast_result.get("success", False),
            "functions": [f.model_dump() for f in functions],
            "function_count": len(functions)
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/generate/harness")
async def generate_harness(request: CodeAnalyzeRequest) -> dict:
    """为代码生成模糊测试驱动程序"""
    from ..agents import GenerationAgent
    from ..models.code_metadata import CodeMetadata
    
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="代码不能为空")
    
    parser = ASTParser()
    
    # 创建临时文件并解析
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix=f".{request.language}",
        delete=False
    ) as f:
        f.write(request.code)
        temp_path = Path(f.name)
    
    try:
        functions = parser.extract_functions(temp_path)
        
        if not functions:
            raise HTTPException(status_code=400, detail="未找到可分析的函数，请检查代码格式")
        
        metadata = CodeMetadata(
            project_name="uploaded_code",
            language=request.language,
            functions=functions
        )
        
        agent = GenerationAgent()
        
        try:
            harness = await agent.execute(metadata, functions[:5])
        except Exception as e:
            error_msg = str(e)
            if "余额不足" in error_msg:
                raise HTTPException(status_code=402, detail="API账户余额不足，请充值后重试")
            elif "密钥无效" in error_msg:
                raise HTTPException(status_code=401, detail="API密钥无效，请检查.env配置")
            else:
                raise HTTPException(status_code=500, detail=f"AI生成失败: {error_msg}")
        
        return {
            "success": True,
            "harness_code": harness.harness_code,
            "target_functions": harness.target_functions
        }
    finally:
        temp_path.unlink(missing_ok=True)
