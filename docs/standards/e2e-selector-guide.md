# E2E 测试选择器指南

**目的**: 统一测试选择器规范，提高测试稳定性

---

## 一、选择器优先级

### 1.1 优先级顺序

| 优先级 | 选择器类型 | 示例 | 稳定性 |
|--------|-----------|------|--------|
| 1 | `data-testid` | `[data-testid="submit-btn"]` | ⭐⭐⭐⭐⭐ |
| 2 | ARIA 属性 | `[role="button"]` | ⭐⭐⭐⭐ |
| 3 | ID | `#submit-button` | ⭐⭐⭐ |
| 4 | Class | `.ant-btn-primary` | ⭐⭐ |
| 5 | Text | `text="Submit"` | ⭐ |
| 6 | XPath | `//button[@type="submit"]` | ⭐ |

### 1.2 推荐做法

✅ **推荐**:
```typescript
// 使用 data-testid
page.locator('[data-testid="login-button"]')

// 使用 ARIA role
page.locator('[role="button"]:has-text("登录")')

// 使用 ID (如果稳定)
page.locator('#username-input')
```

❌ **避免**:
```typescript
// 使用动态生成的 class
page.locator('.ant-btn-primary.ant-btn-sm.u-12345')

// 使用深层嵌套
page.locator('div > div > div > button')

// 使用不稳定的 XPath
page.locator('//div[3]/div[2]/button')
```

---

## 二、data-testid 规范

### 2.1 命名规范

格式: `{feature}-{element}`

| 功能 | 元素 | data-testid |
|------|------|-------------|
| 登录页 | 用户名输入框 | `login-username-input` |
| 登录页 | 密码输入框 | `login-password-input` |
| 登录页 | 提交按钮 | `login-submit-button` |
| 仪表板 | 用户菜单 | `dashboard-user-menu` |
| 用户管理 | 创建按钮 | `user-create-button` |

### 2.2 前端实现

```tsx
// React 示例
<Button
  data-testid="login-submit-button"
  type="submit"
>
  登录
</Button>

<Input
  data-testid="login-username-input"
  name="username"
/>
```

### 2.3 常用 data-testid

#### 登录相关
```typescript
export const loginTestIds = {
  page: 'login-page',
  form: 'login-form',
  usernameInput: 'login-username-input',
  passwordInput: 'login-password-input',
  submitButton: 'login-submit-button',
  errorMessage: 'login-error-message',
} as const;
```

#### 通用组件
```typescript
export const commonTestIds = {
  button: (label: string) => `${label}-button`,
  input: (label: string) => `${label}-input`,
  select: (label: string) => `${label}-select`,
  modal: (title: string) => `${title}-modal`,
} as const;
```

---

## 三、Ant Design 选择器

### 3.1 通用选择器

```typescript
// 按钮
const button = '.ant-btn';
const primaryButton = '.ant-btn-primary';
const dangerButton = '.ant-btn-dangerous';

// 输入框
const input = '.ant-input';
const passwordInput = 'input[type="password"]';

// 表单
const form = '.ant-form';
const formItem = '.ant-form-item';

// 选择器
const select = '.ant-select';
const selectDropdown = '.ant-select-dropdown';
const selectOption = '.ant-select-dropdown-option';

// 表格
const table = '.ant-table';
const tableRow = '.ant-table-row';
const tableCell = '.ant-table-cell';
const tableBody = '.ant-table-tbody';

// 模态框
const modal = '.ant-modal';
const modalTitle = '.ant-modal-title';
const modalContent = '.ant-modal-body';
const modalClose = '.ant-modal-close';

// 消息
const message = '.ant-message';
const successMessage = '.ant-message-success';
const errorMessage = '.ant-message-error';

// 分页
const pagination = '.ant-pagination';
const nextButton = '.ant-pagination-next';
const prevButton = '.ant-pagination-prev';
```

### 3.2 组合选择器

```typescript
// 表格中的特定单元格
const cell = '.ant-table-tbody .ant-table-row:nth-child(2) .ant-table-cell:nth-child(1)';

// 表单中的特定输入框
const formInput = '.ant-form-item:has-text("用户名") .ant-input';

// 按钮组中的特定按钮
const groupButton = '.ant-space button:has-text("确定")';
```

---

