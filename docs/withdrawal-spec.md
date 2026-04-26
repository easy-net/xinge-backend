# 分销商提现功能 Spec

## 1. 概述

本文档描述小程序分销商提现功能的完整流程，包括用户端和管理端的所有接口和交互逻辑。

## 2. 业务流程

### 2.1 三方交互架构

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   微信小程序  │ ←──→ │   后端服务   │ ←──→ │  微信支付后台  │ ←──→ │   用户微信   │
│  (前端页面)   │      │  (你的服务器) │      │  (微信服务器)  │      │  (零钱到账)   │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘      └─────────────┘
       │                    │                    │
       │  1. 申请提现        │                    │
       │ ─────────────────> │                    │
       │                    │  2. 创建提现单      │
       │                    │  3. 调用微信转账    │
       │                    │ ─────────────────> │
       │                    │                    │
       │                    │  4. 返回转账结果    │
       │                    │ <───────────────── │
       │                    │                    │
       │  5. 返回提现结果    │                    │
       │ <───────────────── │                    │
       │                    │                    │  6. 零钱到账通知
       │                    │                    │ ─────────────────>
       │                    │                    │
       │                    │  7. 异步回调(可选)  │
       │                    │ <───────────────── │
```

### 2.2 详细时序图

#### 场景：小额自动提现成功（< 100元）

```
小程序          后端服务           微信支付           用户微信
  │               │                 │                │
  │ ─────────────>│                 │                │
  │  POST /withdraw                │                │
  │  {amount: 5000}                │                │
  │               │                 │                │
  │               │ 1. 校验权限      │                │
  │               │ 2. 校验余额      │                │
  │               │ 3. 扣除余额      │                │
  │               │ 4. 创建提现单    │                │
  │               │    status=processing             │
  │               │                 │                │
  │               │ ───────────────>│                │
  │               │  POST /v3/fund-app/mch-transfer/transfer-bills
  │               │  {out_bill_no, openid, amount}  │
  │               │                 │                │
  │               │ <───────────────│                │
  │               │  Response       │                │
  │               │  {state: SUCCESS│                │
  │               │   transfer_bill_no}              │
  │               │                 │                │
  │               │ 5. 更新状态      │                │
  │               │    status=paid   │                │
  │               │ 6. 更新累计提现  │                │
  │               │ 7. 提交事务      │                │
  │               │                 │                │
  │ <─────────────│                 │                │
  │  Response     │                 │                │
  │  {status: paid}                │                │
  │               │                 │                │
  │ 显示"提现成功" │                 │                │
  │               │                 │ ─────────────> │
  │               │                 │  零钱到账通知   │
  │               │                 │  "¥50.00已到账"│
  │               │                 │                │
```

#### 场景：大额人工审核（≥ 100元）

```
小程序          后端服务           微信支付           用户微信      管理员
  │               │                 │                │            │
  │ ─────────────>│                 │                │            │
  │  POST /withdraw                │                │            │
  │  {amount: 20000}               │                │            │
  │               │                 │                │            │
  │               │ 1. 扣除余额      │                │            │
  │               │ 2. 创建提现单    │                │            │
  │               │    status=pending_review         │            │
  │               │    （不调用微信支付）             │            │
  │               │                 │                │            │
  │ <─────────────│                 │                │            │
  │  Response     │                 │                │            │
  │  {status: pending_review}      │                │            │
  │               │                 │                │            │
  │ 显示"待审核"   │                 │                │            │
  │               │                 │                │            │
  │               │                 │                │            │
  │               │ <────────────────────────────────────────────│
  │               │  POST /admin/withdrawals/{id}/approve        │
  │               │                 │                │            │
  │               │ ───────────────>│                │            │
  │               │  调用微信转账    │                │            │
  │               │ <───────────────│                │            │
  │               │  {state: SUCCESS}                │            │
  │               │                 │                │            │
  │               │ 更新 status=paid │                │            │
  │               │                 │ ─────────────> │
  │               │                 │  零钱到账通知   │
  │               │                 │                │
```

#### 场景：自动转账失败，转人工处理

```
小程序          后端服务           微信支付
  │               │                 │
  │ ─────────────>│                 │
  │  POST /withdraw                │
  │  {amount: 5000}                │
  │               │                 │
  │               │ 1. 扣除余额      │
  │               │ 2. 创建提现单    │
  │               │    status=processing             │
  │               │                 │
  │               │ ───────────────>│
  │               │  调用微信转账    │
  │               │                 │
  │               │ <───────────────│
  │               │  网络超时/返回错误                │
  │               │                 │
  │               │ 3. 捕获异常      │
  │               │ 4. 改状态为      │
  │               │    pending_review │
  │               │    （金额已扣，需人工处理）        │
  │               │ 5. 提交事务      │
  │               │                 │
  │ <─────────────│                 │
  │  Response     │                 │
  │  {status: pending_review}      │
  │               │                 │
  │ 显示"已提交审核" │                │
  │               │                 │
  │               │ <───────────────────────────────
  │               │  管理员审核通过，重新发起转账
  │               │  调用微信转账成功
  │               │  更新 status=paid
