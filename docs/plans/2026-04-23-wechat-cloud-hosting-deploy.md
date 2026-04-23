# 微信云托管部署记录

## 当前状态

仓库已补齐以下部署文件：

- `Dockerfile`
- `.dockerignore`
- `container.config.json`

运行时特性：

- 容器启动命令使用 `uvicorn app.main:app`
- 监听 `PORT` 环境变量，默认 `80`
- 启动时自动建表
- 如果没有价格配置，会自动写入一条默认产品配置

## 当前限制

- 机器上还没有 `node/npm`
- 机器上还没有 `tcb` 或 `wxcloud`
- 当前无法直接完成 CLI 登录与发版
- 当前默认数据库是 `sqlite`，只适合临时 smoke deployment，不适合正式生产

## 下一步可选路径

### 路径 A：CLI 直接发版

前提：

- 安装 Node.js
- 安装 `@cloudbase/cli` 或 `@wxcloud/cli`
- 拿到云托管环境信息并完成登录

### 路径 B：控制台手动发版

在微信云托管控制台中：

1. 新建服务
2. 选择代码构建或源码上传
3. 指向仓库根目录中的 `Dockerfile`
4. 使用 `container.config.json` 中的资源参数
5. 配置必要环境变量
6. 发布新版本

## 推荐

如果要我继续“直接发版”，请提供以下最少信息之一：

- 目标 `envId` 与 `serviceName`，并允许我安装 CLI 后完成登录
- 或者直接提供 `appId`、`privateKey`、`envId`、`serviceName`

这样我就可以继续把部署真正发出去。
