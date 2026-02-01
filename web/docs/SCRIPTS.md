# NPM Scripts Reference

本文档列出 `package.json` 中定义的所有可用脚本。

---

## 开发脚本

### `npm run dev`

启动 Vite 开发服务器。

```bash
npm run dev
```

- **端口**: 3000
- **热更新**: 启用
- **代理**: `/api` → `http://localhost:8010`

---

### `npm run build`

构建生产版本。

```bash
npm run build
```

- **输出目录**: `../services/portal/static/`
- **类型检查**: 运行 `tsc -b`
- **代码分割**: 启用

---

### `npm run preview`

预览构建产物。

```bash
npm run preview
```

---

## 代码质量脚本

### `npm run lint`

使用 ESLint 检查代码质量。

```bash
npm run lint
```

### `npm run lint:fix`

自动修复 ESLint 问题。

```bash
npm run lint:fix
```

---

## 单元测试脚本 (Vitest)

### `npm run test`

运行测试 (watch 模式)。

```bash
npm run test
```

### `npm run test:ui`

启动 Vitest UI 界面。

```bash
npm run test:ui
```

- **访问地址**: http://localhost:51204/__vitest__/

### `npm run test:run`

运行所有测试一次。

```bash
npm run test:run
```

### `npm run test:coverage`

生成测试覆盖率报告。

```bash
npm run test:coverage
```

- **输出目录**: `coverage/`

### `npm run test:watch`

监视模式运行测试。

```bash
npm run test:watch
```

---

## E2E 测试脚本 (Playwright)

### `npm run e2e`

运行所有 E2E 测试。

```bash
npm run e2e
```

- **配置文件**: `e2e/playwright.config.ts`
- **测试目录**: `e2e/tests/`
- **并行度**: 4 workers (本地), 2 workers (CI)

### `npm run e2e:ui`

启动 Playwright UI 模式。

```bash
npm run e2e:ui
```

- **访问地址**: 自动打开浏览器
- **功能**: 可视化选择和调试测试

### `npm run e2e:debug`

调试模式运行测试。

```bash
npm run e2e:debug
```

- **功能**: 慢动作执行，显示每个操作

### `npm run e2e:headed`

有头模式运行测试 (显示浏览器)。

```bash
npm run e2e:headed
```

### `npm run e2e:report`

查看测试报告。

```bash
npm run e2e:report
```

- **打开**: HTML 报告在浏览器中

### 优先级过滤

| 脚本 | 说明 |
|------|------|
| `npm run e2e:p0` | 只运行 P0 优先级测试 |
| `npm run e2e:p1` | 只运行 P1 优先级测试 |
| `npm run e2e:sup` | 只运行 Superset 相关测试 |
| `npm run e2e:adm` | 只运行管理功能测试 |
| `npm run e2e:sci` | 只运行数据科学功能测试 |
| `npm run e2e:ana` | 只运行分析功能测试 |
| `npm run e2e:vw` | 只运行可视化功能测试 |

### 特定测试套件

| 脚本 | 说明 |
|------|------|
| `npm run e2e:smoke` | 运行冒烟测试 |
| `npm run e2e:auth` | 运行认证测试 |

---

## 快捷命令参考

| 任务 | 命令 |
|------|------|
| 启动开发 | `npm run dev` |
| 构建生产 | `npm run build` |
| 检查代码 | `npm run lint` |
| 修复代码 | `npm run lint:fix` |
| 运行测试 | `npm run test:run` |
| 测试覆盖率 | `npm run test:coverage` |
| E2E 测试 | `npm run e2e` |
| E2E UI | `npm run e2e:ui` |
| P0 测试 | `npm run e2e:p0` |

---

## 环境变量

某些测试脚本可能需要以下环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `BASE_URL` | 应用基础 URL | `http://localhost:3000` |
| `CI` | CI 环境标识 | - |

示例：

```bash
BASE_URL=http://localhost:5173 npm run e2e
```
