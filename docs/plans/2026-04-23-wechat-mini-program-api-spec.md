# 微信小程序 API Python First 实现 Spec

**状态**: Draft for review

**目标**: 基于现有 [swagger.yaml](/Users/linjinzhu/code/weixin/xinge-backend/swagger.yaml) 实现微信小程序后台 API，第一版使用 Python，完整覆盖 `/mp/*` 接口、支付回调、报告生成编排、分销链路和测试体系；后续如需迁移到 Go，应尽量只替换传输层和基础设施适配层，不重写业务规则。

## 1. 本轮范围

本轮只实现小程序相关接口，共 27 个：

- `/mp/auth/bind-phone`
- `/mp/auth/login`
- `/mp/config/product`
- `/mp/distributor/application/status`
- `/mp/distributor/apply`
- `/mp/distributor/commissions`
- `/mp/distributor/downlines`
- `/mp/distributor/join`
- `/mp/distributor/me`
- `/mp/distributor/quota/allocate`
- `/mp/distributor/team`
- `/mp/distributor/withdraw`
- `/mp/distributor/withdrawals`
- `/mp/messages/list`
- `/mp/messages/read`
- `/mp/orders`
- `/mp/orders/detail`
- `/mp/orders/notify/wechat`
- `/mp/reports`
- `/mp/reports/detail`
- `/mp/reports/links`
- `/mp/reports/list`
- `/mp/reports/status`
- `/mp/schools/detail`
- `/mp/schools/list`
- `/mp/users/me`
- `/mp/users/me/update`

本轮不实现：

- `/admin/*`
- `/orders/*`
- `/reports/*`
- `/tasks/*`

但数据模型与状态流会兼容这些后续接口，避免未来返工。

## 2. 总体方案

### 2.1 推荐架构

采用 Python 单仓双进程架构：

- `api` 服务：负责 HTTP API、参数校验、鉴权、响应封装、支付回调入口
- `worker` 服务：负责报告生成、佣金结算、消息派发等异步任务

基础设施：

- `FastAPI`：HTTP API 与 Swagger 友好，便于快速开发和契约校验
- `Pydantic v2`：请求响应模型、字段校验、类型约束
- `SQLAlchemy 2.x`：ORM 与事务管理
- `Alembic`：数据库迁移
- `MySQL`：主数据存储
- `Redis`：幂等、短期缓存、分布式锁、任务队列状态
- `Celery` 或 `RQ`：异步任务执行
- `COS`：H5/PDF/图片文件存储与预签名链接
- `pytest`：单元、集成、契约测试

### 2.2 为什么 Python First

采用 Python 的原因：

- 你熟悉 Python，第一版更利于快速迭代和定位问题
- FastAPI + Pydantic 很适合先把 Swagger 契约快速落地
- 测试、Mock 外部依赖、支付回调模拟、异步编排都更省成本

### 2.3 为未来迁移 Go 预留的边界

虽然第一版用 Python，但业务层按“可迁移”方式组织：

- `handler/api schema` 和 `service/use case` 分离
- 微信登录、微信支付、COS、队列都通过 adapter interface 封装
- 业务规则只写在 `service` 层，不散落在路由和 ORM model 中
- 响应 envelope、错误码、状态机、数据表结构尽量稳定

这样后续迁移到 Go 时，优先重写：

- HTTP layer
- repository layer
- infra adapters

尽量不重写：

- 业务规则
- 状态迁移
- 错误码定义
- 接口契约

## 3. 目录规划

建议目录如下：

```text
xinge-backend/
  app/
    api/
      routes/
      deps.py
      middleware.py
      schemas/
    services/
    repositories/
    domain/
    integrations/
      wechat_auth.py
      wechat_pay.py
      cos.py
    tasks/
    core/
      config.py
      logging.py
      security.py
      errors.py
      response.py
    db/
      models/
      session.py
  migrations/
  tests/
    unit/
    integration/
    contract/
    fixtures/
  scripts/
  docs/plans/
```

职责约束：

- `api/routes` 只负责收参与调 service
- `api/schemas` 负责请求响应模型
- `services` 负责业务规则和事务边界
- `repositories` 负责数据库读写
- `integrations` 负责第三方 SDK/HTTP 调用
- `tasks` 负责 worker 中异步任务入口

## 4. 认证与请求约束

### 4.1 保持 Swagger 兼容