## 四、动态元素处理

### 4.1 等待策略

```typescript
// 等待元素可见
await page.waitForSelector('.my-element', { state: 'visible' });

// 等待元素隐藏
await page.waitForSelector('.loading', { state: 'hidden' });

// 等待网络空闲
await page.waitForLoadState('networkidle');

// 等待特定请求
await page.waitForResponse(resp => resp.url().includes('/api/users'));
```

### 4.2 重试机制

```typescript
// 使用 test.step 自动重试
await test.step('click button', async () => {
  await page.click('.my-button');
});

// 使用自定义重试
async function clickWithRetry(selector: string, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await page.click(selector);
      return;
    } catch {
      await page.waitForTimeout(1000);
    }
  }
  throw new Error(`Failed to click ${selector}`);
}
```

---

## 五、页面对象选择器

### 5.1 集中管理

```typescript
// pages/base.page.ts
export class BasePage {
  protected readonly selectors = {
    // 通用
    loading: '.ant-spin, .loading',
    errorMessage: '.ant-message-error',
    successMessage: '.ant-message-success',

    // 表格
    table: '.ant-table',
    tableBody: '.ant-table-tbody',
    tableRow: '.ant-table-row',
    tableCell: '.ant-table-cell',

    // 表单
    form: '.ant-form',
    input: '.ant-input',
    button: '.ant-btn',
  };
}
```

### 5.2 动态生成

```typescript
// 根据文本生成选择器
function getButtonByText(text: string): string {
  return `.ant-btn:has-text("${text}")`;
}

// 根据行号生成选择器
function getTableCell(row: number, col: number): string {
  return `.ant-table-tbody .ant-table-row:nth-child(${row}) .ant-table-cell:nth-child(${col})`;
}
```

---

## 六、调试选择器

### 6.1 UI 模式

```bash
npm run e2e:ui
```

在 UI 模式中:
1. 点击测试名称
2. 点击 "Pick locator"
3. 点击页面元素
4. 复制生成的选择器

### 6.2 控制台调试

```typescript
// 在测试中暂停
await page.pause();

// 在控制台中
$$('.ant-button')  // 查看所有按钮
$$('#submit-btn')  // 查看特定元素
```

### 6.3 Chrome DevTools

```typescript
// 在测试中添加断点
await page.pause();

// 或使用
debugger;
await page.click('.button');
```

---

## 七、最佳实践

### 7.1 选择器编写

```typescript
// ✅ 好: 使用 data-testid
page.locator('[data-testid="submit-button"]')

// ✅ 好: 使用 role
page.locator('button[name="submit"]')

// ✅ 好: 使用可读的组合
page.locator('.user-form').locator('#submit-button')

// ❌ 差: 使用深层嵌套
page.locator('div > div > div > button')

// ❌ 差: 使用动态 class
page.locator('.ant-btn-primary.u-12345')
```

### 7.2 等待策略

```typescript
// ✅ 好: 使用明确的等待
await page.waitForSelector('[data-testid="result"]', { state: 'visible' });

// ❌ 差: 使用固定延迟
await page.waitForTimeout(5000);

// ✅ 好: 等待特定条件
await page.waitForURL(/\/dashboard\/.*/);
await page.waitForResponse(resp => resp.status() === 200);
```

### 7.3 页面对象模式

```typescript
// ✅ 好: 封装选择器
class LoginPage {
  private readonly usernameInput = '[data-testid="username-input"]';
  private readonly passwordInput = '[data-testid="password-input"]';

  async login(username: string, password: string) {
    await this.page.fill(this.usernameInput, username);
    await this.page.fill(this.passwordInput, password);
  }
}

// ❌ 差: 在测试中直接使用选择器
test('login', async ({ page }) => {
  await page.fill('.ant-input:nth-child(1)', 'admin');
  await page.fill('.ant-input:nth-child(2)', 'password');
});
```

---

## 八、检查清单

在提交新测试前，确保:

- [ ] 使用 `data-testid` 而非 CSS 选择器
- [ ] 选择器具有描述性名称
- [ ] 避免使用动态生成的 class
- [ ] 使用页面对象模式封装选择器
- [ ] 添加适当的等待策略
- [ ] 在 UI 模式下验证选择器
- [ ] 更新选择器常量文件
