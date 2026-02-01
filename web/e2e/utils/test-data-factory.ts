/**
 * Test Data Factory
 *
 * Factory functions for generating test data
 */

import { UserRole } from '@types/index';
import { randomString, randomEmail, randomUsername } from '@utils/helpers';

/**
 * Generate test user data
 */
export function generateTestUser(overrides?: {
  username?: string;
  password?: string;
  displayName?: string;
  email?: string;
  role?: UserRole;
  status?: 'active' | 'disabled' | 'pending';
}) {
  const username = overrides?.username || randomUsername();
  const timestamp = Date.now().toString(36);

  return {
    username,
    password: overrides?.password || `Test@${timestamp}123`,
    displayName: overrides?.displayName || `Test User ${timestamp}`,
    email: overrides?.email || randomEmail(),
    role: overrides?.role || UserRole.VIEWER,
    status: overrides?.status || 'active',
  };
}

/**
 * Generate test user for specific role
 */
export function generateUserForRole(role: UserRole): {
  username: string;
  password: string;
  displayName: string;
  email: string;
  role: UserRole;
  status: string;
} {
  const roleCode = {
    [UserRole.SUPER_ADMIN]: 'sup',
    [UserRole.ADMIN]: 'adm',
    [UserRole.DATA_SCIENTIST]: 'sci',
    [UserRole.ANALYST]: 'ana',
    [UserRole.VIEWER]: 'vw',
    [UserRole.SERVICE_ACCOUNT]: 'svc',
  }[role] || 'usr';

  const timestamp = Date.now().toString(36);

  return {
    username: `${roleCode}_${timestamp}`,
    password: `Test@${timestamp}123`,
    displayName: `Test ${role} ${timestamp}`,
    email: `test_${roleCode}_${timestamp}@example.com`,
    role,
    status: 'active',
  };
}

/**
 * Generate audit log entry
 */
export function generateAuditLog(overrides?: {
  userId?: string;
  username?: string;
  action?: string;
  resource?: string;
  result?: 'success' | 'failure';
  details?: Record<string, unknown>;
}) {
  const timestamp = Date.now();
  const actions = ['login', 'logout', 'create_user', 'delete_user', 'update_user', 'query_data'];
  const resources = ['/auth/login', '/operations/users', '/analysis/nl2sql'];

  return {
    id: `log_${randomString(12)}`,
    timestamp,
    userId: overrides?.userId || `user_${randomString(8)}`,
    username: overrides?.username || 'testuser',
    action: overrides?.action || actions[Math.floor(Math.random() * actions.length)],
    resource: overrides?.resource || resources[Math.floor(Math.random() * resources.length)],
    result: overrides?.result || 'success',
    details: overrides?.details || { ip: '127.0.0.1' },
  };
}

/**
 * Generate dataset metadata
 */
export function generateDataset(overrides?: {
  name?: string;
  description?: string;
  type?: string;
  rowCount?: number;
  schema?: Array<{ name: string; type: string; nullable: boolean }>;
  tags?: string[];
}) {
  const timestamp = Date.now().toString(36);
  const types = ['table', 'view', 'materialized_view'];

  return {
    name: overrides?.name || `test_dataset_${timestamp}`,
    description: overrides?.description || `Test dataset created at ${timestamp}`,
    type: overrides?.type || types[Math.floor(Math.random() * types.length)],
    rowCount: overrides?.rowCount || Math.floor(Math.random() * 10000),
    schema: overrides?.schema || [
      { name: 'id', type: 'INTEGER', nullable: false },
      { name: 'name', type: 'VARCHAR', nullable: false },
      { name: 'created_at', type: 'TIMESTAMP', nullable: false },
    ],
    tags: overrides?.tags || ['test', 'e2e'],
    createdAt: timestamp,
    owner: 'e2e_tester',
  };
}

/**
 * Generate API endpoint definition
 */
export function generateApiEndpoint(overrides?: {
  path?: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  description?: string;
  parameters?: Array<{ name: string; type: string; required: boolean }>;
}) {
  const timestamp = Date.now().toString(36);
  const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];

  return {
    path: overrides?.path || `/api/v1/test_${timestamp}`,
    method: overrides?.method || methods[Math.floor(Math.random() * methods.length)],
    description: overrides?.description || `Test endpoint ${timestamp}`,
    parameters: overrides?.parameters || [],
    responseSchema: {
      type: 'object',
      properties: {
        success: { type: 'boolean' },
        data: { type: 'object' },
      },
    },
  };
}

