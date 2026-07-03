import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from atguigu.conf.config import settings
from atguigu.api.lifespan import lifespan
from atguigu.api.middleware import RequestContextMiddleware
from atguigu.api.routers.chat_router import chat_router
from atguigu.api.routers.auth_router import router as auth_router
from atguigu.api.routers.knowledge_router import router as knowledge_router


def create_app() -> FastAPI:
    """
    负责创建fastapi实例  test
    """
    # 1. 实例化FastAPI实例，注册生命周期管理器
    app = FastAPI(
        description="智能金融客服",
        lifespan=lifespan
    )

    # 2. 注册日志请求上下文中间件
    app.add_middleware(RequestContextMiddleware)

    # 3. 跨域配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. 注册路由
    app.include_router(chat_router)
    app.include_router(auth_router)
    app.include_router(knowledge_router)

    # 4. 注册测试路由
    @app.get("/db-test")
    async def db_test():
        """测试数据库连接"""
        from sqlalchemy import text
        from atguigu.infrastructure.database import get_db_session
        try:
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1"))
                return {"status": "ok", "result": result.scalar()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # 返回实例
    return app


if __name__ == '__main__':
    """
    启动web服务器 (fastapi实例)
    """
    import os
    from dotenv import load_dotenv

    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    load_dotenv()

    uvicorn.run(
        "atguigu.api.app:create_app",
        factory=True,
        host=settings.app_host or "0.0.0.0",
        port=settings.app_port or 18000,
        reload=True,  # 热部署：代码修改后自动重启
    )
