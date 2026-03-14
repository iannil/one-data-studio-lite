/**
 * Node Palette Component
 *
 * Categorized panel of draggable task types for workflow DAG creation.
 */

import React, { useMemo } from 'react';
import {
  Card,
  Collapse,
  Tag,
  Input,
  Space,
  Tooltip,
  Badge,
  Empty,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { TaskType, TaskCategory } from '@/types/workflow';
import { TASK_TYPE_CATEGORIES } from '@/types/workflow';

const { Panel } = Collapse;

interface NodePaletteProps {
  taskTypes: TaskType[];
  onTaskSelect?: (taskType: TaskType) => void;
  onTaskDragStart?: (taskType: TaskType, event: React.DragEvent) => void;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  expandedCategories?: string[];
  onCategoryChange?: (categories: string[]) => void;
}

const TASK_ICONS: Record<string, string> = {
  sql: '🔍',
  python: '🐍',
  shell: '⌨️',
  etl: '🔄',
  training: '🧠',
  inference: '🔮',
  evaluation: '📊',
  model_register: '📦',
  wait: '⏳',
  sensor: '📡',
  email: '📧',
  webhook: '🔗',
  slack: '💬',
  export: '📤',
  import: '📥',
  notebook: '📓',
};

const TASK_DESCRIPTIONS: Record<string, string> = {
  sql: 'Execute SQL queries on databases',
  python: 'Run Python code/scripts',
  shell: 'Execute shell/bash commands',
  etl: 'Run ETL pipeline transformations',
  training: 'Train machine learning models',
  inference: 'Run model inference/prediction',
  evaluation: 'Evaluate model performance',
  model_register: 'Register model to registry',
  wait: 'Wait for a specified time',
  sensor: 'Wait for a condition/event',
  email: 'Send email notifications',
  webhook: 'Call HTTP webhook endpoints',
  slack: 'Send Slack notifications',
  export: 'Export data to external systems',
  import: 'Import data from external systems',
  notebook: 'Execute Jupyter notebook',
};

const CATEGORY_COLORS: Record<string, string> = {
  Data: '#1890ff',
  Code: '#52c41a',
  'Machine Learning': '#722ed1',
  'Control Flow': '#faad14',
  Notification: '#13c2c2',
  'Data Transfer': '#fa541c',
  Notebook: '#eb2f96',
  Integration: '#8c8c8c',
};

export const NodePalette: React.FC<NodePaletteProps> = ({
  taskTypes,
  onTaskSelect,
  onTaskDragStart,
  searchValue = '',
  onSearchChange,
  expandedCategories = ['Data', 'Code'],
  onCategoryChange,
}) => {
  // Group task types by category
  const categorizedTasks = useMemo(() => {
    const groups: Record<string, TaskType[]> = {};
    taskTypes.forEach((task) => {
      if (!searchValue || task.name.toLowerCase().includes(searchValue.toLowerCase()) ||
          task.type.toLowerCase().includes(searchValue.toLowerCase())) {
        if (!groups[task.category]) {
          groups[task.category] = [];
        }
        groups[task.category].push(task);
      }
    });
    return groups;
  }, [taskTypes, searchValue]);

  const handleDragStart = (taskType: TaskType, event: React.DragEvent) => {
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('application/json', JSON.stringify(taskType));
    onTaskDragStart?.(taskType, event);
  };

  const handleClick = (taskType: TaskType) => {
    onTaskSelect?.(taskType);
  };

  const renderTaskCard = (taskType: TaskType) => (
    <Card
      key={taskType.type}
      size="small"
      draggable
      onDragStart={(e) => handleDragStart(taskType, e as any)}
      onClick={() => handleClick(taskType)}
      className="task-type-card"
      style={{
        marginBottom: 8,
        cursor: 'grab',
        borderLeft: `3px solid ${CATEGORY_COLORS[taskType] || '#d9d9d9'}`,
        transition: 'all 0.2s',
      }}
      hoverable
      bodyStyle={{ padding: '10px 12px' }}
    >
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Space size={8}>
          <span style={{ fontSize: '16px' }}>
            {TASK_ICONS[taskType.type] || '📄'}
          </span>
          <Tag
            color={CATEGORY_COLORS[taskType.category] || 'default'}
            style={{ margin: 0, fontSize: '10px' }}
          >
            {taskType.type}
          </Tag>
        </Space>
        <div style={{ fontSize: '13px', fontWeight: 500 }}>
          {taskType.name}
        </div>
        {taskType.description && (
          <div style={{ fontSize: '11px', color: '#999', lineHeight: 1.3 }}>
            {taskType.description}
          </div>
        )}
      </Space>
    </Card>
  );

  const renderCategoryPanel = (category: TaskCategory) => {
    const tasks = categorizedTasks[category];
    if (!tasks || tasks.length === 0) return null;

    return (
      <Panel
        key={category}
        header={
          <Space size={8}>
            <Badge
              count={tasks.length}
              size="small"
              style={{
                backgroundColor: CATEGORY_COLORS[category] || '#999',
              }}
            />
            <span style={{ fontWeight: 500 }}>{category}</span>
          </Space>
        }
        style={{
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: 4 }}>
          {tasks.map(renderTaskCard)}
        </div>
      </Panel>
    );
  };

  const hasTasks = Object.keys(categorizedTasks).length > 0;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Search */}
      <div style={{ marginBottom: 12 }}>
        <Input
          placeholder="Search task types..."
          prefix={<SearchOutlined />}
          value={searchValue}
          onChange={(e) => onSearchChange?.(e.target.value)}
          allowClear
        />
      </div>

      {/* Categories */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {hasTasks ? (
          <Collapse
            activeKey={expandedCategories}
            onChange={(keys) => onCategoryChange?.(keys as string[])}
            bordered={false}
            ghost
            style={{ backgroundColor: 'transparent' }}
          >
            {Object.keys(TASK_TYPE_CATEGORIES).map((category) =>
              renderCategoryPanel(category as TaskCategory)
            )}
          </Collapse>
        ) : (
          <Empty
            description="No matching task types"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 40 }}
          />
        )}
      </div>

      {/* Quick Add */}
      {!searchValue && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
          <div style={{ fontSize: '11px', color: '#999', marginBottom: 8 }}>
            Quick Actions
          </div>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            <Tooltip title="Add a SQL query task">
              <div
                className="quick-action-item"
                onClick={() => handleClick({
                  type: 'sql',
                  name: 'SQL Query',
                  category: 'Data',
                  description: TASK_DESCRIPTIONS.sql,
                } as TaskType)}
                style={{
                  padding: '6px 10px',
                  cursor: 'pointer',
                  borderRadius: 4,
                  fontSize: '12px',
                  transition: 'background 0.2s',
                }}
              >
                🔍 SQL Query
              </div>
            </Tooltip>
            <Tooltip title="Add a Python script task">
              <div
                className="quick-action-item"
                onClick={() => handleClick({
                  type: 'python',
                  name: 'Python Script',
                  category: 'Code',
                  description: TASK_DESCRIPTIONS.python,
                } as TaskType)}
                style={{
                  padding: '6px 10px',
                  cursor: 'pointer',
                  borderRadius: 4,
                  fontSize: '12px',
                  transition: 'background 0.2s',
                }}
              >
                🐍 Python Script
              </div>
            </Tooltip>
            <Tooltip title="Add a model training task">
              <div
                className="quick-action-item"
                onClick={() => handleClick({
                  type: 'training',
                  name: 'Model Training',
                  category: 'Machine Learning',
                  description: TASK_DESCRIPTIONS.training,
                } as TaskType)}
                style={{
                  padding: '6px 10px',
                  cursor: 'pointer',
                  borderRadius: 4,
                  fontSize: '12px',
                  transition: 'background 0.2s',
                }}
              >
                🧠 Train Model
              </div>
            </Tooltip>
          </Space>
        </div>
      )}

      <style jsx>{`
        .task-type-card:hover {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          transform: translateY(-1px);
        }
        .quick-action-item:hover {
          background: #f5f5f5;
        }
      `}</style>
    </div>
  );
};

