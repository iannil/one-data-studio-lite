/**
 * Alert Rules Configuration Page
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Switch,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Tooltip,
  Typography,
  message,
  Popconfirm,
  Drawer,
  Row,
  Col,
  Divider,
  Alert,
  List,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BellOutlined,
  TestOutlined,
  FireOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useMonitoringStore, AlertRule, AlertSeverity } from '@/stores/monitoring';
import { monitoringApi } from '@/services/api/monitoring';
import styles from './monitoring.module.scss';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface ConditionForm {
  metric_name: string;
  operator: string;
  threshold: number;
  labels?: Record<string, string>;
  duration_seconds: number;
}

interface RuleForm {
  name: string;
  description: string;
  severity: AlertSeverity;
  enabled: boolean;
  conditions: ConditionForm[];
  condition_operator: 'AND' | 'OR';
  notification_channels: string[];
  notification_recipients: string[];
  evaluation_interval_seconds: number;
  resolve_timeout_seconds?: number;
}

const AVAILABLE_METRICS = [
  { value: 'cpu_usage_percent', label: 'CPU Usage Percent', unit: '%' },
  { value: 'memory_usage_bytes', label: 'Memory Usage Bytes', unit: 'bytes' },
  { value: 'gpu_usage_percent', label: 'GPU Usage Percent', unit: '%' },
  { value: 'gpu_temperature_celsius', label: 'GPU Temperature', unit: '°C' },
  { value: 'db_query_duration_seconds', label: 'Database Query Duration', unit: 's' },
  { value: 'http_request_duration_seconds', label: 'HTTP Request Duration', unit: 's' },
  { value: 'etl_queue_size', label: 'ETL Queue Size', unit: 'items' },
  { value: 'celery_queue_length', label: 'Celery Queue Length', unit: 'items' },
];

const OPERATORS = [
  { value: 'gt', label: 'Greater Than (>)', symbol: '>' },
  { value: 'gte', label: 'Greater or Equal (>=)', symbol: '>=' },
  { value: 'lt', label: 'Less Than (<)', symbol: '<' },
  { value: 'lte', label: 'Less or Equal (<=)', symbol: '<=' },
  { value: 'eq', label: 'Equal (=)', symbol: '=' },
  { value: 'neq', label: 'Not Equal (!=)', symbol: '!=' },
];

const SEVERITY_CONFIG = {
  critical: { color: 'red', icon: <FireOutlined />, label: 'Critical' },
  error: { color: 'orange', icon: <WarningOutlined />, label: 'Error' },
  warning: { color: 'gold', icon: <InfoCircleOutlined />, label: 'Warning' },
  info: { color: 'blue', icon: <InfoCircleOutlined />, label: 'Info' },
};

const AlertRulesPage: React.FC = () => {
  const {
    rules,
    rulesLoading,
    rulesError,
    fetchRules,
    createRule,
    updateRule,
    deleteRule,
    toggleRule,
  } = useMonitoringStore();

  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [form] = Form.useForm<RuleForm>();
  const [testingRule, setTestingRule] = useState(false);
  const [testResult, setTestResult] = useState<{ triggered: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleAdd = () => {
    setEditingRule(null);
    form.resetFields({
      enabled: true,
      conditions: [
        {
          metric_name: 'cpu_usage_percent',
          operator: 'gt',
          threshold: 90,
          duration_seconds: 300,
        },
      ],
      condition_operator: 'AND',
      notification_channels: ['email'],
      evaluation_interval_seconds: 60,
    });
    setTestResult(null);
    setIsModalVisible(true);
  };

  const handleEdit = (rule: AlertRule) => {
    setEditingRule(rule);
    form.setFieldsValue({
      ...rule,
      notification_channels: rule.notification_channels,
      notification_recipients: rule.notification_recipients,
    });
    setTestResult(null);
    setIsModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteRule(id);
      message.success('Alert rule deleted successfully');
    } catch (error: any) {
      message.error(error.message || 'Failed to delete alert rule');
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await toggleRule(id, enabled);
      message.success(`Alert rule ${enabled ? 'enabled' : 'disabled'} successfully`);
    } catch (error: any) {
      message.error(error.message || 'Failed to toggle alert rule');
    }
  };

  const handleTest = async () => {
    try {
      setTestingRule(true);
      const values = await form.validateFields();
      const result = await monitoringApi.testRule(values);
      setTestResult(result.data);
      if (result.data.triggered) {
        message.warning('Rule conditions would trigger an alert');
      } else {
        message.success('Rule conditions would not trigger an alert');
      }
    } catch (error: any) {
      message.error('Failed to test rule');
    } finally {
      setTestingRule(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingRule) {
        await updateRule(editingRule.id, values);
        message.success('Alert rule updated successfully');
      } else {
        await createRule(values);
        message.success('Alert rule created successfully');
      }

      setIsModalVisible(false);
      form.resetFields();
      setTestResult(null);
    } catch (error: any) {
      message.error(error.message || 'Failed to save alert rule');
    }
  };

  const columns = [
    {
      title: 'Rule Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: AlertRule) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.description}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: AlertSeverity) => {
        const config = SEVERITY_CONFIG[severity];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        );
      },
    },
    {
      title: 'Conditions',
      key: 'conditions',
      width: 300,
      render: (_: any, record: AlertRule) => (
        <div>
          {record.conditions.map((condition, index) => {
            const metric = AVAILABLE_METRICS.find((m) => m.value === condition.metric_name);
            const op = OPERATORS.find((o) => o.value === condition.operator);
            return (
              <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                {metric?.label || condition.metric_name} {op?.symbol || condition.operator} {condition.threshold}
                {metric?.unit} for {condition.duration_seconds}s
              </Tag>
            );
          })}
          <Tag color={record.condition_operator === 'AND' ? 'cyan' : 'geekblue'}>
            {record.condition_operator}
          </Tag>
        </div>
      ),
    },
    {
      title: 'Notifications',
      key: 'notifications',
      width: 150,
      render: (_: any, record: AlertRule) => (
        <Space size={4} wrap>
          {record.notification_channels.map((channel) => (
            <Tag key={channel} icon={<BellOutlined />}>
              {channel}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      width: 100,
      render: (state: string) => {
        const colorMap: Record<string, string> = {
          firing: 'red',
          resolved: 'green',
          pending: 'orange',
          silenced: 'default',
        };
        return <Tag color={colorMap[state] || 'default'}>{state.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Status',
      key: 'enabled',
      width: 100,
      render: (_: any, record: AlertRule) => (
        <Switch
          checked={record.enabled}
          onChange={(checked) => handleToggle(record.id, checked)}
          checkedChildren="ON"
          unCheckedChildren="OFF"
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: AlertRule) => (
        <Space>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Are you sure you want to delete this alert rule?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.monitoringDashboard}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <Title level={2}>
            <BellOutlined className={styles.titleIcon} />
            Alert Rules
          </Title>
          <Text type="secondary">Configure monitoring and alerting rules</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          Create Rule
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          loading={rulesLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} rules`,
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
          setTestResult(null);
        }}
        width={800}
        okText={editingRule ? 'Update' : 'Create'}
        footer={[
          <Button key="test" icon={<TestOutlined />} loading={testingRule} onClick={handleTest}>
            Test Rule
          </Button>,
          <Button key="cancel" onClick={() => setIsModalVisible(false)}>
            Cancel
          </Button>,
          <Button key="submit" type="primary" onClick={handleSubmit}>
            {editingRule ? 'Update' : 'Create'}
          </Button>,
        ]}
      >
        {testResult && (
          <Alert
            message={testResult.triggered ? 'Rule Would Trigger Alert' : 'Rule Would Not Trigger'}
            description={testResult.message}
            type={testResult.triggered ? 'warning' : 'success'}
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          initialValues={{
            enabled: true,
            conditions: [
              {
                metric_name: 'cpu_usage_percent',
                operator: 'gt',
                threshold: 90,
                duration_seconds: 300,
              },
            ],
            condition_operator: 'AND',
            notification_channels: ['email'],
            evaluation_interval_seconds: 60,
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Rule Name"
                rules={[{ required: true, message: 'Please enter rule name' }]}
              >
                <Input placeholder="e.g., High CPU Usage" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="severity"
                label="Severity"
                rules={[{ required: true, message: 'Please select severity' }]}
              >
                <Select placeholder="Select severity">
                  {Object.entries(SEVERITY_CONFIG).map(([value, config]) => (
                    <Option key={value} value={value}>
                      <Space>
                        {config.icon}
                        {config.label}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: 'Please enter description' }]}
          >
            <TextArea
              rows={2}
              placeholder="Describe what this rule monitors and when it triggers"
            />
          </Form.Item>

          <Divider orientation="left">Conditions</Divider>

          <Form.List name="conditions">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Card
                    key={key}
                    size="small"
                    style={{ marginBottom: 16 }}
                    extra={
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => remove(name)}
                        disabled={fields.length === 1}
                      >
                        Remove
                      </Button>
                    }
                  >
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item
                          {...restField}
                          name={[name, 'metric_name']}
                          label="Metric"
                          rules={[{ required: true, message: 'Required' }]}
                        >
                          <Select placeholder="Select metric">
                            {AVAILABLE_METRICS.map((m) => (
                              <Option key={m.value} value={m.value}>
                                {m.label} ({m.unit})
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'operator']}
                          label="Operator"
                          rules={[{ required: true, message: 'Required' }]}
                        >
                          <Select placeholder="Select operator">
                            {OPERATORS.map((op) => (
                              <Option key={op.value} value={op.value}>
                                {op.label}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'threshold']}
                          label="Threshold"
                          rules={[{ required: true, message: 'Required' }]}
                        >
                          <InputNumber style={{ width: '100%' }} placeholder="Threshold" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item
                          {...restField}
                          name={[name, 'duration_seconds']}
                          label="Duration (s)"
                          rules={[{ required: true, message: 'Required' }]}
                        >
                          <InputNumber
                            style={{ width: '100%' }}
                            min={0}
                            placeholder="Seconds"
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button
                  type="dashed"
                  onClick={() => add()}
                  block
                  icon={<PlusOutlined />}
                >
                  Add Condition
                </Button>
              </>
            )}
          </Form.List>

          <Form.Item
            name="condition_operator"
            label="Condition Logic"
            rules={[{ required: true }]}
            style={{ marginTop: 16 }}
          >
            <Select>
              <Option value="AND">AND (All conditions must be met)</Option>
              <Option value="OR">OR (Any condition can trigger)</Option>
            </Select>
          </Form.Item>

          <Divider orientation="left">Notifications</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="notification_channels"
                label="Notification Channels"
                rules={[{ required: true, message: 'Select at least one channel' }]}
              >
                <Select mode="tags" placeholder="Select channels">
                  <Option value="email">Email</Option>
                  <Option value="slack">Slack</Option>
                  <Option value="webhook">Webhook</Option>
                  <Option value="pagerduty">PagerDuty</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="notification_recipients"
                label="Recipients"
                extra="Comma-separated emails or channels"
              >
                <Input placeholder="admin@example.com, #alerts" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Evaluation</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="evaluation_interval_seconds"
                label="Evaluation Interval"
                rules={[{ required: true }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={10}
                  suffix="seconds"
                  placeholder="60"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="resolve_timeout_seconds"
                label="Auto-resolve Timeout"
                extra="Optional: Auto-resolve after this duration"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  suffix="seconds"
                  placeholder="Leave empty for manual resolution"
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default AlertRulesPage;
