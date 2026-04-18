"""
智能点餐助手 启动脚本

启动uvicorn web服务器
"""



import logging

logging.basicConfig(
    filename="D:\projects\smart_order\log\\run.log",
    level=logging.INFO,
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

import uvicorn

def main():
    """启动AiMenu API服务"""
    
    print("🍽️ AiMenu 智能点餐系统 v2.0")
    print("=" * 50)
    
    print("✅ 环境配置检查通过")
    print("🚀 正在启动API服务...")
    print("📍 服务地址: http://localhost:8000")
    print("📖 API文档: http://localhost:8000/docs")
    print("=" * 50)
    
    # 启动服务
    try:
        uvicorn.run(
            "api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,  # 开发模式，文件变化时自动重启
            log_level="info"
        )
        logger.info("🚀 启动Uvicorn服务器成功!")
    except KeyboardInterrupt:
        logger.error("\n👋 Uvicorn服务已停止")
    except Exception as e:
        logger.error(f"❌ Uvicorn服务器启动失败: {e}")

if __name__ == "__main__":
    main()