export default NodePalette;

// Enhanced task type with descriptions
export const DEFAULT_TASK_TYPES: TaskType[] = [
  // Data tasks
  {
    type: 'sql',
    name: 'SQL Query',
    category: 'Data',
    description: TASK_DESCRIPTIONS.sql,
    icon: '🔍',
    color: '#1890ff',
  },
  {
    type: 'etl',
    name: 'ETL Pipeline',
    category: 'Data',
    description: TASK_DESCRIPTIONS.etl,
    icon: '🔄',
    color: '#1890ff',
  },
  // Code tasks
  {
    type: 'python',
    name: 'Python Script',
    category: 'Code',
    description: TASK_DESCRIPTIONS.python,
    icon: '🐍',
    color: '#52c41a',
  },
  {
    type: 'shell',
    name: 'Shell Command',
    category: 'Code',
    description: TASK_DESCRIPTIONS.shell,
    icon: '⌨️',
    color: '#52c41a',
  },
  // ML tasks
  {
    type: 'training',
    name: 'Model Training',
    category: 'Machine Learning',
    description: TASK_DESCRIPTIONS.training,
    icon: '🧠',
    color: '#722ed1',
  },
  {
    type: 'inference',
    name: 'Model Inference',
    category: 'Machine Learning',
    description: TASK_DESCRIPTIONS.inference,
    icon: '🔮',
    color: '#722ed1',
  },
  {
    type: 'evaluation',
    name: 'Model Evaluation',
    category: 'Machine Learning',
    description: TASK_DESCRIPTIONS.evaluation,
    icon: '📊',
    color: '#722ed1',
  },
  {
    type: 'model_register',
    name: 'Register Model',
    category: 'Machine Learning',
    description: TASK_DESCRIPTIONS.model_register,
    icon: '📦',
    color: '#722ed1',
  },
  // Control Flow
  {
    type: 'wait',
    name: 'Wait',
    category: 'Control Flow',
    description: TASK_DESCRIPTIONS.wait,
    icon: '⏳',
    color: '#faad14',
  },
  {
    type: 'sensor',
    name: 'Sensor',
    category: 'Control Flow',
    description: TASK_DESCRIPTIONS.sensor,
    icon: '📡',
    color: '#faad14',
  },
  // Notifications
  {
    type: 'email',
    name: 'Email',
    category: 'Notification',
    description: TASK_DESCRIPTIONS.email,
    icon: '📧',
    color: '#13c2c2',
  },
  {
    type: 'webhook',
    name: 'Webhook',
    category: 'Notification',
    description: TASK_DESCRIPTIONS.webhook,
    icon: '🔗',
    color: '#13c2c2',
  },
  {
    type: 'slack',
    name: 'Slack',
    category: 'Notification',
    description: TASK_DESCRIPTIONS.slack,
    icon: '💬',
    color: '#13c2c2',
  },
  // Data Transfer
  {
    type: 'export',
    name: 'Export Data',
    category: 'Data Transfer',
    description: TASK_DESCRIPTIONS.export,
    icon: '📤',
    color: '#fa541c',
  },
  {
    type: 'import',
    name: 'Import Data',
    category: 'Data Transfer',
    description: TASK_DESCRIPTIONS.import,
    icon: '📥',
    color: '#fa541c',
  },
  // Notebook
  {
    type: 'notebook',
    name: 'Notebook',
    category: 'Notebook',
    description: TASK_DESCRIPTIONS.notebook,
    icon: '📓',
    color: '#eb2f96',
  },
];
