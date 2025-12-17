"""
智能代码分析与模糊测试驱动生成系统
主入口文件
"""
import argparse
import asyncio
from pathlib import Path

from src.config import config
from src.analyzers import MetadataExtractor, ASTParser
from src.fuzzer import FuzzEngine
from src.agents import GenerationAgent

def run_server():
    """启动Web服务"""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from src.api import router
    
    app = FastAPI(
        title="智能代码分析系统",
        description="基于LLM智能体的代码分析与模糊测试驱动生成",
        version="0.1.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router, prefix="/api")
    
    # 提供前端静态文件
    @app.get("/")
    async def serve_frontend():
        return FileResponse("web/index.html")
    
    print(f"启动服务: http://{config.host}:{config.port}")
    print(f"API文档: http://{config.host}:{config.port}/docs")
    
    uvicorn.run(app, host=config.host, port=config.port)

async def analyze_project(project_path: str, max_iterations: int = 100):
    """分析项目"""
    path = Path(project_path)
    if not path.exists():
        print(f"错误: 路径不存在 - {project_path}")
        return
    
    print(f"分析项目: {path}")
    
    # 提取元数据
    extractor = MetadataExtractor()
    metadata = extractor.extract_from_project(path)
    
    print(f"发现 {len(metadata.functions)} 个函数")
    print(f"源文件: {len(metadata.source_files)} 个")
    
    if not metadata.functions:
        print("未找到可分析的函数")
        return
    
    # 显示函数列表
    print("\n函数列表:")
    for func in metadata.functions[:20]:
        params = ", ".join([f"{p.type} {p.name}" for p in func.params])
        print(f"  - {func.return_type} {func.name}({params})")
    
    if len(metadata.functions) > 20:
        print(f"  ... 还有 {len(metadata.functions) - 20} 个函数")
    
    # 运行模糊测试引擎
    print("\n开始生成模糊测试驱动程序...")
    engine = FuzzEngine()
    result = await engine.run(metadata, max_iterations=max_iterations)
    
    print(f"\n=== 分析完成 ===")
    print(f"结果: {result.summary}")
    print(f"成功的驱动程序保存在: {config.harness_dir}")

async def analyze_file(file_path: str):
    """分析单个文件"""
    path = Path(file_path)
    if not path.exists():
        print(f"错误: 文件不存在 - {file_path}")
        return
    
    parser = ASTParser()
    
    print(f"分析文件: {path}")
    
    # 解析AST
    result = parser.parse_file(path)
    if "error" in result:
        print(f"解析错误: {result['error']}")
        return
    
    # 提取函数
    functions = parser.extract_functions(path)
    
    print(f"\n发现 {len(functions)} 个函数:")
    for func in functions:
        params = ", ".join([f"{p.type} {p.name}" for p in func.params])
        print(f"  [{func.line_number}] {func.return_type} {func.name}({params})")

async def generate_harness(file_path: str):
    """为文件生成模糊测试驱动"""
    path = Path(file_path)
    if not path.exists():
        print(f"错误: 文件不存在 - {file_path}")
        return
    
    parser = ASTParser()
    functions = parser.extract_functions(path)
    
    if not functions:
        print("未找到可测试的函数")
        return
    
    from src.models.code_metadata import CodeMetadata
    
    metadata = CodeMetadata(
        project_name=path.stem,
        language="cpp" if path.suffix in [".cpp", ".hpp", ".cc"] else "c",
        functions=functions
    )
    
    print(f"为 {len(functions)} 个函数生成驱动程序...")
    
    agent = GenerationAgent()
    harness = await agent.execute(metadata, functions[:5])
    
    print("\n生成的驱动程序:")
    print("-" * 50)
    print(harness.harness_code)
    print("-" * 50)
    
    # 保存到文件
    output_file = config.harness_dir / f"harness_{path.stem}.c"
    with open(output_file, 'w') as f:
        f.write(harness.harness_code)
    print(f"\n已保存到: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="智能代码分析与模糊测试驱动生成系统"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # server命令
    server_parser = subparsers.add_parser("server", help="启动Web服务")
    
    # analyze命令
    analyze_parser = subparsers.add_parser("analyze", help="分析项目或文件")
    analyze_parser.add_argument("path", help="项目目录或文件路径")
    analyze_parser.add_argument(
        "--iterations", "-i", 
        type=int, 
        default=100,
        help="最大迭代次数"
    )
    
    # generate命令
    gen_parser = subparsers.add_parser("generate", help="生成模糊测试驱动")
    gen_parser.add_argument("file", help="源代码文件")
    
    args = parser.parse_args()
    
    if args.command == "server":
        run_server()
    elif args.command == "analyze":
        path = Path(args.path)
        if path.is_file():
            asyncio.run(analyze_file(args.path))
        else:
            asyncio.run(analyze_project(args.path, args.iterations))
    elif args.command == "generate":
        asyncio.run(generate_harness(args.file))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