```

### 2.2 提现状态流转

```
┌─────────┐
│  created │ ← 提现单创建，金额已扣除
│  待处理   │
└────┬────┘
     │
     ├─────────────────────────────────────┐
     │                                     │
     ▼                                     ▼
┌─────────┐                         ┌─────────┐
│pending_ │ 自动审核通过              │pending_ │ 需要人工审核
│review   │ （小额、低风险）           │audit    │ （大额、异常）
│待审核    │                         │待人工审核│
└────┬────┘                         └────┬────┘
     │                                   │
     │ 审核通过                          │ 审核通过
     ▼                                   ▼
┌─────────┐                         ┌─────────┐
│processing│                        │processing│
│处理中    │                        │处理中    │
│调用支付渠道│                        │调用支付渠道│
└────┬────┘                         └────┬────┘
     │                                   │
     ├────────────┬────────────┐        │
     ▼            ▼            ▼        ▼
┌────────┐  ┌────────┐  ┌────────┐ ┌────────┐
│success │  │failed  │  │pending │ │rejected│
│成功到账 │  │失败退回 │  │异步处理 │ │审核拒绝 │
└────────┘  └────────┘  └────┬───┘ └────────┘
                             │
                        异步回调
                             │
                        ┌────┴────┐
                        ▼         ▼
                   ┌────────┐ ┌────────┐
                   │success │ │failed  │
                   │成功到账 │ │失败退回 │
                   └────────┘ └────────┘
```

**状态说明：**
- `created`: 已创建，金额已扣除（冻结）
- `pending_review`: 待审核（超过自动转账阈值或自动转账失败）
- `processing`: 处理中（已调用微信支付转账接口，等待结果或回调）
- `paid`: 已到账（微信支付转账成功）
- `rejected`: 已拒绝（管理员拒绝，金额退回用户余额）
- `failed`: 失败（转账失败，金额已退回用户余额）

### 2.2 自动转账规则

- 设置阈值 `distributor_withdraw_auto_approve_fen`（默认 10000 分 = 100元）
- 提现金额 **小于** 阈值：自动调用微信支付转账
  - 同步成功：状态直接变为 `paid`，用户立即到账
  - 异步受理：状态变为 `processing`，等待微信回调
  - 转账失败：状态变为 `pending_review`，进入人工审核队列
- 提现金额 **大于等于** 阈值：进入 `pending_review` 状态，需管理员手动审核

### 2.3 完整提现流程

#### 场景 A：小额自动提现（< 100元）

```
用户点击提现
    │
    ▼
┌─────────────────────────┐
│ 小程序端                 │
│ - 显示可提现余额         │
│ - 输入提现金额           │
│ - 点击确认提现           │
└────────┬────────────────┘
         │ POST /withdraw
         │ {amount: 5000}
         ▼
┌─────────────────────────┐
│ 后端服务                 │
│ 1. 校验用户权限          │
│ 2. 校验余额充足          │
│ 3. 扣除 unsettled_commission
│ 4. 创建提现记录          │
│    status: processing   │
│ 5. 调用微信转账          │
│    transfer_to_balance   │
└────────┬────────────────┘
         │ 请求转账
         ▼
┌─────────────────────────┐
│ 微信支付后台             │
│ - 校验商户权限           │
│ - 校验用户 openid        │
│ - 执行转账               │
└────────┬────────────────┘
         │ 返回结果
         ▼
┌─────────────────────────┐
│ 后端处理结果             │
│ ├─ SUCCESS: status=paid │
│ ├─ ACCEPTED: status=processing
│ └─ 失败: status=pending_review
└────────┬────────────────┘
         │ 返回结果
         ▼
┌─────────────────────────┐
│ 小程序端                 │
│ - 显示提现结果           │
│ - 如成功，提示已到账     │
│ - 如待审核，提示等待     │
└─────────────────────────┘
         │
         │ 微信推送
         ▼
┌─────────────────────────┐
│ 用户微信                 │
│ 收到零钱到账通知         │
│ "分销佣金提现 ¥50.00"   │
└─────────────────────────┘
```

#### 场景 B：大额人工审核（≥ 100元）

```
用户发起提现（200元）
    │
    ▼
