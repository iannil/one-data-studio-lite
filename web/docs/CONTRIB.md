# Frontend Development Guide

本文档介绍 ONE-DATA-STUDIO-LITE 前端 (Web) 的开发指南。

---

## 环境准备

### 系统要求

- Node.js 18+
- npm 或 pnpm
- Python 3.11+ (后端服务)

### 克隆项目

```bash
git clone <repo-url>
cd one-data-studio-lite/web
```

### 安装依赖

```bash
npm install
# 或
pnpm install
```

### 配置环境变量

前端通过 Vite 代理访问后端 API，环境变量配置在项目根目录的 `.env` 文件中：

```bash
# 从示例文件复制
cp ../.env.example ../.env
# 编辑 .env 文件设置必要的配置
```

---

## 项目结构

```
web/
├── src/
│   ├── api/              # API 客户端模块
│   │   ├── auth.ts       # 认证 API
│   │   ├── client.ts     # HTTP 客户端
│   │   ├── types.ts      # API 类型定义
│   │   └── *.test.ts     # 单元测试
│   ├── components/       # React 组件
│   ├── pages/            # 页面组件
│   ├── mock/             # Mock 数据
│   ├── utils/            # 工具函数
│   ├── main.tsx          # 应用入口
│   └── App.tsx           # 根组件
├── e2e/                  # E2E 测试
│   ├── pages/            # Page Object Model
│   ├── tests/            # 测试用例
│   └── playwright.config.ts
├── docs/                 # 文档
├── package.json          # 项目配置
├── vite.config.ts        # Vite 配置
├── tsconfig.json         # TypeScript 配置
└── eslint.config.js      # ESLint 配置
```

---

## 可用脚本

### 开发

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器 (http://localhost:3000) |
| `npm run build` | 构建生产版本 |
| `npm run preview` | 预览构建产物 |

### 代码质量

| 命令 | 说明 |
|------|------|
| `npm run lint` | 运行 ESLint 检查 |
| `npm run lint:fix` | 自动修复 ESLint 问题 |

### 单元测试 (Vitest)

| 命令 | 说明 |
|------|------|
| `npm run test` | 运行测试 (watch 模式) |
| `npm run test:ui` | 启动 Vitest UI |
| `npm run test:run` | 运行所有测试一次 |
| `npm run test:coverage` | 生成测试覆盖率报告 |
| `npm run test:watch` | 监视模式运行测试 |

### E2E 测试 (Playwright)

| 命令 | 说明 |
|------|------|
| `npm run e2e` | 运行所有 E2E 测试 |
| `npm run e2e:ui` | 启动 Playwright UI |
| `npm run e2e:debug` | 调试模式运行测试 |
| `npm run e2e:headed` | 有头模式运行测试 |
| `npm run e2e:report` | 查看测试报告 |
| `npm run e2e:p0` | 运行 P0 优先级测试 |
| `npm run e2e:p1` | 运行 P1 优先级测试 |
| `npm run e2e:smoke` | 运行冒烟测试 |
| `npm run e2e:auth` | 运行认证测试 |

---

## 开发规范

### 组件开发

使用函数组件 + Hooks：

```tsx
import { useState, useEffect } from 'react';
import { Button, Form, Input } from 'antd';

interface MyComponentProps {
  title: string;
  onSubmit?: (data: any) => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({ title, onSubmit }) => {
  const [form] = Form.useForm();

  const handleSubmit = async (values: any) => {
    onSubmit?.(values);
  };

  return (
    <div>
      <h2>{title}</h2>
      <Form form={form} onFinish={handleSubmit}>
        <Form.Item name="username" label="用户名">
          <Input />
        </Form.Item>
        <Button type="primary" htmlType="submit">提交</Button>
      </Form>
    </div>
  );
};
```

### API 调用

使用统一的 API 客户端：

```tsx
import { login, getUserInfo } from '@/api/auth';
import type { LoginRequest, User } from '@/api/types';

export const LoginForm = () => {
  const handleLogin = async (values: LoginRequest) => {
    try {
      const response = await login(values);
      if (isSuccessResponse(response)) {
        // 登录成功
        const user = await getUserInfo();
      }
    } catch (error) {
      // 错误处理
    }
  };

  return <Form onFinish={handleLogin}>...</Form>;
};
```

### 路由配置

使用 react-router-dom：

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '@/pages/Login';
import { DashboardPage } from '@/pages/Dashboard';

export const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
```

---

## 状态管理

使用 Zustand 进行状态管理：

```tsx
import { create } from 'zustand';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  login: (user, token) => {
    localStorage.setItem('token', token);
    set({ user, token });
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null });
  },
}));
```

---

## 测试

### 单元测试

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    screen.getByText('Click me').click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### E2E 测试

```tsx
import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder="用户名"]', 'admin');
    await page.fill('input[placeholder="密码"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
```

---

## 样式指南

- 使用 Ant Design 组件库
- 遵循 Ant Design 设计规范
- 使用 CSS Modules 或 styled-components 处理样式

---

## 调试

### 浏览器 DevTools

1. 打开浏览器开发者工具 (F12)
2. 使用 React Developer Tools 调试组件
3. 使用 Redux DevTools 调试状态 (如果使用)

### Vite HMR

开发服务器支持热模块替换，修改代码后会自动刷新。

---

## 常见问题

### 端口冲突

如果 3000 端口被占用，修改 `vite.config.ts` 中的端口配置。

### API 请求失败

1. 确认后端服务正在运行 (http://localhost:8010)
2. 检查 Vite 代理配置
3. 查看浏览器控制台和网络请求

### 构建失败

1. 清除 node_modules 和重新安装：`rm -rf node_modules && npm install`
2. 检查 TypeScript 类型错误
3. 运行 `npm run lint` 检查代码问题