/**
 * Generate query for NL2SQL testing
 */
export function generateTestQuery(): {
  queries = [
    '显示所有用户',
    '查询销售额最高的产品',
    '统计每个部门的人数',
    '查找最近7天的订单',
    '显示库存不足的产品',
  ];

  return {
    natural: queries[Math.floor(Math.random() * queries.length)],
    expectedSql: 'SELECT * FROM test_table LIMIT 10',
  };
}

/**
 * Generate sensitive data scan result
 */
export function generateSensitiveScanResult(overrides?: {
  tableName?: string;
  totalRows?: number;
  sensitiveRows?: number;
  fields?: Array<{ field: string; type: string; count: number }>;
}) {
  const fieldTypes = [
    { field: 'email', type: 'email', count: Math.floor(Math.random() * 100) },
    { field: 'phone', type: 'phone', count: Math.floor(Math.random() * 50) },
    { field: 'id_card', type: 'id_card', count: Math.floor(Math.random() * 20) },
    { field: 'address', type: 'address', count: Math.floor(Math.random() * 30) },
  ];

  return {
    scanId: `scan_${Date.now().toString(36)}`,
    tableName: overrides?.tableName || 'test_table',
    status: 'completed',
    result: {
      totalRows: overrides?.totalRows || Math.floor(Math.random() * 1000),
      sensitiveRows: overrides?.sensitiveRows || Math.floor(Math.random() * 50),
      sensitiveFields: overrides?.fields || fieldTypes.slice(0, 2),
      confidence: 0.95,
    },
    startTime: Date.now() - 5000,
    endTime: Date.now(),
  };
}

/**
 * Generate notification data
 */
export function generateNotification(overrides?: {
  title?: string;
  message?: string;
  type?: 'info' | 'success' | 'warning' | 'error';
  read?: boolean;
}) {
  const types = ['info', 'success', 'warning', 'error'];

  return {
    id: `notif_${Date.now().toString(36)}`,
    title: overrides?.title || 'Test Notification',
    message: overrides?.message || 'This is a test notification',
    type: overrides?.type || types[Math.floor(Math.random() * types.length)],
    read: overrides?.read ?? false,
    createdAt: new Date().toISOString(),
    userId: 'test_user',
  };
}

/**
 * Generate dashboard stats
 */
export function generateDashboardStats() {
  return {
    totalUsers: Math.floor(Math.random() * 1000) + 100,
    activeUsers: Math.floor(Math.random() * 500) + 50,
    totalQueries: Math.floor(Math.random() * 10000) + 1000,
    todayQueries: Math.floor(Math.random() * 500) + 50,
    totalDatasets: Math.floor(Math.random() * 100) + 10,
    sensitiveDataFound: Math.floor(Math.random() * 100),
  };
}

/**
 * Generate pipeline data
 */
export function generatePipeline(overrides?: {
  name?: string;
  status?: 'idle' | 'running' | 'success' | 'failed';
  steps?: Array<{ name: string; status: string }>;
}) {
  const statuses = ['idle', 'running', 'success', 'failed'];
  const timestamp = Date.now().toString(36);

  return {
    id: `pipeline_${timestamp}`,
    name: overrides?.name || `Test Pipeline ${timestamp}`,
    status: overrides?.status || statuses[Math.floor(Math.random() * statuses.length)],
    steps: overrides?.steps || [
      { name: 'Extract', status: 'success' },
      { name: 'Transform', status: 'success' },
      { name: 'Load', status: 'pending' },
    ],
    createdAt: new Date().toISOString(),
    lastRun: new Date().toISOString(),
    schedule: '0 0 * * *',
  };
}

/**
 * Generate chart data
 */