所有私有 `/mp/*` 接口继续要求以下 Header：

- `X-Login-Code`
- `X-System-Version`
- `X-Device-UUID`

公开接口不要求登录：

- `/mp/config/product`
- `/mp/schools/list`
- `/mp/schools/detail`

### 4.2 认证实现

私有接口通过 middleware 或 dependency 完成以下流程：

1. 读取 `X-Login-Code`
2. 调用微信 `code2session`
3. 获取 `openid`，必要时获取 `unionid`
4. 按 `openid` 查找或创建用户
5. 记录设备信息、系统版本、最近登录时间
6. 将当前用户上下文注入 request state

### 4.3 风险和说明

这是严格遵循 Swagger 的实现方式，但它有一个现实代价：

- 小程序每次私有请求前都需要先执行 `wx.login()`

第一版 spec 默认不改这个契约，以保证与 Swagger 一致；如果后续想优化，我建议二期增加服务端 session token，再让小程序只在 token 失效时重新 `wx.login()`。

## 5. 领域模型

### 5.1 用户域

`mp_users`

- `id`
- `openid`
- `unionid`
- `nickname`
- `avatar_url`
- `phone_ciphertext`
- `phone_masked`
- `role`
- `is_distributor`
- `created_at`
- `updated_at`

`mp_user_devices`

- `id`
- `user_id`
- `device_uuid`
- `system_version`
- `last_login_at`
- `last_login_ip`

### 5.2 报告域

`reports`

- `id`
- `user_id`
- `name`
- `report_type`
- `status`
- `fail_stage`
- `progress_json`
- `created_at`
- `updated_at`

`report_profiles`

- `report_id`
- 表单字段，基本对应 `MPCreateReportReq`

`report_assets`

- `report_id`
- `preview_h5_key`
- `full_h5_key`
- `pdf_key`
- `generated_at`

说明：

- 小程序 `report_id` 与内部报告主键统一使用同一 ID
- 这样支付、状态轮询、结果链接和后续内部报告接口可以共用一套主键与状态机

### 5.3 订单与支付域

`orders`

- `id`
- `order_id`
- `user_id`
- `report_id`
- `amount`
- `status`
- `channel`
- `prepay_id`
- `paid_at`
- `created_at`
- `updated_at`

`payment_callbacks`

- `id`
- `order_id`
- `provider`
- `notify_id`
- `payload_raw`
- `verify_status`
- `processed_at`

### 5.4 分销域

`distributors`

- `user_id`
- `distributor_level`
- `parent_distributor_id`
- `quota_total`
- `quota_allocated`
- `quota_used`
- `quota_remaining`

`distributor_applications`

- `application_id`
- `user_id`
- `target_level`
- `real_name`
- `phone`
- `reason`
- `status`
- `reject_reason`

`quota_ledgers`

- `id`
- `from_user_id`
- `to_user_id`
- `amount`
- `created_at`

`commissions`

- `commission_id`
- `beneficiary_user_id`
- `order_id`
- `amount`
- `rate`
- `status`

`withdrawals`

- `withdraw_id`
- `user_id`
- `amount`
- `bank_name`
- `bank_account_ciphertext`
- `bank_account_masked`
- `status`

### 5.5 消息域

`messages`

- `id`
- `user_id`
- `type`
- `title`
- `content`
- `is_read`
- `created_at`

### 5.6 学校域

`schools`

- `id`
- `name`
- `city`
- `city_level`
- `is_985`
- `is_211`
- `is_double_first_class`
- `school_level_tag`
- `school_score`

`colleges`

- `id`
- `school_id`
- `name`
- `college_score`

`majors`

- `id`
- `college_id`
- `name`
- `major_type`
- `major_score`

## 6. 接口分组与实现要点

### 6.1 `mp/auth`

`/mp/auth/login`

- 通过 `X-Login-Code` 调微信登录
- 按 `openid` 查找或新建用户
- 可接收 `distributor_id` 作为后续绑定上下文
- 返回 `is_new_user`、`has_phone`、`role`、`user_info`

`/mp/auth/bind-phone`

- 使用微信手机号能力解密手机号
- 原始手机号 AES-256-GCM 加密入库
- 返回脱敏手机号

### 6.2 `mp/users`

`/mp/users/me`

- 返回当前用户基础信息、报告数量、未读消息数、分销状态

`/mp/users/me/update`

