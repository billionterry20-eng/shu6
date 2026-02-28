# 步数自动提交系统

基于 Flask 的自动化步数提交系统，支持多账号管理、定时任务和提交记录。

## 功能特性

- ✅ 多账号管理（添加、编辑、删除）
- ⏰ 定时任务（每个账号独立设置时间）
- 📊 提交记录查询
- 📝 系统日志
- 🎨 Web 管理界面
- 🚀 支持 Render 部署

## 默认账号

系统初始化时自动创建：
- 账号：`Tbh2356@126.com`
- 密码：`112233qq`
- 步数：`38889`
- 定时：`00:05`（每天凌晨 0 点 5 分）

## 部署到 Render

### 方法一：Blueprint（推荐）

1. Fork 代码到 GitHub
2. 登录 [Render](https://render.com)
3. New + → Blueprint
4. 选择仓库，自动读取 `render.yaml`

### 方法二：手动创建

1. New + → Web Service
2. 选择 Python 3 运行时
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 60`

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python app.py

# 访问 http://localhost:5000
```

## API 接口

- `GET /api/accounts` - 获取账号列表
- `POST /api/accounts` - 创建账号
- `PUT /api/accounts/<id>` - 更新账号
- `DELETE /api/accounts/<id>` - 删除账号
- `POST /api/accounts/<id>/submit` - 手动提交
- `GET /api/records` - 获取提交记录
- `GET /api/logs` - 获取系统日志
- `POST /api/test-submit` - 测试提交

## 注意事项

1. **Token 更新**：如果提交失败，可能需要更新 Authorization 和 time token
2. **频率限制**：API 有频率限制，短时间内多次提交会失败
3. **时区**：所有定时任务使用北京时间

## 更新 Token

1. 使用抓包工具（如 Stream）抓取成功请求
2. 复制 `Authorization` 和 `time` 值
3. 在账号编辑页面更新

## 测试提交

```bash
curl -X POST http://localhost:5000/api/test-submit \
  -H "Content-Type: application/json" \
  -d '{"phone":"Tbh2356@126.com","password":"112233qq","steps":38889}'
```