export function generateChartData(dataType: 'line' | 'bar' | 'pie') {
  const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];

  if (dataType === 'line' || dataType === 'bar') {
    return {
      labels,
      datasets: [{
        label: 'Dataset 1',
        data: labels.map(() => Math.floor(Math.random() * 100)),
      }],
    };
  }

  // Pie chart
  return {
    labels: ['Category A', 'Category B', 'Category C'],
    datasets: [{
      data: [Math.floor(Math.random() * 100), Math.floor(Math.random() * 100), Math.floor(Math.random() * 100)],
    }],
  };
}

/**
 * Generate table data
 */
export function generateTableData(
  columns: string[],
  rowCount: number = 10
): Array<Record<string, string>> {
  const data: Array<Record<string, string>> = [];

  for (let i = 0; i < rowCount; i++) {
    const row: Record<string, string> = {};
    columns.forEach((col) => {
      row[col] = `value_${i}_${col.substring(0, 3)}`;
    });
    data.push(row);
  }

  return data;
}

/**
 * Generate form data
 */
export function generateFormData(fields: Record<string, string>) {
  const data: Record<string, string> = {};

  Object.entries(fields).forEach(([key, value]) => {
    if (value.includes('{{timestamp}}')) {
      data[key] = value.replace('{{timestamp}}', Date.now().toString());
    } else if (value.includes('{{random}}')) {
      data[key] = randomString(8);
    } else if (value.includes('{{email}}')) {
      data[key] = randomEmail();
    } else {
      data[key] = value;
    }
  });

  return data;
}

/**
 * Generate test scenario
 */
export function generateTestScenario(overrides?: {
  name?: string;
  description?: string;
  steps?: Array<{ action: string; expected: string }>;
  preconditions?: string[];
  postconditions?: string[];
}) {
  const timestamp = Date.now().toString(36);

  return {
    id: `scenario_${timestamp}`,
    name: overrides?.name || `Test Scenario ${timestamp}`,
    description: overrides?.description || 'Generated test scenario',
    steps: overrides?.steps || [
      { action: 'Navigate to page', expected: 'Page loads successfully' },
      { action: 'Perform action', expected: 'Action completes' },
      { action: 'Verify result', expected: 'Result is as expected' },
    ],
    preconditions: overrides?.preconditions || ['User is logged in'],
    postconditions: overrides?.postconditions || ['System is in valid state'],
    priority: 'P0',
    tags: ['generated', 'e2e'],
  };
}

/**
 * Data factory for bulk test data
 */
export class TestDataFactory {
  private timestamp: number;

  constructor() {
    this.timestamp = Date.now();
  }

  /**
   * Reset timestamp (for consistent data generation)
   */
  resetTimestamp(): void {
    this.timestamp = Date.now();
  }

  /**
   * Get current timestamp suffix
   */
  getSuffix(): string {
    return this.timestamp.toString(36);
  }

  /**
   * Generate multiple users
   */
  generateUsers(count: number, role?: UserRole): Array<ReturnType<typeof generateTestUser>> {
    const users: ReturnType<typeof generateTestUser>[] = [];

    for (let i = 0; i < count; i++) {
      this.timestamp += 1;
      users.push(generateTestUser({ role }));
    }

    return users;
  }

  /**
   * Generate multiple datasets
   */
  generateDatasets(count: number): Array<ReturnType<typeof generateDataset>> {
    const datasets: ReturnType<typeof generateDataset>[] = [];

    for (let i = 0; i < count; i++) {
      this.timestamp += 1;
      datasets.push(generateDataset());
    }

    return datasets;
  }

  /**
   * Generate audit log entries
   */
  generateAuditLogs(count: number): Array<ReturnType<typeof generateAuditLog>> {
    const logs: ReturnType<typeof generateAuditLog>[] = [];

    for (let i = 0; i < count; i++) {
      logs.push(generateAuditLog({
        timestamp: this.timestamp + i * 1000,
      }));
    }

    return logs;
  }

  /**
   * Generate notifications
   */
  generateNotifications(count: number): Array<ReturnType<typeof generateNotification>> {
    const notifications: ReturnType<typeof generateNotification>[] = [];

    for (let i = 0; i < count; i++) {
      notifications.push(generateNotification());
    }

    return notifications;
  }

  /**
   * Generate pipelines
   */
  generatePipelines(count: number): Array<ReturnType<typeof generatePipeline>> {
    const pipelines: ReturnType<typeof generatePipeline>[] = [];

    for (let i = 0; i < count; i++) {
      this.timestamp += 1;
      pipelines.push(generatePipeline());
    }

    return pipelines;
  }