- 更新昵称、头像

### 6.3 `mp/schools`

`/mp/schools/list`

- 支持关键词、城市、985/211 条件检索
- 分页返回学校基础信息

`/mp/schools/detail`

- 按学校名称返回学校、学院、专业完整嵌套结构

### 6.4 `mp/reports`

`/mp/reports`

- 创建报告草稿
- 初始状态为 `draft`

`/mp/reports/list`

- 返回当前用户报告列表
- 按创建时间倒序
- 补充关联订单信息

`/mp/reports/detail`

- 返回完整表单回显数据、状态、订单摘要

建议返回结构：

```json
{
  "report_id": 101,
  "status": "draft",
  "report_type": "preview",
  "is_paid": false,
  "order_id": "ORDxxx",
  "order_status": "pending",
  "form": {},
  "created_at": "2026-04-20T10:00:00Z",
  "updated_at": "2026-04-20T10:00:00Z"
}
```

`/mp/reports/status`

- 返回状态与进度条信息
- 前端 3 到 5 秒轮询

`/mp/reports/links`

- 返回预览 H5、完整 H5、PDF 的预签名链接
- 未支付时 `full_h5_url` 与 `pdf_url` 返回 `null`

### 6.5 `mp/orders`

`/mp/orders`

- 校验报告归属
- 校验价格配置与传入金额一致
- 防止重复创建未支付订单
- 创建统一下单，返回 `payment_params`

`/mp/orders/detail`

- 查询订单最终状态
- 用于弥补 `wx.requestPayment()` 前端回调不稳定

`/mp/orders/notify/wechat`

- 仅微信服务器调用
- 验签
- AES-GCM 解密
- 校验订单号、金额、支付状态
- 幂等更新订单为 `paid`
- 触发报告生成任务
- 触发佣金计算任务

### 6.6 `mp/messages`

`/mp/messages/list`

- 支持按已读状态筛选
- 分页返回消息列表

`/mp/messages/read`

- 仅允许标记当前用户自己的消息

### 6.7 `mp/distributor`

`/mp/distributor/join`

- 用户扫码绑定上级分销商
- 无需审核
- 防止重复加入

`/mp/distributor/apply`

- 普通用户主动申请成为分销商
- 创建待审核申请
- 审核结果通过消息通知

`/mp/distributor/application/status`

- 返回当前用户最新申请状态

`/mp/distributor/me`

- 返回配额、团队统计、佣金汇总、报告统计

`/mp/distributor/downlines`

- 返回直接下级列表

`/mp/distributor/team`

- Swagger 当前未展开返回结构，建议实现为按层级分组：

```json
{
  "summary": {
    "campus_count": 0,
    "city_count": 0,
    "user_count": 0
  },
  "strategic_list": [],
  "city_list": [],
  "campus_list": [],
  "page": 1,
  "page_size": 20
}
```

`/mp/distributor/quota/allocate`

- 上级只能给直接下级分配
- `campus` 级无权分配
- 通过事务和分布式锁避免超分配

`/mp/distributor/commissions`

- 按订单维度返回佣金明细

`/mp/distributor/withdraw`

- 校验可提现金额
- 银行账号密文保存，只返回脱敏值

`/mp/distributor/withdrawals`

- 返回提现历史

### 6.8 `mp/config`

`/mp/config/product`

- 返回当前价格、原价、折扣、限时优惠结束时间、展示用统计
- 价格来源建议走独立配置表，不硬编码

## 7. 状态机

### 7.1 报告状态

```text
draft -> unpaid -> paid -> collecting -> planning -> generating -> analyzing -> completed
draft -> unpaid -> paid -> ... -> failed
```

约束：

- 创建报告后为 `draft`
- 创建待支付订单后更新为 `unpaid`
- 支付成功后更新为 `paid`
- worker 按阶段推进
- 任一阶段失败时写入 `fail_stage` 并终止

### 7.2 订单状态

```text
pending -> paid
pending -> failed
```

### 7.3 申请状态

```text
pending -> approved
pending -> rejected
```

### 7.4 提现状态

```text
pending -> processing -> completed
pending -> rejected
```

## 8. 异步任务设计

建议任务类型：

- `report_generate`
- `commission_calculate`
- `message_dispatch`

任务要求：

- 所有任务必须具备幂等性
- 所有外部调用失败都可重试
- 任务状态与重试次数可观测
- 支付回调重复通知不得重复生成报告或重复结算佣金

