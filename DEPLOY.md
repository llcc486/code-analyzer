# 部署指南

## 方案：Render 免费部署

### 步骤

1. **推送代码到GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/你的用户名/code-analyzer.git
   git push -u origin main
   ```

2. **在Render部署**
   - 访问 https://render.com 注册/登录
   - 点击 "New" → "Web Service"
   - 连接你的GitHub仓库
   - 配置：
     - Name: `code-analyzer`
     - Environment: `Python`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python main.py server`
   
3. **设置环境变量**（在Render Dashboard → Environment）
   ```
   OPENAI_API_KEY=你的DeepSeek密钥
   OPENAI_MODEL=deepseek-chat
   OPENAI_BASE_URL=https://api.deepseek.com/v1
   LLM_PROVIDER=openai
   HOST=0.0.0.0
   PORT=10000
   ```

4. **部署完成**
   - Render会自动构建和部署
   - 访问 `https://你的应用名.onrender.com` 即可使用

### 注意事项
- Render免费版会在15分钟无访问后休眠，首次访问需等待约30秒启动
- 免费版每月有750小时运行时间限制