  /**
   * Generate pagination data
   */
  generatePagination(total: number, pageSize: number = 10) {
    const totalPages = Math.ceil(total / pageSize);

    return {
      total,
      pageSize,
      totalPages,
      currentPage: 1,
      hasNext: totalPages > 1,
      hasPrev: false,
    };
  }

  /**
   * Generate filter options
   */
  generateFilterOptions(type: 'role' | 'status' | 'category') {
    const options = {
      role: [
        { value: 'super_admin', label: '超级管理员' },
        { value: 'admin', label: '管理员' },
        { value: 'data_scientist', label: '数据科学家' },
        { value: 'analyst', label: '数据分析师' },
        { value: 'viewer', label: '查看者' },
      ],
      status: [
        { value: 'active', label: '激活' },
        { value: 'disabled', label: '禁用' },
        { value: 'pending', label: '待定' },
      ],
      category: [
        { value: 'user', label: '用户数据' },
        { value: 'business', label: '业务数据' },
        { value: 'system', label: '系统数据' },
      ],
    };

    return options[type] || [];
  }

  /**
   * Generate search query variants
   */
  generateSearchVariations(baseTerm: string): string[] {
    return [
      baseTerm,
      baseTerm.toUpperCase(),
      baseTerm.toLowerCase(),
      baseTerm.split('').join(' '),
      `${baseTerm} test`,
    ];
  }

  /**
   * Generate date range test data
   */
  generateDateRange(days: number = 7): {
    startDate: string;
    endDate: string;
    formatted: { start: string; end: string };
  } {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);

    const formatDate = (date: Date) => date.toISOString().split('T')[0];

    return {
      startDate: formatDate(start),
      endDate: formatDate(end),
      formatted: {
        start: formatDate(start),
        end: formatDate(end),
      },
    };
  }

  /**
   * Generate test file name
   */
  generateFileName(prefix: string, extension: string = 'csv'): string {
    return `${prefix}_${this.getSuffix()}.${extension}`;
  }

  /**
   * Generate test email addresses
   */
  generateEmails(count: number): string[] {
    const emails: string[] = [];

    for (let i = 0; i < count; i++) {
      this.timestamp += 1;
      emails.push(`test_${this.getSuffix()}_${i}@example.com`);
    }

    return emails;
  }
}

/**
 * Global test data factory instance
 */
export const testDataFactory = new TestDataFactory();

// ============================================================
// Dictionary Data Generators
// ============================================================

/**
 * Generate data layer dictionary entry
 */
export function generateDataLayer(overrides?: {
  layerCode?: string;
  layerName?: string;
  layerLevel?: number;
}) {
  const layers = [
    { code: 'ODS', name: '操作数据层', level: 1 },
    { code: 'DWD', name: '明细数据层', level: 2 },
    { code: 'DWS', name: '汇总数据层', level: 3 },
    { code: 'ADS', name: '应用数据层', level: 4 },
    { code: 'DIM', name: '维度数据层', level: 5 },
  ];
  const layer = layers[Math.floor(Math.random() * layers.length)];

  return {
    layerCode: overrides?.layerCode || layer.code,
    layerName: overrides?.layerName || layer.name,
    layerLevel: overrides?.layerLevel ?? layer.level,
    color: '#1890ff',
  };
}

/**
 * Generate sync frequency dictionary entry
 */
export function generateSyncFrequency(overrides?: {
  frequencyCode?: string;
  frequencyName?: string;
  cronExpression?: string;
}) {
  const frequencies = [
    { code: 'REALTIME', name: '实时', cron: null },
    { code: 'HOURLY', name: '每小时', cron: '0 * * * *' },
    { code: 'DAILY', name: '每天', cron: '0 0 * * *' },
    { code: 'WEEKLY', name: '每周', cron: '0 0 * * 0' },
    { code: 'MONTHLY', name: '每月', cron: '0 0 1 * *' },
  ];
  const freq = frequencies[Math.floor(Math.random() * frequencies.length)];

  return {
    frequencyCode: overrides?.frequencyCode || freq.code,
    frequencyName: overrides?.frequencyName || freq.name,
    cronExpression: overrides?.cronExpression || freq.cron,
    intervalSeconds: freq.code === 'REALTIME' ? 60 : 3600,
  };
}

