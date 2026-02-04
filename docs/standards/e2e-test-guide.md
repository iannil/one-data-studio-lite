# E2E 测试执行指南

**最后更新**: 2026-01-31
**测试用例总数**: 1260+
**页面对象模型**: 12 个

---

## 一、测试覆盖概览

### 1.1 测试套件分类

| 分类 | 用例数 | 说明 |
|------|--------|------|
| 通用测试 (Common) | 46 | 冒烟、认证、导航 |
| 角色测试 (Roles) | 134 | 6 种角色的全生命周期测试 |
| 生命周期测试 (Lifecycle) | 64 | 9 个生命周期阶段 |
| 功能模块测试 (Features) | 495 | 24 个功能模块 |
| 集成测试 (Integration) | 64 | 跨模块集成场景 |
| API 测试 | 230 | 后端 API 直接测试 |
| 性能测试 (Performance) | 15 | 页面加载、Core Web Vitals |
| 视觉回归测试 (Visual) | 70 | UI 一致性验证 |
| 可访问性测试 (Accessibility) | 43 | WCAG 合规性 |
| 错误处理测试 (Error Handling) | 78 | 错误场景和恢复 |
| 冒烟测试 (Smoke) | 11 | 生产环境冒烟 |
| 企业版测试 (Enterprise) | 27 | 企业版部署验证 |

### 1.2 功能模块列表

- NL2SQL - 自然语言查询
- Audit Log - 审计日志
- User Management - 用户管理
- Sensitive Data - 敏感数据检测
- Data Catalog - 数据目录
- Data API - 数据 API
- Pipeline - 数据管道
- Data Cleaning - 数据清洗
- Settings - 系统设置
- Data Source - 数据源管理
- Workflow - 工作流编排
- Reporting - 报告生成
- Data Quality - 数据质量监控
- Data Governance - 数据治理与合规
- Collaboration - 协作功能
- Metadata - 元数据管理
- File Management - 文件管理
- Search - 全局搜索
- Dashboard Widgets - 仪表板组件
- Scheduling - 任务调度

---

## 二、快速开始

### 2.1 环境准备

```bash
# 确保前端和后端服务都在运行
cd /Users/iannil/Code/zproducts/one-data-studio-lite/web

# 启动前端 (新终端)
npm run dev

# 启动后端服务 (在服务目录)
# ...
```

### 2.2 运行测试

```bash
# 列出所有测试
npx playwright test --list

# 运行所有测试
npm run e2e

# UI 模式 (推荐新手)
npm run e2e:ui
```

---

## 三、测试命令详解

### 3.1 基础命令

| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `npm run e2e` | 运行所有测试 | CI/CD、完整验证 |
| `npm run e2e:ui` | UI 模式运行 | 开发调试、交互式测试 |
| `npm run e2e:debug` | 调试模式 | 逐步调试、断点查看 |
| `npm run e2e:headed` | 有头模式 | 可视化测试执行过程 |
| `npm run e2e:report` | 查看测试报告 | 测试完成后查看结果 |

### 3.2 按优先级运行

```bash
# P0 测试 - 冒烟、核心功能
npm run e2e:p0

# P1 测试 - 重要功能
npm run e2e:p1
```

### 3.3 按角色运行

```bash
# 超级管理员测试
npm run e2e:sup

# 管理员测试
npm run e2e:adm

# 数据科学家测试
npm run e2e:sci

# 数据分析师测试
npm run e2e:ana

# 查看者测试
npm run e2e:vw
```

### 3.4 按功能模块运行

```bash
# Pipeline 测试
npx playwright test --grep "@pipeline"

# Data Cleaning 测试
npx playwright test --grep "@cleaning"

# Workflow 测试
npx playwright test --grep "@workflow"

# Reporting 测试
npx playwright test --grep "@reporting"

# Scheduling 测试
npx playwright test --grep "@scheduling"

# Settings 测试
npx playwright test --grep "@settings"

# Data Quality 测试
npx playwright test --grep "@data-quality"

# Data Governance 测试
npx playwright test --grep "@governance"

# Collaboration 测试
npx playwright test --grep "@collaboration"

# Error Handling 测试
npx playwright test --grep "@error-handling"
```

### 3.5 按套件运行

```bash
# 冒烟测试
npx playwright test e2e/tests/smoke/

# 认证测试
npx playwright test e2e/tests/common/auth.spec.ts

# 生命周期测试
npx playwright test e2e/tests/lifecycle/

# 功能测试
npx playwright test e2e/tests/features/
```

---

## 四、调试技巧

### 4.1 UI 模式调试

```bash
npm run e2e:ui
```

**功能**:
- 可视化查看测试执行
- 时间旅行调试
- 查看网络请求
- 检查选择器

### 3.2 调试模式

```bash
npm run e2e:debug
```

