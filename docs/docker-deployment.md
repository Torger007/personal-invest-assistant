# Docker 部署

本项目使用 Docker Compose 运行四项服务：PostgreSQL、一次性数据库迁移、FastAPI 后端和 Nginx 前端。只有前端的 HTTP 端口会暴露给宿主机；数据库与后端 API 均不直接暴露。

## 首次部署

1. 在项目根目录复制环境变量模板：

   ```powershell
   Copy-Item .env.production.example .env.production
   ```

2. 编辑 `.env.production`，至少设置 PostgreSQL 密码、与之匹配且 URL 编码后的 `DATABASE_URL`、初始管理员账号密码，以及实际使用的 LLM API Key。

3. 启动：

   ```powershell
   docker compose --env-file .env.production up -d --build
   docker compose --env-file .env.production ps
   ```

4. 浏览器打开 `http://localhost:8080`。启动完成后，`migrate` 显示为已成功退出（exit code 0），其余三个服务为运行状态。

## HTTPS 与 Cookie

生产环境应使用 Caddy、Traefik、Nginx 或云负载均衡在应用前终止 HTTPS，并将流量转发到 `APP_PORT`。在这种情况下保留 `SESSION_SECURE=true`。仅在本机通过 `http://localhost:8080` 测试登录时，才临时将其改为 `false`。

## 日常维护

```powershell
# 查看日志
docker compose --env-file .env.production logs -f backend

# 更新镜像和代码后重建
docker compose --env-file .env.production up -d --build

# 停止服务（不会删除数据库卷）
docker compose --env-file .env.production down
```

不要执行 `docker compose down -v`，除非确认需要删除所有 PostgreSQL 数据。数据定时任务运行在后端进程中，因此 `backend` 保持单副本、单个 Uvicorn worker；扩容 API 前应先把调度器拆分为独立 worker。