┌─────────────────────────┐
│ 后端服务                 │
│ 1. 扣除余额              │
│ 2. 创建提现记录          │
│    status: pending_review│
│    （不调用微信转账）     │
└────────┬────────────────┘
         │ 返回"待审核"
         ▼
┌─────────────────────────┐
│ 小程序端                 │
│ 显示：提现申请已提交     │
│      等待管理员审核      │
└─────────────────────────┘
         │
         │ 管理员审核
         ▼
┌─────────────────────────┐
│ 管理后台                 │
│ 管理员点击"通过"         │
│ 调用微信转账             │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 用户微信                 │
│ 收到零钱到账通知         │
└─────────────────────────┘
```

#### 场景 C：自动转账失败

```
用户发起提现（50元）
    │
    ▼
┌─────────────────────────┐
│ 后端调用微信转账         │
│ 网络超时/配置错误        │
│ 返回异常                 │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 后端处理                 │
│ - 捕获异常               │
│ - 改状态为 pending_review│
│ - 金额已扣，需人工处理   │
└────────┬────────────────┘
         │ 返回"待审核"
         ▼
┌─────────────────────────┐
│ 管理员后台处理           │
│ 重新发起转账             │
└─────────────────────────┘
```

## 3. 用户端接口

### 3.1 获取分销商信息

**接口：** `POST /mp/distributor/me`

**响应字段：**
```json
{
  "unsettled_commission": 5000,      // 未结算佣金（可提现金额，单位：分）
  "total_withdrawn_amount": 10000,   // 累计已提现金额
  "withdrawable_amount": 5000,       // 当前可提现金额
  // ... 其他字段
}
```

### 3.2 创建提现申请

**接口：** `POST /mp/distributor/withdraw`

**请求参数：**
```json
{
  "amount": 5000   // 提现金额（单位：分）
}
```

**校验规则：**
1. 用户必须是分销商
2. 提现金额必须大于 0
3. 提现金额不能超过可提现余额

**响应数据：**
```json
{
  "withdraw_id": "WD20250426120000100001",
  "amount": 5000,
  "status": "processing",           // 或 "pending_review"
  "channel_name": "微信零钱",
  "receiver_name": "张三",
  "receiver_masked": "138****8888",
  "created_at": "2025-04-26T12:00:00Z",
  "withdrawable_amount_after": 0,   // 提现后剩余可提现金额
  "transfer_bill_no": "TRANS_xxx"   // 自动转账时的微信转账单号
}
```

**处理流程：**
1. 校验用户权限和余额
2. **先扣除用户 `unsettled_commission` 余额**（防止并发超提）
3. 创建提现记录，状态根据金额决定
4. 如果金额小于阈值，调用微信支付转账接口
5. 根据转账结果更新状态
6. 返回提现结果

**与微信支付交互：**
```
后端 ──POST──→ 微信支付 /v3/fund-app/mch-transfer/transfer-bills
请求头：
  Authorization: WECHATPAY2-SHA256-RSA2048 mchid="1230000109",...
  Content-Type: application/json
  Wechatpay-Serial: 444F4865EA9B34415...

请求体：
{
  "appid": "wxf636efh567hg5678",
  "out_bill_no": "WD20250426120000100001",
  "transfer_scene_id": "1005",
  "openid": "o-MYE42l80oelYMDMi34m1DVf0-4",
  "transfer_amount": 5000,
  "transfer_remark": "分销佣金提现",
  "user_recv_perception": "佣金提现",
  "notify_url": "https://api.example.com/api/v1/mp/distributor/withdrawals/notify/wechat"
}