**功能**:
- 自动打开 DevTools
- 支持断点
- 慢动作执行

### 3.3 有头模式

```bash
npm run e2e:headed
```

**用途**:
- 观看测试执行过程
- 截图测试

### 3.4 单独运行测试

```bash
# 运行特定测试文件
npx playwright test e2e/tests/common/auth.spec.ts

# 运行特定测试行
npx playwright test e2e/tests/common/auth.spec.ts:21

# 运行匹配标题的测试
npx playwright test --grep "登录"
```

---

## 四、测试报告

### 4.1 HTML 报告

```bash
# 自动在测试后打开
npm run e2e

# 手动打开
npm run e2e:report
```

### 4.2 JSON 报告

报告位置: `e2e/test-results/results.json`

```bash
# 合并多个 JSON 报告
npx playwright merge-reports test-results/results-*.json
```

### 4.3 JUnit 报告

报告位置: `e2e/test-results/junit.xml`

用于 CI/CD 集成。

---

## 五、常见问题

### 5.1 测试超时

**问题**: 测试执行超时

**解决**:
```bash
# 增加超时时间
npx playwright test --timeout=60000
```

### 5.2 测试不稳定

**问题**: 测试时而通过时而失败

**解决**:
```bash
# 启用重试
npx playwright test --retries=3
```

### 5.3 选择器找不到

**问题**: 元素定位失败

**解决**:
1. 检查前端是否已添加 `data-testid`
2. 使用 UI 模式检查选择器
3. 调整等待时间

### 5.4 后端服务未启动

**问题**: API 请求失败

**解决**:
```bash
# 检查服务状态
curl http://localhost:8010/health

# 启动对应服务
cd services/portal && python main.py
```

---

## 六、编写新测试

### 6.1 测试模板

```typescript
import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { loginAs } from '@utils/test-helpers';

test.describe('My Feature Tests', { tag: ['@p0'] }, () => {
  test('TC-MY-001: Basic test', async ({ page }) => {
    // 1. Setup
    await loginAs(page, 'admin');

    // 2. Execute
    await page.goto('/my-page');
    const element = page.locator('.my-element');

    // 3. Verify
    await expect(element).toBeVisible();
  });
});
```

### 6.2 页面对象模式

```typescript
// 1. 创建页面对象 (e2e/pages/my-page.page.ts)
export class MyPage extends BasePage {
  private readonly container = '[data-testid="my-page"]';

  async clickButton(): Promise<void> {
    await this.page.locator('button').click();
  }
}

// 2. 在测试中使用
import { MyPage } from '@pages/my-page.page';

test('my test', async ({ page }) => {
  const myPage = new MyPage(page);
  await myPage.goto();
  await myPage.clickButton();
});
```

### 6.3 使用测试辅助函数

```typescript
import {
  loginAs,
  waitForMessage,
  assertVisible,
  logout,
} from '@utils/test-helpers';

test('my test', async ({ page }) => {
  // 使用辅助函数
  await loginAs(page, 'admin');
  await assertVisible(page, '.dashboard');
  await logout(page);
});
```

---

## 七、持续集成

### 7.1 GitHub Actions

工作流文件: `.github/workflows/e2e.yml`

```bash
# 手动触发
gh workflow run e2e.yml

# 查看运行状态
gh run list --workflow=e2e.yml
```

### 7.2 本地预览 CI 环境

```bash
# 使用与 CI 相同的配置
npx playwright test --project=chromium
```

---

## 八、性能优化

### 8.1 并行执行

```bash
# 增加并行数
npx playwright test --workers=8
```

### 8.2 分片执行

```bash
# 分片执行 (CI)
npx playwright test --shard=1/4
npx playwright test --shard=2/4
npx playwright test --shard=3/4
npx playwright test --shard=4/4
```

### 8.3 只运行变更的测试

```bash
# 结合 git 使用
npx playwright test $(git diff --name-only | grep '\.spec\.ts')
```

---

## 九、维护指南

### 9.1 定期更新

| 频率 | 任务 |
|------|------|
| 每周 | 更新 Playwright 版本 |
| 每周 | 检查测试通过率 |
| 每月 | 审查测试覆盖 |
| 每季度 | 重构不稳定测试 |

### 9.2 测试健康度

```bash
# 查看测试统计
npx playwright test --reporter=list | grep -E "(passed|failed|skipped)"
```

### 9.3 清理旧报告

```bash
# 清理超过 7 天的报告
find e2e/playwright-report -type f -mtime +7 -delete
find e2e/test-results -type f -mtime +7 -delete
```

---

## 十、参考资源

- [Playwright 文档](https://playwright.dev)
- [页面对象模式](https://playwright.dev/docs/pom)
- [最佳实践](https://playwright.dev/docs/best-practices)
- [测试指南](https://playwright.dev/docs/test-guidelines)
