# Frontend Runbook

本文档包含 ONE-DATA-STUDIO-LITE 前端的部署、监控和故障处理指南。

---

## 部署流程

### 1. 开发环境部署

```bash
# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
# 访问 http://localhost:3000

# 3. 启动后端服务 (在另一个终端)
cd ../services
python -m portal.main
```

### 2. 生产环境构建

```bash
# 1. 构建前端
cd web
npm run build

# 2. 构建产物输出到
# ../services/portal/static/

# 3. 重启后端服务
# 静态文件将由 Portal 服务托管
```

### 3. Docker 部署

```bash
# 使用项目根目录的 docker-compose.yml
docker-compose up -d portal

# 或使用 Make
make portal-up
```

---

## 监控和告警

### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 页面加载时间 | 首屏内容加载时间 | > 3s |
| API 响应时间 | 后端 API 响应延迟 | > 1s |
| 错误率 | JavaScript 错误发生率 | > 1% |
| 资源大小 | 打包后资源体积 | > 5MB |

### 浏览器控制台监控

打开浏览器开发者工具查看：

```javascript
// 查看未捕获的错误
window.addEventListener('error', (e) => {
  console.error('Error:', e.message);
});

// 查看 Promise 拒绝
window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled rejection:', e.reason);
});
```

---

## 常见问题和修复

### 问题 1: 页面空白

**症状**: 浏览器显示空白页面，控制台有错误

**可能原因**:
1. JavaScript 错误导致组件渲染失败
2. API 请求失败导致数据加载失败
3. 路由配置错误

**排查步骤**:
```bash
# 1. 检查浏览器控制台错误
# 打开 F12 → Console

# 2. 检查网络请求
# 打开 F12 → Network

# 3. 检查构建产物
npm run build
# 查看是否有构建错误
```

**修复方法**:
- 检查组件代码中的 JavaScript 错误
- 确认后端 API 正常运行
- 检查路由配置是否正确

---

### 问题 2: API 请求失败 (CORS 错误)

**症状**: 控制台显示 CORS 相关错误

**可能原因**:
1. 后端 CORS 配置不正确
2. Vite 代理配置失效
3. 后端服务未启动

**排查步骤**:
```bash
# 1. 检查后端服务
curl http://localhost:8010/health

# 2. 检查 Vite 配置
cat vite.config.ts

# 3. 检查网络请求
# F12 → Network → 查看 Request Headers
```

**修复方法**:
```typescript
// vite.config.ts 确保代理配置正确
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
    },
  },
});
```

---

### 问题 3: 样式加载异常

**症状**: 页面显示但样式混乱

**可能原因**:
1. Ant Design CSS 未加载
2. 样式文件路径错误
3. CSS Modules 配置问题

**修复方法**:
```tsx
// 确保在 main.tsx 中导入 Ant Design 样式
import 'antd/dist/reset.css';

// 或使用按需导入
import { ConfigProvider } from 'antd';
```

---

### 问题 4: 构建失败

**症状**: `npm run build` 报错

**可能原因**:
1. TypeScript 类型错误
2. 依赖版本冲突
3. 内存不足

**排查步骤**:
```bash
# 1. 检查 TypeScript 错误
npx tsc --noEmit

# 2. 清理缓存
rm -rf node_modules dist
npm install

# 3. 增加 Node.js 内存限制
NODE_OPTIONS=--max_old_space_size=4096 npm run build
```

---

### 问题 5: E2E 测试失败

**症状**: Playwright 测试无法找到元素

**可能原因**:
1. 页面加载超时
2. 元素选择器错误
3. 应用未正确启动

**修复方法**:
```typescript
// 增加超时时间
await page.waitForSelector('selector', { timeout: 30000 });

// 使用更稳定的选择器
// 优先使用 data-testid
<input data-testid="username-input" />
await page.fill('[data-testid="username-input"]', 'admin');

// 检查页面状态
await page.waitForLoadState('networkidle');
```

---

## 回滚流程

### 1. 前端回滚

```bash
# 方法 1: Git 回退
git log --oneline  # 查看提交历史
git checkout <previous-commit>
npm run build

# 方法 2: 恢复备份
cp -r ../backup/portal/static/* ../services/portal/static/
```

### 2. 完整回滚 (前端 + 后端)

```bash
# 停止服务
docker-compose down

# 回退代码
git checkout <previous-tag>

# 重新部署
docker-compose up -d
```

---

## 性能优化

### 构建优化

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    // 代码分割
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd-vendor': ['antd', '@ant-design/icons'],
        },
      },
    },
    // 压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // 移除 console
      },
    },
  },
});
```

### 运行时优化

1. **懒加载路由组件**
```tsx
const Dashboard = lazy(() => import('./pages/Dashboard'));
```

2. **使用 useMemo 和 useCallback**
```tsx
const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b]);
```

3. **虚拟滚动** (Ant Design Table)
```tsx
<Table
  scroll={{ y: 400 }}
  pagination={false}
/>
```

---

## 日志和调试

### 前端日志

```javascript
// 生产环境禁用 console.log
if (import.meta.env.PROD) {
  console.log = () => {};
  console.debug = () => {};
}

// 使用自定义日志
const logger = {
  info: (...args: any[]) => {
    if (import.meta.env.DEV) {
      console.log('[INFO]', ...args);
    }
  },
  error: (...args: any[]) => {
    console.error('[ERROR]', ...args);
    // 发送到日志服务
  },
};
```

### 错误监控

集成 Sentry 或类似服务：

```tsx
import * as Sentry from '@sentry/react';

if (import.meta.env.PROD) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
  });
}
```

---

## 健康检查

```bash
# 检查前端服务
curl http://localhost:3000

# 检查后端 API
curl http://localhost:8010/health

# 检查构建状态
ls -lh ../services/portal/static/
```

---

## 紧急联系

| 角色 | 联系方式 |
|------|---------|
| 前端负责人 | - |
| 运维负责人 | - |
| 项目经理 | - |