## 9. 错误处理与响应规范

小程序接口统一使用 Swagger 中的 envelope：

成功：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "timestamp": 1713600000,
  "user_info": {
    "user_id": 42,
    "open_id": "oXXXXXXXXX"
  }
}
```

公开接口不返回 `user_info`。

错误：

```json
{
  "code": 1001,
  "message": "invalid request",
  "timestamp": 1713600000
}
```

要求：

- 业务错误码集中维护在 `app/core/errors.py`
- 统一异常处理器映射为 Swagger 风格响应
- 所有接口返回 JSON，不抛裸异常

## 10. 安全与合规

- 手机号、银行卡号必须密文存储
- 日志中禁止打印原始手机号、银行卡号、支付敏感字段
- 微信支付回调原文单独存档，但敏感字段要控制输出级别
- 所有修改型接口记录审计日志
- 支付回调、配额分配、提现申请必须有幂等保护

## 11. 测试策略

### 11.1 单元测试

覆盖：

- schema 校验
- 金额校验
- 手机号脱敏
- 订单状态转换
- 报告状态转换
- 配额扣减与防超发
- 佣金计算
- 提现额度校验
- 权限判断

### 11.2 集成测试

覆盖关键链路：

- `login -> bind phone -> me`
- `create report -> list -> detail`
- `create order -> query detail`
- `wechat notify -> order paid -> report status progressing`
- `report completed -> links available`
- `join distributor -> distributor me -> downlines`
- `apply distributor -> status -> message notice`
- `allocate quota -> commissions -> withdraw -> withdrawals`

### 11.3 契约测试

目标：

- 逐个校验 27 个 `/mp/*` 接口与 `swagger.yaml` 的字段结构一致
- 校验必需 header、状态码、响应 envelope、字段命名

说明：

- `/mp/reports/detail` 与 `/mp/distributor/team` 因 Swagger 未完全展开，需要在实现时同步补充文档并在契约测试中按最终确认版校验

### 11.4 第三方依赖 Mock

必须 mock：

- 微信 `code2session`
- 微信手机号解密能力
- 微信支付验签与解密
- COS 预签名

避免测试依赖真实微信与真实云资源。

## 12. 微信云托管部署方案

部署两个服务：

- `api`
- `worker`

环境变量：

- `APP_ENV`
- `APP_SECRET_KEY`
- `MYSQL_DSN`
- `REDIS_URL`
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`
- `WECHAT_MCH_ID`
- `WECHAT_PAY_API_V3_KEY`
- `WECHAT_PAY_SERIAL_NO`
- `WECHAT_PAY_PRIVATE_KEY`
- `WECHAT_PAY_PLATFORM_CERT`
- `COS_SECRET_ID`
- `COS_SECRET_KEY`
- `COS_BUCKET`
- `COS_REGION`

运维要求：

- `api` 提供 `/healthz` 与 `/readyz`
- `worker` 提供基础存活探针
- 日志带 `request_id`、`user_id`、`report_id`、`order_id`
- 支付回调日志单独分类

## 13. 第一版实现顺序

推荐顺序：

1. 项目骨架、配置、数据库会话、错误处理、统一响应
2. 用户登录与绑手机
3. 学校公开接口
4. 报告创建、列表、详情
5. 订单创建、订单详情、支付回调
6. 报告异步状态与结果链接
7. 消息中心
8. 分销加入、申请、详情、下线
9. 配额、佣金、提现
10. 完整契约测试与集成测试

## 14. 已确认和待确认

### 已按你的反馈更新

- 第一版改为 Python 实现
- 目标是先把功能和测试跑通，再考虑 Go 迁移
- spec 需要落盘，方便后续按文档推进

### 仍建议你确认

1. 是否接受第一版严格沿用 Swagger 认证方式，也就是私有接口每次都带 `X-Login-Code`
2. `/mp/reports/detail` 的建议返回结构是否 OK
3. `/mp/distributor/team` 的建议返回结构是否 OK
4. 是否接受 `report_id` 与内部报告主键统一

## 15. 下一步

你确认这份 spec 后，我会继续输出实现 plan，内容会细到：

- 具体要创建/修改哪些 Python 文件
- 每个阶段先写哪些 failing tests
- 如何拆出可运行的第一批接口
- 本地和云托管分别如何验证
