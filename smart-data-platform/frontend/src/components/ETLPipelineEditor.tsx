'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Tooltip,
  Drawer,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Divider,
  Typography,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SettingOutlined,
  ArrowRightOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

interface ETLStep {
  id: string;
  name: string;
  step_type: string;
  config: Record<string, unknown>;
  order: number;
  is_enabled: boolean;
}

interface ETLPipelineEditorProps {
  steps: ETLStep[];
  onChange: (steps: ETLStep[]) => void;
  sourceColumns?: string[];
}

const STEP_CONFIGS: Record<string, {
  label: string;
  icon: string;
  category: string;
  color: string;
  fields: Array<{
    name: string;
    label: string;
    type: 'text' | 'select' | 'number' | 'switch' | 'json' | 'columns';
    options?: Array<{ value: string; label: string }>;
    defaultValue?: unknown;
    required?: boolean;
    tooltip?: string;
  }>;
}> = {
  filter: {
    label: '过滤',
    icon: '🔍',
    category: 'transform',
    color: 'blue',
    fields: [
      { name: 'column', label: '列名', type: 'text', required: true },
      {
        name: 'operator',
        label: '操作符',
        type: 'select',
        options: [
          { value: 'eq', label: '等于 (=)' },
          { value: 'ne', label: '不等于 (!=)' },
          { value: 'gt', label: '大于 (>)' },
          { value: 'gte', label: '大于等于 (>=)' },
          { value: 'lt', label: '小于 (<)' },
          { value: 'lte', label: '小于等于 (<=)' },
          { value: 'contains', label: '包含' },
          { value: 'is_null', label: '为空' },
          { value: 'is_not_null', label: '不为空' },
        ],
        required: true,
      },
      { name: 'value', label: '值', type: 'text' },
    ],
  },
  deduplicate: {
    label: '去重',
    icon: '🔄',
    category: 'transform',
    color: 'cyan',
    fields: [
      { name: 'columns', label: '去重列 (逗号分隔)', type: 'text', tooltip: '留空则对所有列去重' },
      {
        name: 'keep',
        label: '保留',
        type: 'select',
        options: [
          { value: 'first', label: '第一条' },
          { value: 'last', label: '最后一条' },
        ],
        defaultValue: 'first',
      },
    ],
  },
  fill_missing: {
    label: '填充缺失值',
    icon: '📝',
    category: 'transform',
    color: 'orange',
    fields: [
      { name: 'column', label: '列名', type: 'text', required: true },
      {
        name: 'strategy',
        label: '填充策略',
        type: 'select',
        options: [
          { value: 'value', label: '固定值' },
          { value: 'mean', label: '均值' },
          { value: 'median', label: '中位数' },
          { value: 'mode', label: '众数' },
          { value: 'forward_fill', label: '向前填充' },
          { value: 'backward_fill', label: '向后填充' },
        ],
        required: true,
      },
      { name: 'value', label: '填充值', type: 'text', tooltip: '策略为固定值时必填' },
    ],
  },
  ai_fill_missing: {
    label: 'AI智能填充',
    icon: '🤖',
    category: 'ai',
    color: 'purple',
    fields: [
      { name: 'target_column', label: '目标列', type: 'text', required: true },
      { name: 'feature_columns', label: '特征列 (逗号分隔)', type: 'text', required: true, tooltip: '用于预测的特征列' },
      {
        name: 'algorithm',
        label: '算法',
        type: 'select',
        options: [
          { value: 'knn', label: 'KNN (K近邻)' },
          { value: 'random_forest', label: '随机森林' },
          { value: 'linear_regression', label: '线性回归' },
          { value: 'gradient_boosting', label: '梯度提升' },
        ],
        defaultValue: 'knn',
      },
      { name: 'n_neighbors', label: 'K值 (KNN)', type: 'number', defaultValue: 5 },
      { name: 'n_estimators', label: '树数量', type: 'number', defaultValue: 100 },
      {
        name: 'fallback_strategy',
        label: '回退策略',
        type: 'select',
        options: [
          { value: 'mean', label: '均值' },
          { value: 'median', label: '中位数' },
          { value: 'mode', label: '众数' },
        ],
        defaultValue: 'mean',
      },
    ],
  },
  mask: {
    label: '数据脱敏',
    icon: '🔒',
    category: 'security',
    color: 'red',
    fields: [
      { name: 'column', label: '列名', type: 'text', required: true },
      {
        name: 'strategy',
        label: '脱敏策略',
        type: 'select',
        options: [
          { value: 'partial', label: '部分遮盖' },
          { value: 'hash', label: '哈希' },
          { value: 'replace', label: '替换' },
        ],
        required: true,
      },
      { name: 'start', label: '保留前N位', type: 'number', defaultValue: 3 },
      { name: 'end', label: '保留后N位', type: 'number', defaultValue: 4 },
      { name: 'mask_char', label: '遮盖字符', type: 'text', defaultValue: '*' },
    ],
  },
  auto_mask: {
    label: 'AI自动脱敏',
    icon: '🛡️',
    category: 'ai',
    color: 'volcano',
    fields: [
      {
        name: 'sensitivity_threshold',
        label: '敏感度阈值',
        type: 'select',
        options: [
          { value: 'low', label: '低' },
          { value: 'medium', label: '中' },
          { value: 'high', label: '高' },
          { value: 'critical', label: '关键' },
        ],
        defaultValue: 'medium',
      },
      {
        name: 'default_strategy',
        label: '默认脱敏策略',
        type: 'select',
        options: [
          { value: 'partial', label: '部分遮盖' },
          { value: 'hash', label: '哈希' },
          { value: 'replace', label: '替换' },
        ],
        defaultValue: 'partial',
      },
      { name: 'skip_columns', label: '跳过列 (逗号分隔)', type: 'text', tooltip: '不进行脱敏的列' },
      { name: 'mask_char', label: '遮盖字符', type: 'text', defaultValue: '*' },
    ],
  },
  rename: {
    label: '重命名',
    icon: '✏️',
    category: 'transform',
    color: 'geekblue',
    fields: [
      { name: 'old_name', label: '原列名', type: 'text', required: true },
      { name: 'new_name', label: '新列名', type: 'text', required: true },
    ],
  },
  type_cast: {
    label: '类型转换',
    icon: '🔄',
    category: 'transform',
    color: 'lime',
    fields: [
      { name: 'column', label: '列名', type: 'text', required: true },
      {
        name: 'target_type',
        label: '目标类型',
        type: 'select',
        options: [
          { value: 'int', label: '整数' },
          { value: 'float', label: '浮点数' },
          { value: 'str', label: '字符串' },
          { value: 'datetime', label: '日期时间' },
          { value: 'bool', label: '布尔' },
        ],
        required: true,
      },
      { name: 'format', label: '日期格式', type: 'text', tooltip: '类型为日期时间时使用' },
    ],
  },
  calculate: {
    label: '计算字段',
    icon: '🧮',
    category: 'transform',
    color: 'gold',
    fields: [
      { name: 'target_column', label: '新列名', type: 'text', required: true },
      {
        name: 'type',
        label: '计算类型',
        type: 'select',
        options: [
          { value: 'formula', label: '公式' },
          { value: 'concat', label: '字符串连接' },
          { value: 'date_diff', label: '日期差' },
        ],
        defaultValue: 'formula',
      },
      { name: 'expression', label: '表达式', type: 'text', tooltip: '例如: col1 + col2 * 0.1' },
      { name: 'columns', label: '连接列 (逗号分隔)', type: 'text', tooltip: '字符串连接时使用' },
      { name: 'separator', label: '分隔符', type: 'text', defaultValue: '' },
    ],
  },
  aggregate: {
    label: '聚合',
    icon: '📊',
    category: 'transform',
    color: 'magenta',
    fields: [
      { name: 'group_by', label: '分组列 (逗号分隔)', type: 'text', required: true },
      { name: 'agg_column', label: '聚合列', type: 'text', required: true },
      {
        name: 'agg_func',
        label: '聚合函数',
        type: 'select',
        options: [
          { value: 'sum', label: '求和' },
          { value: 'mean', label: '平均' },
          { value: 'count', label: '计数' },
          { value: 'min', label: '最小值' },
          { value: 'max', label: '最大值' },
          { value: 'std', label: '标准差' },
        ],
        required: true,
      },
    ],
  },
  sort: {
    label: '排序',
    icon: '📋',
    category: 'transform',
    color: 'cyan',
    fields: [
      { name: 'columns', label: '排序列 (逗号分隔)', type: 'text', required: true },
      { name: 'ascending', label: '升序', type: 'switch', defaultValue: true },
    ],
  },
  drop_columns: {
    label: '删除列',
    icon: '❌',
    category: 'transform',
    color: 'default',
    fields: [
      { name: 'columns', label: '删除列 (逗号分隔)', type: 'text', required: true },
    ],
  },
  select_columns: {
    label: '选择列',
    icon: '✅',
    category: 'transform',
    color: 'green',
    fields: [
      { name: 'columns', label: '保留列 (逗号分隔)', type: 'text', required: true },
    ],
  },
  join: {
    label: '关联合并',
    icon: '🔗',
    category: 'transform',
    color: 'purple',
    fields: [
      { name: 'source_id', label: '数据源ID', type: 'text', required: true },
      { name: 'join_table', label: '关联表名', type: 'text', required: true },
      {
        name: 'join_type',
        label: '关联类型',
        type: 'select',
        options: [
          { value: 'left', label: '左连接' },
          { value: 'right', label: '右连接' },
          { value: 'inner', label: '内连接' },
          { value: 'outer', label: '外连接' },
        ],
        defaultValue: 'left',
      },
      { name: 'on', label: '关联键 (逗号分隔)', type: 'text', required: true },
    ],
  },
};

