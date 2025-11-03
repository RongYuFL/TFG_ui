# 使用 Python 官方镜像
FROM python:3.8-slim

# 环境变量：不生成 pyc，输出不缓冲
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 先复制依赖文件以利用缓存
COPY requirements.txt .

# 安装依赖并确保 gunicorn 可用（用于生产）
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 复制项目文件
COPY . .

# 如果 Flask 使用默认端口，暴露 5000（可按需修改）
EXPOSE 5000

# 用 gunicorn 启动（假设入口是 app.py 且实例名为 app）
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "4", "--timeout", "120"]

# 构建镜像并打标签 docker build -t genefaceplusplus:latest .
# 运行容器并映射端口 5000 docker run --rm -p 5000:5000 genefaceplusplus:latest