/**
 * Generate quality level dictionary entry
 */
export function generateQualityLevel(overrides?: {
  levelCode?: string;
  levelName?: string;
  scoreMin?: number;
  scoreMax?: number;
}) {
  const levels = [
    { code: 'EXCELLENT', name: '优秀', min: 95, max: 100 },
    { code: 'GOOD', name: '良好', min: 85, max: 94 },
    { code: 'FAIR', name: '一般', min: 70, max: 84 },
    { code: 'POOR', name: '较差', min: 60, max: 69 },
    { code: 'CRITICAL', name: '严重', min: 0, max: 59 },
  ];
  const level = levels[Math.floor(Math.random() * levels.length)];

  return {
    levelCode: overrides?.levelCode || level.code,
    levelName: overrides?.levelName || level.name,
    scoreMin: overrides?.scoreMin ?? level.min,
    scoreMax: overrides?.scoreMax ?? level.max,
    color: '#52c41a',
  };
}

/**
 * Generate sensitivity level dictionary entry
 */
export function generateSensitivityLevel(overrides?: {
  levelCode?: string;
  levelName?: string;
  levelValue?: number;
}) {
  const levels = [
    { code: 'PUBLIC', name: '公开', value: 0 },
    { code: 'INTERNAL', name: '内部', value: 1 },
    { code: 'SENSITIVE', name: '敏感', value: 2 },
    { code: 'CONFIDENTIAL', name: '机密', value: 3 },
    { code: 'RESTRICTED', name: '绝密', value: 4 },
  ];
  const level = levels[Math.floor(Math.random() * levels.length)];

  return {
    levelCode: overrides?.levelCode || level.code,
    levelName: overrides?.levelName || level.name,
    levelValue: overrides?.levelValue ?? level.value,
    color: '#1890ff',
  };
}

/**
 * Generate alert level dictionary entry
 */
export function generateAlertLevel(overrides?: {
  levelCode?: string;
  levelName?: string;
  levelValue?: number;
}) {
  const levels = [
    { code: 'INFO', name: '信息', value: 1 },
    { code: 'WARNING', name: '警告', value: 2 },
    { code: 'CRITICAL', name: '严重', value: 3 },
    { code: 'EMERGENCY', name: '紧急', value: 4 },
  ];
  const level = levels[Math.floor(Math.random() * levels.length)];

  return {
    levelCode: overrides?.levelCode || level.code,
    levelName: overrides?.levelName || level.name,
    levelValue: overrides?.levelValue ?? level.value,
    color: '#faad14',
  };
}

/**
 * Generate task status dictionary entry
 */
export function generateTaskStatus(overrides?: {
  statusCode?: string;
  statusName?: string;
  statusCategory?: string;
}) {
  const statuses = [
    { code: 'PENDING', name: '等待中', category: 'pending' },
    { code: 'RUNNING', name: '运行中', category: 'active' },
    { code: 'SUCCESS', name: '成功', category: 'terminated' },
    { code: 'FAILED', name: '失败', category: 'terminated' },
    { code: 'CANCELLED', name: '已取消', category: 'terminated' },
  ];
  const status = statuses[Math.floor(Math.random() * statuses.length)];

  return {
    statusCode: overrides?.statusCode || status.code,
    statusName: overrides?.statusName || status.name,
    statusCategory: overrides?.statusCategory || status.category,
    color: '#1890ff',
  };
}

// ============================================================
// Notification Template Generators
// ============================================================

/**
 * Generate notification template
 */
export function generateNotificationTemplate(overrides?: {
  templateCode?: string;
  templateName?: string;
  templateType?: string;
  templateCategory?: string;
}) {
  const types = ['task', 'quality', 'system', 'auth', 'data'];
  const categories = ['success', 'failure', 'warning', 'info'];
  const timestamp = Date.now().toString(36);

  return {
    templateCode: overrides?.templateCode || `TPL_${timestamp}`,
    templateName: overrides?.templateName || `Test Template ${timestamp}`,
    templateType: overrides?.templateType || types[Math.floor(Math.random() * types.length)],
    templateCategory: overrides?.templateCategory || categories[Math.floor(Math.random() * categories.length)],
    subjectTemplate: `[System] {{event_name}} occurred`,
    contentTemplate: 'Hello {{username}},\n\n{{event_details}}\n\nRegards,\nSystem',
    variables: ['event_name', 'event_details', 'username'],
    channels: ['email', 'web'],
    priority: 2,
  };
}

