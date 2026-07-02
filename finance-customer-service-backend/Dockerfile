FROM python:3.12-slim

WORKDIR /app

# pip 使用国内镜像安装 uv
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com uv

# uv 使用国内镜像安装依赖
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY . .

EXPOSE 7000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7000"]
