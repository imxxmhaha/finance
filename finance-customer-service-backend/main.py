"""
智能金融客服系统 - 主入口文件
"""
import os
import uvicorn
from dotenv import load_dotenv

# 切换到项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from atguigu.api.app import create_app
from atguigu.conf.config import settings

app = create_app()


def main():
    uvicorn.run(
        "main:app",
        host=settings.app_host or "0.0.0.0",
        port=settings.app_port or 18000,
        reload=True,
    )


if __name__ == '__main__':
    main()