const generateId = () => `step_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export default function ETLPipelineEditor({
  steps,
  onChange,
  sourceColumns = [],
}: ETLPipelineEditorProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingStep, setEditingStep] = useState<ETLStep | null>(null);
  const [form] = Form.useForm();

  const handleAddStep = (stepType: string) => {
    const config = STEP_CONFIGS[stepType];
    if (!config) return;

    const newStep: ETLStep = {
      id: generateId(),
      name: `${config.label} ${steps.length + 1}`,
      step_type: stepType,
      config: {},
      order: steps.length,
      is_enabled: true,
    };

    onChange([...steps, newStep]);
    handleEditStep(newStep);
  };

  const handleEditStep = (step: ETLStep) => {
    setEditingStep(step);
    form.setFieldsValue({
      name: step.name,
      is_enabled: step.is_enabled,
      ...step.config,
    });
    setDrawerOpen(true);
  };

  const handleDeleteStep = (stepId: string) => {
    const newSteps = steps
      .filter((s) => s.id !== stepId)
      .map((s, idx) => ({ ...s, order: idx }));
    onChange(newSteps);
  };

  const handleMoveStep = (stepId: string, direction: 'up' | 'down') => {
    const idx = steps.findIndex((s) => s.id === stepId);
    if (idx === -1) return;

    const newIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= steps.length) return;

    const newSteps = [...steps];
    const temp = newSteps[idx];
    newSteps[idx] = newSteps[newIdx];
    newSteps[newIdx] = temp;

    onChange(newSteps.map((s, i) => ({ ...s, order: i })));
  };

  const handleSaveStep = (values: Record<string, unknown>) => {
    if (!editingStep) return;

    const { name, is_enabled, ...config } = values;

    const processedConfig = Object.entries(config).reduce((acc, [key, value]) => {
      if (typeof value === 'string' && value.includes(',') && !['expression', 'value'].includes(key)) {
        acc[key] = value.split(',').map((v) => v.trim()).filter(Boolean);
      } else if (value !== undefined && value !== '') {
        acc[key] = value;
      }
      return acc;
    }, {} as Record<string, unknown>);

    const updatedStep: ETLStep = {
      ...editingStep,
      name: name as string,
      is_enabled: is_enabled as boolean,
      config: processedConfig,
    };

    const newSteps = steps.map((s) => (s.id === editingStep.id ? updatedStep : s));
    onChange(newSteps);
    setDrawerOpen(false);
    setEditingStep(null);
  };

  const stepTypeGroups = useMemo(() => {
    const groups: Record<string, Array<{ type: string; config: typeof STEP_CONFIGS[string] }>> = {
      transform: [],
      ai: [],
      security: [],
    };

    Object.entries(STEP_CONFIGS).forEach(([type, config]) => {
      groups[config.category].push({ type, config });
    });

    return groups;
  }, []);

  return (
    <div style={{ display: 'flex', gap: 16 }}>
      {/* Step Palette */}
      <Card
        title="步骤类型"
        size="small"
        style={{ width: 200, flexShrink: 0 }}
        bodyStyle={{ padding: 8 }}
      >
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>数据转换</Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
            {stepTypeGroups.transform.map(({ type, config }) => (
              <Tooltip key={type} title={config.label}>
                <Button
                  size="small"
                  onClick={() => handleAddStep(type)}
                  style={{ padding: '0 8px' }}
                >
                  {config.icon}
                </Button>
              </Tooltip>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>AI增强</Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
            {stepTypeGroups.ai.map(({ type, config }) => (
              <Tooltip key={type} title={config.label}>
                <Button
                  size="small"
                  type="primary"
                  ghost
                  onClick={() => handleAddStep(type)}
                  style={{ padding: '0 8px' }}
                >
                  {config.icon}
                </Button>
              </Tooltip>
            ))}
          </div>
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>数据安全</Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
            {stepTypeGroups.security.map(({ type, config }) => (
              <Tooltip key={type} title={config.label}>
                <Button
                  size="small"
                  danger
                  onClick={() => handleAddStep(type)}
                  style={{ padding: '0 8px' }}
                >
                  {config.icon}
                </Button>
              </Tooltip>
            ))}
          </div>
        </div>
      </Card>

      {/* Pipeline Canvas */}
      <Card
        title="管道步骤"
        size="small"
        style={{ flex: 1, minHeight: 300 }}
        bodyStyle={{ padding: 12 }}
      >
        {steps.length === 0 ? (
          <Alert
            message="开始构建管道"
            description="从左侧面板点击添加步骤，或拖拽步骤到此处"
            type="info"
            showIcon
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {/* Source Node */}
            <div
              style={{
                padding: '8px 12px',
                background: '#f0f5ff',
                borderRadius: 4,
                border: '1px solid #adc6ff',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span>📥</span>
              <Text strong>数据源</Text>
            </div>

            {/* Steps */}
            {steps.map((step, idx) => {
              const config = STEP_CONFIGS[step.step_type];
              return (
                <div key={step.id}>
                  <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
                    <ArrowDownOutlined style={{ color: '#bfbfbf' }} />
                  </div>
                  <div
                    style={{
                      padding: '8px 12px',
                      background: step.is_enabled ? '#fff' : '#f5f5f5',
                      borderRadius: 4,
                      border: `1px solid ${step.is_enabled ? '#d9d9d9' : '#f0f0f0'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      opacity: step.is_enabled ? 1 : 0.6,
                    }}
                  >
                    <Space>
                      <span>{config?.icon || '📦'}</span>
                      <div>
                        <Text strong={step.is_enabled}>{step.name}</Text>
                        <br />
                        <Tag color={config?.color} style={{ fontSize: 12 }}>
                          {config?.label || step.step_type}
                        </Tag>
                      </div>
                    </Space>
                    <Space size={4}>
                      <Tooltip title="上移">
                        <Button
                          type="text"
                          size="small"
                          disabled={idx === 0}
                          onClick={() => handleMoveStep(step.id, 'up')}
                        >
                          ↑
                        </Button>
                      </Tooltip>
                      <Tooltip title="下移">
                        <Button
                          type="text"
                          size="small"
                          disabled={idx === steps.length - 1}
                          onClick={() => handleMoveStep(step.id, 'down')}
                        >
                          ↓
                        </Button>
                      </Tooltip>
                      <Tooltip title="配置">
                        <Button
                          type="text"
                          size="small"
                          icon={<SettingOutlined />}
                          onClick={() => handleEditStep(step)}
                        />
                      </Tooltip>
                      <Tooltip title="删除">
                        <Button
                          type="text"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleDeleteStep(step.id)}
                        />
                      </Tooltip>
                    </Space>
                  </div>
                </div>
              );
            })}

            {/* Target Node */}
            <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
              <ArrowDownOutlined style={{ color: '#bfbfbf' }} />
            </div>
            <div
              style={{
                padding: '8px 12px',
                background: '#f6ffed',
                borderRadius: 4,
                border: '1px solid #b7eb8f',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span>📤</span>
              <Text strong>目标表</Text>
            </div>
          </div>
        )}
      </Card>

      {/* Step Configuration Drawer */}
      <Drawer
        title={editingStep ? `配置: ${editingStep.name}` : '配置步骤'}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setEditingStep(null);
        }}
        width={400}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => form.submit()}>
              保存
            </Button>
          </Space>
        }
      >
        {editingStep && (
          <Form form={form} layout="vertical" onFinish={handleSaveStep}>
            <Form.Item name="name" label="步骤名称" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="is_enabled" label="启用" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
            <Divider />

            {STEP_CONFIGS[editingStep.step_type]?.fields.map((field) => (
              <Form.Item
                key={field.name}
                name={field.name}
                label={field.label}
                rules={field.required ? [{ required: true }] : []}
                tooltip={field.tooltip}
                initialValue={field.defaultValue}
              >
                {field.type === 'text' && <Input />}
                {field.type === 'number' && <InputNumber style={{ width: '100%' }} />}
                {field.type === 'switch' && <Switch />}
                {field.type === 'select' && (
                  <Select options={field.options} />
                )}
                {field.type === 'json' && <Input.TextArea rows={4} />}
                {field.type === 'columns' && (
                  <Select
                    mode="multiple"
                    options={sourceColumns.map((c) => ({ value: c, label: c }))}
                    placeholder="选择列"
                  />
                )}
              </Form.Item>
            ))}
          </Form>
        )}
      </Drawer>
    </div>
  );
}