后端 ←─Response── 微信支付
HTTP/1.1 200 OK
{
  "out_bill_no": "WD20250426120000100001",
  "transfer_bill_no": "TRANS_1234567890123456789",
  "state": "SUCCESS",
  "create_time": "2025-04-26T12:00:00+08:00"
}
```

### 3.3 查询提现记录列表

**接口：** `POST /mp/distributor/withdrawals`

**请求参数：**
```json
{
  "page": 1,
  "page_size": 20
}
```

**响应数据：**
```json
{
  "list": [
    {
      "withdraw_id": "WD20250426120000100001",
      "amount": 5000,
      "status": "paid",
      "channel_name": "微信零钱",
      "receiver_name": "张三",
      "receiver_masked": "138****8888",
      "created_at": "2025-04-26T12:00:00Z",
      "completed_at": "2025-04-26T12:01:30Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "page_total": 1,
  "total": 1
}
```

## 4. 管理端接口

### 4.1 微信支付转账回调接口（新增）

**接口：** `POST /api/v1/mp/distributor/withdrawals/notify/wechat`

**说明：** 接收微信支付转账结果的异步通知（商家转账到零钱）

#### 4.1.1 微信支付 V3 回调格式

**回调触发时机：**
- 转账状态变为终态时（SUCCESS/FAILED）
- 事件类型：`MCHTRANSFER.BILL.FINISHED`

**请求头（签名验证所需）：**
| 字段 | 说明 |
|------|------|
| Wechatpay-Serial | 微信支付平台证书序列号 |
| Wechatpay-Nonce | 随机字符串 |
| Wechatpay-Timestamp | 时间戳 |
| Wechatpay-Signature | 签名值 |

**请求体格式：**
```json
{
  "id": "EV-20250426120000-1234567890",
  "create_time": "2025-04-26T12:00:00+08:00",
  "resource_type": "encrypt-resource",
  "event_type": "MCHTRANSFER.BILL.FINISHED",
  "resource": {
    "original_type": "mch_transfer_bill",
    "algorithm": "AEAD_AES_256_GCM",
    "ciphertext": "...",
    "associated_data": "...",
    "nonce": "..."
  }
}
```

**字段说明：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 回调通知唯一 ID |
| create_time | string | 回调创建时间，RFC3339 格式 |
| resource_type | string | 资源类型，固定值 `encrypt-resource` |
| event_type | string | 事件类型，固定值 `MCHTRANSFER.BILL.FINISHED` |
| resource | object | 加密资源对象 |
| resource.original_type | string | 原始类型，固定值 `mch_transfer_bill` |
| resource.algorithm | string | 加密算法，固定值 `AEAD_AES_256_GCM` |
| resource.ciphertext | string | Base64 编码的密文 |
| resource.associated_data | string | 附加数据（AEAD）|
| resource.nonce | string | 加密随机串 |

#### 4.1.2 解密后数据格式

使用微信支付 V3 密钥（APIv3 Key）解密 `resource.ciphertext` 后得到：

```json
{
  "mchid": "1230000109",
  "out_bill_no": "WD20250426120000100001",
  "transfer_bill_no": "TRANS_1234567890123456789",
  "appid": "wxf636efh567hg5678",
  "state": "SUCCESS",
  "transfer_amount": 5000,
  "openid": "o-MYE42l80oelYMDMi34m1DVf0-4",
  "create_time": "2025-04-26T12:00:00+08:00",
  "update_time": "2025-04-26T12:01:30+08:00",
  "fail_reason": ""
}
```

**解密后字段说明：**
| 字段 | 类型 | 说明 |
|------|------|------|
| mchid | string | 商户号 |
| out_bill_no | string | 商户转账单号（即提现ID）|
| transfer_bill_no | string | 微信转账单号 |
| appid | string | 应用 ID |
| state | string | 转账状态：SUCCESS/FAILED |
| transfer_amount | int | 转账金额（分）|
| openid | string | 收款用户 OpenID |
| create_time | string | 转账创建时间 |
| update_time | string | 状态更新时间 |
| fail_reason | string | 失败原因（失败时返回）|

#### 4.1.3 回调处理流程

1. **接收回调请求**
   - 记录回调日志（用于对账和排查）

2. **验证签名（V3 回调）**
   ```python
   # 使用微信支付 SDK 验证签名
   # 1. 获取请求头中的签名信息
   # 2. 使用平台证书验证签名
   # 3. 验证时间戳防止重放攻击
   ```

3. **解密资源**
   ```python
   # 使用 APIv3 Key 解密 ciphertext
   # 算法：AEAD_AES_256_GCM
   ```

4. **提取关键字段**
   - `transfer_bill_no`: 微信转账单号
   - `out_bill_no`: 商户转账单号（提现ID）
   - `state`: 转账状态
   - `transfer_amount`: 转账金额（用于校验）

5. **业务处理**
   - 调用 `DistributorService.handle_transfer_callback()`
   - 根据 state 更新提现记录状态

6. **返回响应**

#### 4.1.4 响应格式

**成功响应（HTTP 200）：**
```json
{
  "code": "SUCCESS",
  "data": {
    "withdraw_id": "WD20250426120000100001",
    "status": "paid"
  }
}
```

**失败响应（HTTP 200，但业务失败）：**
```json
{
  "code": "FAIL",
  "message": "提现记录不存在"
}
```

**注意：** 即使处理失败，也应返回 HTTP 200，并通过 `code` 字段标识业务结果。微信支付会根据响应决定是否重试。

#### 4.1.5 回调状态处理

| 回调状态 | 业务处理 | 状态变更 |
|----------|----------|----------|
| SUCCESS | 转账成功 | `processing` → `paid`，更新累计提现金额 |
| FAILED | 转账失败 | `processing` → `failed`，金额退回余额 |

#### 4.1.6 幂等性保证

- 同一笔转账可能多次回调（网络重试）
- 使用 `out_bill_no` + `transfer_bill_no` 作为唯一标识
- 已处理的回调直接返回 SUCCESS，不做重复业务操作
- 建议记录回调日志，用于对账和排查

#### 4.1.7 Mock/测试格式（开发调试用）

为方便开发和测试，接口同时支持简化格式：

```json
{
  "transfer_bill_no": "TRANS_1234567890123456789",
  "out_bill_no": "WD20250426120000100001",
  "state": "SUCCESS"
}
```

**注意：** 生产环境必须使用 V3 回调格式并验证签名。

### 4.2 查询提现列表

**接口：** `GET /admin/distributor/withdrawals`

**查询参数：**
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）
- `status`: 状态筛选（可选：pending_review, processing, paid, rejected）

**响应数据：**
```json
{
  "list": [
    {
      "withdraw_id": "WD20250426120000100001",
      "user_id": 100001,
      "nickname": "张三",
      "avatar_url": "https://...",
      "amount": 5000,
      "status": "pending_review",
      "channel_name": "微信零钱",
      "receiver_name": "张三",
      "receiver_masked": "138****8888",
      "created_at": "2025-04-26T12:00:00Z",
      "completed_at": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "page_total": 1,
  "total": 1
}
```

### 4.2 审核通过提现

**接口：** `POST /admin/distributor/withdrawals/{withdraw_id}/approve`

**响应数据：**
```json
{
  "withdraw_id": "WD20250426120000100001",
  "status": "paid",
  "amount": 5000,
  "transfer_state": "SUCCESS",
  "transfer_bill_no": "TRANS_xxx",
  "package_info": "",
  "completed_at": "2025-04-26T12:01:30Z"
}
```

**处理流程：**
1. 校验提现记录状态为 `pending_review`
2. 调用微信支付转账接口
3. 更新提现状态为 `paid` 或 `processing`
4. 更新用户累计提现金额

### 4.3 审核拒绝提现

**接口：** `POST /admin/distributor/withdrawals/{withdraw_id}/reject`

**响应数据：**
```json
{
  "withdraw_id": "WD20250426120000100001",
  "status": "rejected",
  "amount": 5000
}
```

**处理流程：**
1. 校验提现记录状态为 `pending_review`
2. 将提现金额退回用户 `unsettled_commission`
3. 更新提现状态为 `rejected`

## 5. 服务层方法

### 5.1 create_withdrawal（创建提现）

**功能：** 用户发起提现申请

**自动提现逻辑：**
1. 校验用户权限和余额
2. **先扣除用户余额**（防止并发问题）
3. 创建提现记录，初始状态根据金额决定
4. 如果金额 < 阈值，调用 `_process_withdraw_transfer` 执行自动转账
5. 如果自动转账失败，状态改为 `pending_review`，进入人工审核
6. 提交事务

### 5.2 _process_withdraw_transfer（处理转账）

**功能：** 调用微信支付执行转账

**状态处理：**
- `SUCCESS`: 同步成功，更新为 `paid`，更新累计提现金额
- `ACCEPTED/PROCESSING/WAIT_PAY`: 异步受理，更新为 `processing`，等待回调
- 其他状态: 抛出异常，由上层处理为失败

### 5.3 handle_transfer_callback（处理回调）

**功能：** 处理微信支付异步回调

**方法签名：**
```python
def handle_transfer_callback(
    self,
    *,
    transfer_bill_no: str,  # 微信转账单号
    state: str,              # 转账状态
    out_bill_no: str = ""    # 商户转账单号（提现ID）
) -> dict
```

**参数说明：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| transfer_bill_no | str | 是 | 微信转账单号，微信生成 |
| state | str | 是 | 转账状态：SUCCESS/FAILED |
| out_bill_no | str | 否 | 商户转账单号，用于查找提现记录 |

**处理逻辑：**

1. **查找提现记录**
   - 优先使用 `out_bill_no` 查找
   - 或使用 `transfer_bill_no` 查找
   - 找不到则抛出异常

2. **幂等性检查**
   - 如果状态已经是终态（paid/failed/rejected），直接返回
   - 防止重复处理同一回调

3. **状态处理**

| 回调状态 | 业务处理 | 数据库更新 |
|----------|----------|------------|
| SUCCESS | 1. 更新提现状态<br>2. 更新累计提现金额<br>3. 记录完成时间 | `status='paid'`<br>`total_withdrawn_amount += amount`<br>`completed_at=now()` |
| FAILED | 1. 将金额退回用户余额<br>2. 更新提现状态<br>3. 记录失败原因 | `unsettled_commission += amount`<br>`status='failed'`<br>`completed_at=now()` |

4. **返回结果**
```python
{
    "withdraw_id": "WD20250426120000100001",
    "status": "paid",  # 或 "failed"
    "transfer_bill_no": "TRANS_xxx"
}
```

**异常处理：**
| 异常场景 | 处理方式 |
|----------|----------|
| 提现记录不存在 | 抛出 ValidationError，返回 "提现记录不存在" |
| 状态已经是终态 | 直接返回，不做重复处理 |
| 数据库更新失败 | 抛出异常，微信支付会重试回调 |

## 6. 微信支付转账

### 6.1 转账接口

使用微信支付「商家转账到零钱」功能，调用微信支付 V3 接口。

#### 6.1.1 接口定义

**请求 URL：** `POST https://api.mch.weixin.qq.com/v3/fund-app/mch-transfer/transfer-bills`

**请求头：**
| 字段 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | 微信支付 V3 签名认证头 |
| Content-Type | 是 | `application/json` |
| Wechatpay-Serial | 是 | 微信支付平台证书序列号 |

**请求参数：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| appid | string | 是 | 直连商户申请的公众号/小程序 appid |
| out_bill_no | string | 是 | 商户转账单号，唯一标识一笔转账，最多 32 个字符 |
| transfer_scene_id | string | 是 | 转账场景 ID，固定值 `1005`（分销返佣） |
| openid | string | 是 | 收款用户 OpenID |
| transfer_amount | int | 是 | 转账金额，单位分（最小 1 分，最大 200 元 = 20000 分） |
| transfer_remark | string | 是 | 转账备注，用户可见，最多 32 个字符 |
| user_recv_perception | string | 否 | 用户收款感知，如"佣金提现" |
| notify_url | string | 否 | 异步通知回调地址 |

**请求示例：**
```json
{
  "appid": "wxf636efh567hg5678",
  "out_bill_no": "WD20250426120000100001",
  "transfer_scene_id": "1005",
  "openid": "o-MYE42l80oelYMDMi34m1DVf0-4",
  "transfer_amount": 5000,
  "transfer_remark": "分销佣金提现",
  "user_recv_perception": "佣金提现",
  "notify_url": "https://api.example.com/api/v1/mp/distributor/withdrawals/notify/wechat"
}
```

**响应参数：**
| 字段 | 类型 | 说明 |
|------|------|------|
| out_bill_no | string | 商户转账单号 |
| transfer_bill_no | string | 微信转账单号 |
| state | string | 转账状态：SUCCESS/ACCEPTED/PROCESSING/WAIT_PAY/FAILED |
| create_time | string | 创建时间，RFC3339 格式 |
| fail_reason | string | 失败原因（失败时返回）|

**响应状态说明：**
| 状态 | 说明 | 处理方式 |
|------|------|----------|
| SUCCESS | 转账成功 | 更新状态为 `paid` |
| ACCEPTED | 已受理 | 更新状态为 `processing`，等待回调 |
| PROCESSING | 处理中 | 更新状态为 `processing`，等待回调 |
| WAIT_PAY | 待支付 | 更新状态为 `processing`，等待回调 |
| WAIT_USER_CONFIRM | 待用户确认 | 更新状态为 `processing`，等待回调 |
| FAILED | 转账失败 | 更新状态为 `pending_review` 或 `failed` |

### 6.2 转账结果处理

**同步成功（SUCCESS）：**
- 更新提现状态为 `paid`
- 更新 `completed_at` 时间
- 更新用户 `total_withdrawn_amount`

**异步受理（ACCEPTED/PROCESSING）：**
- 更新提现状态为 `processing`
- 等待微信支付异步回调通知
- 收到回调后更新为 `paid` 或 `failed`

**转账失败：**
- 自动转账失败：状态变为 `pending_review`，等待人工处理
- 异步回调失败：金额退回用户余额，状态改为 `failed`
- 人工审核后转账失败：金额退回用户余额

## 7. 数据模型

### 7.1 DistributorWithdrawal（提现记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| withdraw_id | str | 提现单号（唯一） |
| user_id | int | 用户ID |
| amount | int | 提现金额（分） |
| account_name | str | 收款人姓名 |
| bank_name | str | 银行名称（固定"微信零钱"） |
| bank_account_masked | str | 脱敏账号 |
| status | str | 状态 |
| completed_at | datetime | 完成时间 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 7.2 DistributorProfile（分销商档案）

| 字段 | 类型 | 说明 |
|------|------|------|
| unsettled_commission | int | 未结算佣金（可提现） |
| total_withdrawn_amount | int | 累计已提现金额 |
| ... | ... | 其他字段 |

## 8. 前端交互流程

### 8.1 用户提现流程

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐
│ 我的页面  │ ──→ │  分销商中心  │ ──→ │   提现页面   │
└─────────┘     └─────────────┘     └──────┬──────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │  输入金额    │
                                    │  确认提现    │
                                    └──────┬──────┘
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                        ┌─────────┐  ┌─────────┐  ┌─────────┐
                        │ 自动到账 │  │ 待审核   │  │ 余额不足 │
                        │ 成功提示 │  │ 提交成功 │  │ 错误提示 │
                        └─────────┘  └─────────┘  └─────────┘
```

### 8.2 小程序端与后端交互

**发起提现：**
```javascript
// 小程序端代码示例
async function handleWithdraw(amount) {
  wx.showLoading({ title: '处理中...' });
  
  try {
    const res = await wx.request({
      url: 'https://api.example.com/api/v1/mp/distributor/withdraw',
      method: 'POST',
      header: { 'Authorization': `Bearer ${token}` },
      data: { amount: amount }  // 单位：分
    });
    
    if (res.data.code === 0) {
      const { status, withdraw_id } = res.data.data;
      
      switch(status) {
        case 'paid':
          wx.showToast({ title: '提现成功，已到账' });
          break;
        case 'processing':
          wx.showToast({ title: '处理中，请稍后查看' });
          break;
        case 'pending_review':
          wx.showModal({
            title: '提现申请已提交',
            content: '大额提现需要管理员审核，审核通过后到账',
            showCancel: false
          });
          break;
      }
    } else {
      wx.showToast({ title: res.data.message, icon: 'none' });
    }
  } finally {
    wx.hideLoading();
  }
}
```

**查询提现记录：**
```javascript
async function loadWithdrawals(page = 1) {
  const res = await wx.request({
    url: 'https://api.example.com/api/v1/mp/distributor/withdrawals',
    method: 'POST',
    header: { 'Authorization': `Bearer ${token}` },
    data: { page, page_size: 20 }
  });
  
  return res.data.data.list.map(item => ({
    ...item,
    statusText: getStatusText(item.status),
    amountYuan: (item.amount / 100).toFixed(2)
  }));
}

function getStatusText(status) {
  const map = {
    'pending_review': '待审核',
    'processing': '处理中',
    'paid': '已到账',
    'rejected': '已拒绝',
    'failed': '失败'
  };
  return map[status] || status;
}
```

### 8.3 提现页面设计

**提现页面：**
```
┌─────────────────────────┐
│ ← 提现                  │
├─────────────────────────┤
│                         │
│  可提现余额              │
│  ¥200.00               │
│                         │
├─────────────────────────┤
│ 提现金额                │
│ ┌─────────────────────┐ │
│ │ ¥                  │ │
│ │ 50.00              │ │
│ └─────────────────────┘ │
│ 最小提现金额 ¥1.00      │
├─────────────────────────┤
│ 提现到                  │
│ ┌─────────────────────┐ │
│ │ 💰 微信零钱         │ │
│ │    预计实时到账     →│ │
│ └─────────────────────┘ │
├─────────────────────────┤
│                         │
│    [   立即提现   ]     │
│                         │
├─────────────────────────┤
│ 查看提现记录 >          │
└─────────────────────────┘
```

**提现记录页面：**
```
┌─────────────────────────┐
│ ← 提现记录              │
├─────────────────────────┤
│ 2025-04-26 14:30    ┌───┐
│ 提现 ¥50.00         │已 │
│ 单号：WD20250426... │到账│
├─────────────────────────┤
│ 2025-04-25 09:15    ┌───┐
│ 提现 ¥200.00        │待 │
│ 单号：WD20250425... │审核│
├─────────────────────────┤
│ 2025-04-20 16:45    ┌───┐
│ 提现 ¥100.00        │已 │
│ 单号：WD20250420... │拒绝│
└─────────────────────────┘
```

**状态标签样式：**
- `待审核` - 橙色标签
- `处理中` - 蓝色标签  
- `已到账` - 绿色标签
- `已拒绝` - 红色标签
- `失败` - 灰色标签

## 9. 异常处理

### 9.1 用户端异常

| 场景 | 错误提示 |
|------|----------|
| 非分销商 | "您还不是分销商" |
| 余额不足 | "可提现余额不足" |
| 金额非法 | "请输入正确的提现金额" |
| 系统错误 | "提现申请失败，请稍后重试" |

### 9.2 管理端异常

| 场景 | 错误提示 |
|------|----------|
| 提现不存在 | "提现记录不存在" |
| 状态错误 | "该提现已处理" |
| 转账失败 | "转账失败，请检查配置或稍后重试" |

## 10. 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| distributor_withdraw_auto_approve_fen | 10000 | 自动转账阈值（分） |
| wechat_transfer_scene_id | 1005 | 微信支付场景ID |
| wechat_transfer_remark | "分销佣金提现" | 转账备注 |
| wechat_transfer_user_recv_perception | "" | 用户收款感知 |

## 11. 金额处理机制

### 11.1 余额冻结机制

```
用户申请提现 100元（10000分）
    │
    ▼
┌─────────────────────────┐
│ 提现前：                 │
│ unsettled_commission: 20000
│ total_withdrawn_amount: 50000
└────────┬────────────────┘
         │ 扣除余额
         ▼
┌─────────────────────────┐
│ 提现后：                 │
│ unsettled_commission: 10000  ← 立即扣除
│ total_withdrawn_amount: 50000 ← 不变
└────────┬────────────────┘
         │
    ┌────┴────┬────────────┐
    ▼         ▼            ▼
┌───────┐ ┌────────┐  ┌──────────┐
│ 成功   │ │ 失败   │  │ 被拒绝   │
│ paid  │ │ failed │  │ rejected │
└───┬───┘ └───┬────┘  └────┬─────┘
    │         │            │
    ▼         ▼            ▼
┌─────────────────────────────────┐
│ total_withdrawn_amount: 60000   │ ← 成功时更新
│ unsettled_commission: 10000     │ ← 不变
└─────────────────────────────────┘
         │         │            │
         ▼         ▼            ▼
┌─────────────────────────────────┐
│ 失败/拒绝时退回：                │
│ unsettled_commission: 20000     │ ← 恢复原值
│ total_withdrawn_amount: 50000   │ ← 不变
└─────────────────────────────────┘
```

### 11.2 关键设计原则

1. **先扣后转**：先扣除余额，再调用支付渠道
2. **失败回滚**：任何环节失败，金额退回用户余额
3. **幂等控制**：同一提现单号重复提交，支付渠道不会重复转账
4. **状态机**：严格的状态流转，防止重复处理

## 12. 安全考虑

### 12.1 系统安全

1. **金额校验**
   - 提现前校验余额 ≥ 提现金额
   - 校验提现金额 > 0
   - 校验提现金额 ≤ 单日/单笔限额

2. **并发安全**
   - 先扣余额再创建记录
   - 数据库事务保证原子性
   - 同一用户同时只能有一笔处理中的提现

3. **转账幂等**
   - 使用唯一 `out_bill_no`（提现ID）
   - 微信支付根据商户单号去重
   - 重复提交返回相同结果

4. **回调安全**
   - 验证微信支付回调签名
   - 解密回调数据
   - 处理完成后返回 SUCCESS

### 12.2 业务安全

1. **权限控制**
   - 只有分销商可以提现
   - 只有管理员可以审核
   - 只能提现自己的余额

2. **风控策略**
   - 小额自动提现（< 100元）
   - 大额人工审核（≥ 100元）
   - 异常提现自动拦截

3. **敏感信息保护**
   - 银行账号脱敏展示
   - 接口返回最小必要信息
   - 日志中隐藏敏感字段

### 12.3 异常处理

| 异常场景 | 处理策略 | 用户提示 |
|---------|---------|---------|
| 余额不足 | 拒绝提现 | "可提现余额不足" |
| 支付渠道超时 | 标记为待审核 | "系统繁忙，已转人工处理" |
| 支付渠道失败 | 退回余额 | "提现失败，金额已退回" |
| 重复提交 | 返回已有结果 | 正常返回 |
| 回调延迟 | 主动查询状态 | 显示"处理中" |

## 13. 监控与对账

### 13.1 监控指标

- 提现成功率
- 平均到账时间
- 自动提现比例
- 人工审核积压量

### 13.2 每日对账

```
系统提现记录 vs 微信支付流水
- 核对笔数是否一致
- 核对金额是否匹配
- 核对状态是否同步
- 处理差异记录
```
