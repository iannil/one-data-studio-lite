import React, { useEffect, useState } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Form,
  Input,
  Select,
  message,
  Typography,
  Space,
  Switch,
  Alert,
  Modal,
  Tabs,
  InputNumber,
  Row,
  Col,
} from 'antd';
import {
  BellOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
type AlertStatus = 'active' | 'paused' | 'triggered';
type NotifyChannel = 'email' | 'sms' | 'webhook' | 'dingtalk';
type MetricType = 'data_quality' | 'task_failure' | 'data_volume' | 'latency' | 'custom';

interface AlertRule {
  id: string;
  name: string;
  description?: string;
  metricType: MetricType;
  severity: AlertSeverity;
  status: AlertStatus;
  condition: string;
  threshold: number;
  notifyChannels: NotifyChannel[];
  recipients: string[];
  lastTriggered?: string;
  triggerCount: number;
  createdAt: string;
}

const DEMO_RULES: AlertRule[] = [
  {
    id: '1',
    name: '数据质量异常告警',
    description: '当数据完整度低于90%时触发',
    metricType: 'data_quality',
    severity: 'high',
    status: 'active',
    condition: 'completeness < 0.9',
    threshold: 90,
    notifyChannels: ['email', 'dingtalk'],
    recipients: ['admin@example.com'],
    lastTriggered: '2026-01-30 14:30:00',
    triggerCount: 5,
    createdAt: '2026-01-20 10:00:00',
  },
  {
    id: '2',
    name: 'ETL 任务失败告警',
    description: '任务执行失败时立即通知',
    metricType: 'task_failure',
    severity: 'critical',
    status: 'active',
    condition: 'status == "failed"',
    threshold: 0,
    notifyChannels: ['sms', 'webhook'],
    recipients: ['+8613800138000'],
    lastTriggered: '2026-01-31 02:15:00',
    triggerCount: 2,
    createdAt: '2026-01-15 09:00:00',
  },
  {
    id: '3',
    name: '数据量异常检测',
    description: '每日数据增量低于预期值',
    metricType: 'data_volume',
    severity: 'medium',
    status: 'paused',
    condition: 'daily_increment < expected * 0.5',
    threshold: 50,
    notifyChannels: ['email'],
    recipients: ['data-team@example.com'],
    triggerCount: 0,
    createdAt: '2026-01-25 14:20:00',
  },
];

const METRIC_TYPE_OPTIONS = [
  { label: '数据质量', value: 'data_quality' },
  { label: '任务失败', value: 'task_failure' },
  { label: '数据量异常', value: 'data_volume' },
  { label: '延迟告警', value: 'latency' },
  { label: '自定义指标', value: 'custom' },
];

const SEVERITY_OPTIONS = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'critical' },
];

const CHANNEL_OPTIONS = [
  { label: '邮件', value: 'email' },
  { label: '短信', value: 'sms' },
  { label: 'Webhook', value: 'webhook' },
  { label: '钉钉', value: 'dingtalk' },
];