// ============================================================
// Workflow Template Generators
// ============================================================

/**
 * Generate workflow template
 */
export function generateWorkflowTemplate(overrides?: {
  templateCode?: string;
  templateName?: string;
  templateType?: string;
  templateCategory?: string;
}) {
  const types = ['sync', 'cleaning', 'fusion', 'quality'];
  const categories = ['standard', 'full', 'increment'];
  const timestamp = Date.now().toString(36);

  return {
    templateCode: overrides?.templateCode || `WFL_${timestamp}`,
    templateName: overrides?.templateName || `Test Workflow ${timestamp}`,
    templateType: overrides?.templateType || types[Math.floor(Math.random() * types.length)],
    templateCategory: overrides?.templateCategory || categories[Math.floor(Math.random() * categories.length)],
    description: 'Test workflow template',
    flowConfig: {
      version: '1.0',
      engine: 'seatunnel',
      parallelism: 2,
    },
    nodes: [
      {
        id: 'node_source',
        name: '数据源',
        type: 'source',
        position: { x: 100, y: 100 },
      },
      {
        id: 'node_target',
        name: '目标',
        type: 'sink',
        position: { x: 300, y: 100 },
      },
    ],
    edges: [
      { source: 'node_source', target: 'node_target' },
    ],
    estimatedDuration: 30,
    complexity: 'simple',
  };
}

/**
 * Generate workflow node
 */
export function generateWorkflowNode(overrides?: {
  nodeId?: string;
  nodeName?: string;
  nodeType?: string;
}) {
  const types = ['source', 'transform', 'sink', 'checkpoint', 'quality_check'];
  const timestamp = Date.now().toString(36);

  return {
    id: overrides?.nodeId || `node_${timestamp}`,
    name: overrides?.nodeName || `Node ${timestamp}`,
    type: overrides?.nodeType || types[Math.floor(Math.random() * types.length)],
    position: { x: Math.floor(Math.random() * 500), y: Math.floor(Math.random() * 300) },
  };
}

// ============================================================
// Dashboard Template Generators
// ============================================================

/**
 * Generate dashboard template
 */
export function generateDashboardTemplate(overrides?: {
  templateCode?: string;
  templateName?: string;
  templateCategory?: string;
}) {
  const categories = ['operation', 'governance', 'system'];
  const timestamp = Date.now().toString(36);

  return {
    templateCode: overrides?.templateCode || `DASH_${timestamp}`,
    templateName: overrides?.templateName || `Test Dashboard ${timestamp}`,
    templateCategory: overrides?.templateCategory || categories[Math.floor(Math.random() * categories.length)],
    description: 'Test dashboard template',
    layoutConfig: {
      type: 'grid',
      columns: 24,
      rows: 12,
      gap: [16, 16],
    },
    themeConfig: {
      theme: 'light',
      primaryColor: '#1890ff',
    },
    chartTemplates: [],
    refreshInterval: 300,
    isPublic: true,
  };
}

/**
 * Generate dashboard widget
 */
export function generateDashboardWidget(overrides?: {
  widgetCode?: string;
  widgetName?: string;
  widgetType?: string;
}) {
  const types = ['line', 'bar', 'pie', 'card', 'table', 'gauge', 'map'];
  const timestamp = Date.now().toString(36);

  return {
    widgetCode: overrides?.widgetCode || `WGT_${timestamp}`,
    widgetName: overrides?.widgetName || `Test Widget ${timestamp}`,
    widgetType: overrides?.widgetType || types[Math.floor(Math.random() * types.length)],
    category: 'chart',
    config: {},
    dataSource: { type: 'sql', query: 'SELECT * FROM test_table' },
    defaultSize: { w: 8, h: 4 },
    description: 'Test widget',
  };
}
