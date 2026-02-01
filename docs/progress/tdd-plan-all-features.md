# ONE-DATA-STUDIO-LITE TDD 完整规划

**创建时间**: 2026-02-01
**目标覆盖率**: 80% (API层100%)
**测试框架**: Vitest + React Testing Library + Playwright

---

## 目录

- [1. 测试基础设施搭建](#1-测试基础设施搭建)
- [2. API层测试计划](#2-api层测试计划)
- [3. 工具层测试计划](#3-工具层测试计划)
- [4. 状态管理测试计划](#4-状态管理测试计划)
- [5. 组件层测试计划](#5-组件层测试计划)
- [6. E2E测试计划](#6-e2e测试计划)
- [7. 实施顺序](#7-实施顺序)

---

## 1. 测试基础设施搭建

### 1.1 安装依赖

```bash
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
npm install -D @vitest/coverage-v8
```

### 1.2 创建 `vitest.config.ts`

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mock/**',
        'src/main.tsx',
      ],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### 1.3 创建测试工具文件 `src/test/setup.ts`

```typescript
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
```

### 1.4 更新 `package.json` scripts

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest --watch"
  }
}
```

---

## 2. API层测试计划

**覆盖率要求**: 100% (核心业务逻辑)

### 2.1 API类型和工具 (`src/api/types.ts`, `src/api/utils.ts`)

**测试文件**: `src/api/types.test.ts`, `src/api/utils.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `isSuccessResponse` | P0 | 成功响应返回true |
| | P0 | 失败响应返回false |
| | P1 | 边界值测试(0, 20000) |
| `getErrorMessage` | P0 | 所有错误码映射正确 |
| | P1 | 未知错误码返回默认消息 |
| `createSuccessResponse` | P0 | 创建标准成功响应 |
| `createErrorResponse` | P0 | 创建标准错误响应 |
| `createPaginatedResponse` | P0 | 创建分页响应 |
| | P1 | 空数据分页 |
| | P1 | 单页数据等于总数 |
| `unwrapApiResponse` | P0 | 正常响应解包 |
| | P0 | 成功但data为null抛错 |
| | P0 | 失败响应抛错误 |
| | P1 | 非ApiResponse格式直接返回 |
| `handleResponse` | P0 | 成功响应返回data |
| | P0 | 失败显示错误消息 |
| | P1 | showSuccess选项 |
| `handleApiError` | P0 | Error对象提取消息 |
| | P0 | 字符串直接使用 |
| | P1 | 401清除token并跳转 |
| `retryRequest` | P0 | 重试成功 |
| | P0 | 达最大重试次数抛错 |
| | P1 | 指数退避延迟 |

### 2.2 认证API (`src/api/auth.ts`)

**测试文件**: `src/api/auth.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `login` | P0 | 成功登录返回token |
| | P0 | 失败登录抛错误 |
| | P1 | 网络错误处理 |
| `refreshToken` | P0 | 成功刷新返回新token |
| | P0 | token无效抛错 |
| `validateToken` | P0 | 有效token返回true |
| | P0 | 过期token返回false |
| `revokeToken` | P0 | 成功撤销返回true |
| `getUserInfo` | P0 | 返回用户信息 |
| | P0 | 未认证抛错 |
| `updatePassword` | P0 | 密码正确返回true |
| | P0 | 旧密码错误返回false |
| `updateProfile` | P0 | 成功更新返回用户信息 |
| | P1 | 验证失败抛错 |

### 2.3 审计日志API (`src/api/audit.ts`)

**测试文件**: `src/api/audit.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `getLogs` | P0 | 返回审计日志列表 |
| | P0 | 带筛选参数查询 |
| | P0 | 分页参数正确传递 |
| | P1 | 空列表处理 |
| `getLog` | P0 | 返回单条日志 |
| | P0 | 不存在的ID抛错 |
| `getStats` | P0 | 返回统计数据 |
| `exportLogs` | P0 | CSV格式导出 |
| | P0 | JSON格式导出 |
| | P1 | 大数据量导出 |

### 2.4 敏感数据API (`src/api/sensitive.ts`)

**测试文件**: `src/api/sensitive.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `scan` | P0 | 成功扫描返回报告 |
| | P0 | 无敏感数据返回空结果 |
| `classify` | P0 | LLM分类成功 |
| | P0 | 空数据样本抛错 |
| `getRules` | P0 | 返回规则列表 |
| | P0 | 空列表处理 |
| `getRule` | P0 | 返回单个规则 |
| | P0 | 不存在返回404 |
| `addRule` | P0 | 成功添加返回规则 |
| | P0 | 重复名称抛错 |
| `deleteRule` | P0 | 成功删除 |
| | P0 | 规则不存在抛错 |
| `getReports` | P0 | 返回报告列表 |
| | P1 | 分页处理 |
| `scanAndApply` | P0 | 成功扫描并应用 |
| | P1 | 部分应用场景 |
| | P1 | 全部跳过场景 |

### 2.5 SeaTunnel API (`src/api/seatunnel.ts`)

**测试文件**: `src/api/seatunnel.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `getJobsV1` | P0 | 返回任务列表 |
| | P0 | 状态筛选running |
| | P0 | 状态筛选finished |
| `getJobDetailV1` | P0 | 返回任务详情 |
| | P0 | 不存在任务抛错 |
| `getJobStatusV1` | P0 | 返回任务状态 |
| `submitJobV1` | P0 | 成功提交任务 |
| | P1 | 配置校验失败 |
| `cancelJobV1` | P0 | 成功取消运行中任务 |
| | P1 | 取消已完成任务抛错 |
| `getClusterStatusV1` | P0 | 返回集群状态 |

### 2.6 Hop ETL API (`src/api/hop.ts`)

**测试文件**: `src/api/hop.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `listWorkflows` | P0 | 返回工作流列表 |
| | P0 | 包含总数统计 |
| `getWorkflow` | P0 | 返回工作流详情 |
| | P0 | 不存在返回404 |
| `runWorkflow` | P0 | 成功启动 |
| | P1 | 返回execution_id |
| `getWorkflowStatus` | P0 | 返回执行状态 |
| | P0 | Finished状态 |
| | P0 | Error状态 |
| `stopWorkflow` | P0 | 成功停止 |
| `runWorkflowAndWait` | P0 | 成功完成返回状态 |
| | P1 | 超时抛错 |
| | P1 | 失败抛错 |

### 2.7 其他API模块

| 模块 | 文件 | P0用例数 | P1用例数 |
|------|------|----------|----------|
| NL2SQL | `nl2sql.ts` | 3 | 2 |
| DataHub | `datahub.ts` | 4 | 3 |
| Superset | `superset.ts` | 3 | 2 |
| DolphinScheduler | `dolphinscheduler.ts` | 4 | 2 |
| ShardingSphere | `shardingsphere.ts` | 5 | 3 |
| DataAPI | `data-api.ts` | 4 | 2 |
| Cleaning | `cleaning.ts` | 3 | 2 |
| MetadataSync | `metadata-sync.ts` | 3 | 2 |
| CubeStudio | `cubestudio.ts` | 4 | 3 |

---

## 3. 工具层测试计划

**覆盖率要求**: 90%

### 3.1 Token工具 (`src/utils/token.ts`)

**测试文件**: `src/utils/token.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `getToken` | P0 | 返回存储的token |
| | P0 | 无token返回null |
| `setToken` | P0 | 成功存储token |
| | P1 | 覆盖已有token |
| `removeToken` | P0 | 成功删除token |
| | P1 | 删除不存在不抛错 |
| `getTokenExpiration` | P0 | JWT解析成功 |
| | P0 | 无payload返回null |
| | P1 | 无效JWT格式 |
| `isTokenExpiringSoon` | P0 | token即将过期返回true |
| | P0 | token有效返回false |
| | P0 | 无token返回false |
| | P1 | 自定义阈值 |
| `isTokenExpired` | P0 | 已过期返回true |
| | P0 | 未过期返回false |
| | P1 | 无token视为过期 |

---

## 4. 状态管理测试计划

**覆盖率要求**: 85%

### 4.1 认证Store (`src/store/authStore.ts`)

**测试文件**: `src/store/authStore.test.ts`

| 测试用例 | 优先级 | 场景 |
|---------|-------|------|
| `initialState` | P0 | token从localStorage读取 |
| | P0 | isAuthenticated正确计算 |
| `login` | P0 | 成功登录更新状态 |
| | P0 | 失败登录不更新状态 |
| `logout` | P0 | 清除token和状态 |
| `checkAuth` | P0 | token有效保持登录 |
| | P0 | token过期退出登录 |
| `refreshToken` | P0 | 成功刷新更新token |
| | P1 | 刷新失败保持登录 |

---

## 5. 组件层测试计划

**覆盖率要求**: 75% (组件)

### 5.1 通用组件

| 组件 | 文件 | P0用例数 | 场景 |
|------|------|----------|------|
| MainLayout | `Layout/MainLayout.tsx` | 3 | 渲染、菜单导航、折叠展开 |
| Loading | `common/Loading.tsx` | 2 | 显示、隐藏 |
| ComingSoon | `common/ComingSoon.tsx` | 2 | 渲染、倒计时 |

### 5.2 页面组件测试策略

**由于页面组件数量众多(85+文件)，采用分层测试策略:**

#### 第一批: 核心业务页面 (P0)

| 页面 | 模块 | 测试重点 |
|------|------|---------|
| Login | 认证 | 表单提交、错误处理、跳转 |
| Workspace | Dashboard | Todo列表、状态切换 |
| Notifications | Dashboard | 列表渲染、标记已读 |
| Profile | Dashboard | 表单验证、密码修改 |
| SyncJobs | 数据汇聚 | 列表、启动/停止、状态显示 |
| Dashboards | 数据分析 | 列表、删除、编辑 |
| Alerts | 数据分析 | 规则列表、严重度标签 |

#### 第二批: 重要功能页面 (P1)

| 页面 | 模块 | 测试重点 |
|------|------|---------|
| CleaningRules | 数据开发 | 规则配置、预览 |
| QualityCheck | 数据开发 | 报告展示、导出 |
| OcrProcessing | 数据开发 | 任务创建、进度显示 |
| FillMissing | 数据开发 | 字段选择、策略配置 |
| Search | 数据资产 | 搜索、筛选、结果展示 |
| Permissions | 安全 | 权限树、角色分配 |
| MaskRules | 安全 | 规则列表、脱敏预览 |

#### 第三批: 辅助功能页面 (P2)

其余页面采用基本渲染测试和快照测试。

---

## 6. E2E测试计划

**已有Playwright E2E测试，需补充覆盖:**

### 6.1 现有E2E测试

| 测试文件 | 覆盖功能 | 状态 |
|---------|---------|------|
| smoke.spec.ts | 基础冒烟 | ✅ |
| auth.spec.ts | 认证流程 | ✅ |
| user-management.spec.ts | 用户管理 | ✅ |
| data-source.spec.ts | 数据源 | ✅ |
| sensitive-data.spec.ts | 敏感数据 | ✅ |
| nl2sql.spec.ts | NL2SQL | ✅ |

### 6.2 需补充的E2E测试

| 测试场景 | 优先级 | 描述 |
|---------|-------|------|
| 完整数据同步流程 | P0 | 创建→运行→验证结果 |
| 数据清洗流程 | P0 | 配置规则→执行→质量检查 |
| 仪表盘创建流程 | P1 | 创建仪表盘→添加图表→查看 |
| 权限分配流程 | P1 | 创建角色→分配权限→验证访问 |
| SSO登录流程 | P1 | 配置SSO→测试登录 |

---

## 7. 实施顺序

### 阶段一：基础设施 (Week 1)

```bash
# Day 1-2: 搭建测试环境
- 安装Vitest依赖
- 配置vitest.config.ts
- 创建测试工具和Mock
- 配置CI集成

# Day 3-5: 测试工具和类型
- src/test/setup.ts
- src/test/mocks/server.ts (MSW Mock)
- src/test/utils/testHelpers.ts
```

### 阶段二：API层测试 (Week 2-3)

```bash
# Week 2: 核心API
- src/api/types.test.ts
- src/api/utils.test.ts
- src/api/auth.test.ts
- src/api/audit.test.ts
- src/api/sensitive.test.ts

# Week 3: 业务API
- src/api/seatunnel.test.ts
- src/api/hop.test.ts
- src/api/nl2sql.test.ts
- src/api/datahub.test.ts
- src/api/cleaning.test.ts
```

### 阶段三：工具和状态 (Week 4)

```bash
# Week 4: 工具层和状态
- src/utils/token.test.ts
- src/store/authStore.test.ts
- src/utils/*.test.ts (新增工具)
```

### 阶段四：组件测试 (Week 5-7)

```bash
# Week 5: 核心页面组件
- src/pages/Login/index.test.tsx
- src/pages/Dashboard/*.test.tsx
- src/pages/Analysis/*.test.tsx

# Week 6: 业务页面组件
- src/pages/Collection/*.test.tsx
- src/pages/Development/*.test.tsx
- src/pages/Assets/*.test.tsx

# Week 7: 安全和运维页面
- src/pages/Security/*.test.tsx
- src/pages/Operations/*.test.tsx
- src/pages/Support/*.test.tsx
```

### 阶段五：E2E补充和覆盖率达标 (Week 8)

```bash
# Week 8: 收尾
- 补充E2E测试
- 覆盖率检查和补充
- CI/CD集成
- 文档完善
```

---

## 8. 测试模板

### 8.1 API测试模板

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { someFunction } from './api';
import { client } from './client';

// Mock axios client
vi.mock('./client');

describe('someFunction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return data on success', async () => {
    // Arrange
    const mockData = { id: 1, name: 'Test' };
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 20000, message: 'success', data: mockData }
    });

    // Act
    const result = await someFunction();

    // Assert
    expect(result).toEqual(mockData);
  });

  it('should throw error on failure', async () => {
    // Arrange
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 40001, message: 'Bad Request', data: null }
    });

    // Act & Assert
    await expect(someFunction()).rejects.toThrow('Bad Request');
  });
});
```

### 8.2 组件测试模板

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Title')).toBeInTheDocument();
  });

  it('should handle button click', async () => {
    const user = userEvent.setup();
    const mockFn = vi.fn();

    render(<MyComponent onSubmit={mockFn} />);

    await user.click(screen.getByRole('button'));

    expect(mockFn).toHaveBeenCalledTimes(1);
  });
});
```

---

## 9. 覆盖率目标

| 模块 | 语句 | 分支 | 函数 | 行 |
|------|------|------|------|-----|
| API层 | 100% | 100% | 100% | 100% |
| 工具层 | 90% | 85% | 90% | 90% |
| 状态层 | 85% | 80% | 85% | 85% |
| 组件层 | 75% | 70% | 75% | 75% |
| **总体** | **80%** | **80%** | **80%** | **80%** |

---

## 10. CI/CD集成

### 10.1 GitHub Actions配置

```yaml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v3
```

### 10.2 Pre-commit Hook

```json
{
  "husky": {
    "hooks": {
      "pre-commit": "npm run test:run"
    }
  }
}
```

---

**文档状态**: 📝 规划中
**下一步**: 开始执行阶段一 - 基础设施搭建