const Alerts: React.FC = () => {
  const [rules, setRules] = useState<AlertRule[]>(DEMO_RULES);
  const [histories, setHistories] = useState<any[]>([
    { id: '1', ruleId: '1', ruleName: '数据质量异常告警', triggeredAt: '2026-01-30 14:30:00', status: 'resolved', message: '表 user_data 完整度 85%' },
    { id: '2', ruleId: '2', ruleName: 'ETL 任务失败告警', triggeredAt: '2026-01-31 02:15:00', status: 'active', message: '任务 daily_sync 执行失败' },
  ]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({
      severity: 'medium',
      status: 'active',
      notifyChannels: ['email'],
    });
    setModalVisible(true);
  };

  const handleEdit = (rule: AlertRule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setModalVisible(true);
  };

  const handleDelete = (id: string) => {
    setRules(rules.filter((r) => r.id !== id));
    message.success('删除成功');
  };

  const handleToggleStatus = (id: string) => {
    setRules((prev) =>
      prev.map((r) =>
        r.id === id
          ? { ...r, status: r.status === 'active' ? ('paused' as const) : ('active' as const) }
          : r
      )
    );
    message.success('状态已更新');
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingRule) {
        setRules((prev) =>
          prev.map((r) =>
            r.id === editingRule.id ? { ...r, ...values } : r
          )
        );
        message.success('更新成功');
      } else {
        const newRule: AlertRule = {
          id: Date.now().toString(),
          name: values.name,
          description: values.description,
          metricType: values.metricType,
          severity: values.severity,
          status: values.status,
          condition: values.condition,
          threshold: values.threshold || 0,
          notifyChannels: values.notifyChannels,
          recipients: values.recipients?.split(',').map((s: string) => s.trim()) || [],
          triggerCount: 0,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setRules([newRule, ...rules]);
        message.success('创建成功');
      }
      setModalVisible(false);
    });
  };

  const getSeverityTag = (severity: AlertSeverity) => {
    const config = {
      low: { color: 'green', text: '低' },
      medium: { color: 'orange', text: '中' },
      high: { color: 'red', text: '高' },
      critical: { color: 'magenta', text: '紧急' },
    };
    const { color, text } = config[severity];
    return <Tag color={color}>{text}</Tag>;
  };

  const getStatusTag = (status: AlertStatus) => {
    const config = {
      active: { color: 'success', text: '启用' },
      paused: { color: 'default', text: '暂停' },
      triggered: { color: 'error', text: '触发中' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const ruleColumns = [
    { title: '规则名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '指标类型',
      dataIndex: 'metricType',
      key: 'metricType',
      width: 120,
      render: (type: MetricType) => {
        const opt = METRIC_TYPE_OPTIONS.find((o) => o.value === type);
        return <Tag color="blue">{opt?.label || type}</Tag>;
      },
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (severity: AlertSeverity) => getSeverityTag(severity),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: AlertStatus, record: AlertRule) => (
        <Switch
          size="small"
          checked={status === 'active'}
          onChange={() => handleToggleStatus(record.id)}
          checkedChildren="启用"
          unCheckedChildren="暂停"
        />
      ),
    },
    {
      title: '触发次数',
      dataIndex: 'triggerCount',
      key: 'triggerCount',
      width: 100,
      render: (count: number) => <Text strong>{count}</Text>,
    },
    {
      title: '最后触发',
      dataIndex: 'lastTriggered',
      key: 'lastTriggered',
      width: 160,
      render: (t?: string) => t || '-',
    },
    {
      title: '通知渠道',
      dataIndex: 'notifyChannels',
      key: 'notifyChannels',
      width: 150,
      render: (channels: NotifyChannel[]) =>
        channels.map((c) => {
          const opt = CHANNEL_OPTIONS.find((o) => o.value === c);
          return <Tag key={c}>{opt?.label || c}</Tag>;
        }),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: AlertRule) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const historyColumns = [
    { title: '规则名称', dataIndex: 'ruleName', key: 'ruleName' },
    { title: '触发时间', dataIndex: 'triggeredAt', key: 'triggeredAt' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'resolved' ? 'success' : 'error'}>
          {status === 'resolved' ? '已解决' : '活跃'}
        </Tag>
      ),
    },
    { title: '消息内容', dataIndex: 'message', key: 'message', ellipsis: true },
  ];

  const tabItems = [
    {
      key: 'rules',
      label: `预警规则 (${rules.length})`,
      children: (
        <Card
          size="small"
          title="预警规则列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建规则
            </Button>
          }
        >
          <Table
            columns={ruleColumns}
            dataSource={rules.map((r) => ({ ...r, key: r.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1100 }}
          />
        </Card>
      ),
    },
    {
      key: 'history',
      label: '告警历史',
      children: (
        <Card size="small" title="告警触发历史">
          <Table
            columns={historyColumns}
            dataSource={histories.map((h) => ({ ...h, key: h.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <BellOutlined /> 智能预警配置
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="预警配置说明"
          description="配置数据质量、任务执行、数据量等指标的预警规则，当触发条件满足时将通过指定渠道发送通知。"
          type="info"
          showIcon
          icon={<ExclamationCircleOutlined />}
        />
        <Tabs items={tabItems} />
      </Space>

      <Modal
        title={editingRule ? '编辑预警规则' : '新建预警规则'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="规则名称"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="如：数据质量异常告警" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="metricType"
                label="指标类型"
                rules={[{ required: true, message: '请选择指标类型' }]}
              >
                <Select options={METRIC_TYPE_OPTIONS} placeholder="选择指标类型" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="severity"
                label="严重程度"
                rules={[{ required: true }]}
              >
                <Select options={SEVERITY_OPTIONS} placeholder="选择严重程度" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="threshold" label="阈值">
                <InputNumber placeholder="阈值" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="condition"
            label="触发条件表达式"
            rules={[{ required: true, message: '请输入触发条件' }]}
          >
            <Input placeholder="如：completeness < 0.9 或 status == 'failed'" />
          </Form.Item>

          <Form.Item
            name="notifyChannels"
            label="通知渠道"
            rules={[{ required: true, message: '请选择通知渠道' }]}
          >
            <Select mode="multiple" options={CHANNEL_OPTIONS} placeholder="选择通知渠道" />
          </Form.Item>

          <Form.Item name="recipients" label="接收人">
            <Input placeholder="邮箱地址或手机号，逗号分隔" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="规则描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Alerts;
