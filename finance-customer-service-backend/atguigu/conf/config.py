from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """从当前文件向上查找项目根目录"""
    current = Path(__file__).resolve().parent
    for parent in current.parents:
        if (parent / '.env').exists():
            return parent
    return current.parents[1]


ENV_FILE = find_project_root() / '.env'


class Settings(BaseSettings):
    # LLM
    llm_api_key: str
    llm_model: str
    llm_base_url: str

    # 数据库
    database_url: str

    # 金融 API
    finance_api_base_url: str

    # 中台 API 请求头
    api_channel_code: str = "OPEN_API"
    api_operator_no: str = "EMP000006"

    # 服务器
    app_host: str
    app_port: int

    # 阿里百炼 Embedding
    dashscope_api_key: str = ""

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    model_config = SettingsConfigDict(env_file=ENV_FILE)


settings = Settings()

if __name__ == '__main__':
    print(settings.llm_base_url)
