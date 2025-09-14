FROM nginx:alpine

# 直接使用预构建的前端产物（在 Release 工作流中先执行 npm ci && npm run build 生成 frontend/dist）
# 构建镜像时，工作目录即为 frontend/，因此直接复制 dist 即可。
COPY dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
