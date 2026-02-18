'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Tabs,
  Tag,
  Button,
  Space,
  Typography,
  Badge,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Alert,
  Divider,
  List,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SearchOutlined,
  WarningOutlined,
  MailOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { alertsApi, securityApi, sourcesApi } from '@/services/api';
import type { AlertRule, Alert as AlertType, DataSource } from '@/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface AnomalyResult {
  method: string;
  column: string;
  total_rows: number;
  anomaly_count: number;
  anomaly_percentage: number;
  statistics: Record<string, number>;
  anomalies: Array<{
    index: number;
    value: number;
    z_score?: number;
    bound_violated?: string;
  }>;
}

export default function SecurityPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [form] = Form.useForm();

  // Anomaly detection state
  const [sources, setSources] = useState<DataSource[]>([]);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [anomalyResult, setAnomalyResult] = useState<AnomalyResult | null>(null);
  const [anomalyForm] = Form.useForm();

  const fetchRules = async () => {
    try {
      const response = await alertsApi.listRules();
      setRules(response.data);
    } catch (error) {
      console.error('Failed to fetch rules');
    }
  };

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const response = await alertsApi.listAlerts();
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await securityApi.listAuditLogs({ limit: 100 });
      setAuditLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch audit logs');
    }
  };

  const fetchSources = async () => {
    try {
      const response = await sourcesApi.list();
      setSources(response.data);
    } catch (error) {
      console.error('Failed to fetch sources');
    }
  };

  useEffect(() => {
    fetchRules();
    fetchAlerts();
    fetchAuditLogs();
    fetchSources();
  }, []);

  const handleCreateRule = async (values: any) => {
    const ruleData = {
      ...values,
      notification_channels: values.notification_channels || [],
      notification_config: {
        email_recipients: values.email_recipients
          ? values.email_recipients.split(',').map((e: string) => e.trim())
          : [],
        webhook_url: values.webhook_url || undefined,
      },
    };

    try {
      await alertsApi.createRule(ruleData);
      message.success('创建成功');
      setRuleModalOpen(false);
      form.resetFields();
      fetchRules();
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleAcknowledge = async (id: string) => {
    try {
      await alertsApi.acknowledgeAlert(id);
      message.success('已确认');
      fetchAlerts();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await alertsApi.resolveAlert(id);
      message.success('已解决');
      fetchAlerts();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDetectAnomalies = async (values: any) => {
    setAnomalyLoading(true);
    setAnomalyResult(null);

    try {
      const response = await alertsApi.detectAnomalies(
        values.source_id,
        values.table_name,
        values.column_name,
        values.method,
        values.threshold
      );
      setAnomalyResult(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '检测失败');
    } finally {
      setAnomalyLoading(false);
    }
  };

  const ruleColumns: ColumnsType<AlertRule> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => {
        const colors: Record<string, string> = {
          info: 'blue',
          warning: 'orange',
          critical: 'red',
        };
        return <Tag color={colors[severity]}>{severity}</Tag>;
      },
    },
    {
      title: '条件',
      key: 'condition',
      render: (_, record) => (
        <Text code>
          {record.metric_name} {record.condition} {record.threshold}
        </Text>
      ),
    },
    {
      title: '通知渠道',
      key: 'channels',
      render: (_, record) => (
        <Space>
          {record.notification_channels?.map((ch: string) => (
            <Tag key={ch} icon={ch === 'email' ? <MailOutlined /> : null}>
              {ch}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled) => (
        <Badge status={enabled ? 'success' : 'default'} text={enabled ? '启用' : '禁用'} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small">编辑</Button>
          <Popconfirm title="确定删除?" onConfirm={() => alertsApi.deleteRule(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const alertColumns: ColumnsType<AlertType> = [
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => {
        const colors: Record<string, string> = {
          info: 'blue',
          warning: 'orange',
          critical: 'red',
        };
        return <Tag color={colors[severity]} icon={<ExclamationCircleOutlined />}>{severity}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const colors: Record<string, string> = {
          active: 'error',
          acknowledged: 'warning',
          resolved: 'success',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '当前值 / 阈值',
      key: 'values',
      render: (_, record) => (
        <Text>
          {record.current_value.toFixed(2)} / {record.threshold_value.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'active' && (
            <Button size="small" onClick={() => handleAcknowledge(record.id)}>
              确认
            </Button>
          )}
          {record.status !== 'resolved' && (
            <Button size="small" type="primary" onClick={() => handleResolve(record.id)}>
              解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const auditColumns: ColumnsType<any> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '用户',
      dataIndex: 'user_email',
      key: 'user_email',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action) => <Tag>{action}</Tag>,
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
    },
    {
      title: '资源名称',
      dataIndex: 'resource_name',
      key: 'resource_name',
    },
    {
      title: 'IP',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
  ];

  const activeAlerts = alerts.filter((a) => a.status === 'active').length;

  return (
    <AuthGuard>
      <Card title={<Title level={4}>安全管理</Title>}>
        <Tabs
          items={[
            {
              key: 'alerts',
              label: (
                <Badge count={activeAlerts} offset={[10, 0]}>
                  <BellOutlined /> 告警中心
                </Badge>
              ),
              children: (
                <Table columns={alertColumns} dataSource={alerts} rowKey="id" loading={loading} />
              ),
            },
            {
              key: 'rules',
              label: '告警规则',
              children: (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setRuleModalOpen(true)}>
                      创建规则
                    </Button>
                  </div>
                  <Table columns={ruleColumns} dataSource={rules} rowKey="id" />
                </>
              ),
            },
            {
              key: 'anomaly',
              label: (
                <span><WarningOutlined /> 异常检测</span>
              ),
              children: (
                <Row gutter={24}>
                  <Col span={8}>
                    <Card title="检测配置" size="small">
                      <Form
                        form={anomalyForm}
                        layout="vertical"
                        onFinish={handleDetectAnomalies}
                        initialValues={{ method: 'zscore', threshold: 3.0 }}
                      >
                        <Form.Item name="source_id" label="数据源" rules={[{ required: true }]}>
                          <Select
                            placeholder="选择数据源"
                            options={sources.map((s) => ({ value: s.id, label: s.name }))}
                          />
                        </Form.Item>
                        <Form.Item name="table_name" label="表名" rules={[{ required: true }]}>
                          <Input placeholder="输入表名" />
                        </Form.Item>
                        <Form.Item name="column_name" label="数值列" rules={[{ required: true }]}>
                          <Input placeholder="输入数值列名" />
                        </Form.Item>
                        <Form.Item name="method" label="检测方法">
                          <Select
                            options={[
                              { value: 'zscore', label: 'Z-Score (标准差)' },
                              { value: 'iqr', label: 'IQR (四分位距)' },
                            ]}
                          />
                        </Form.Item>
                        <Form.Item name="threshold" label="阈值">
                          <InputNumber min={0.5} max={10} step={0.5} style={{ width: '100%' }} />
                        </Form.Item>
                        <Button
                          type="primary"
                          htmlType="submit"
                          loading={anomalyLoading}
                          icon={<SearchOutlined />}
                          block
                        >
                          开始检测
                        </Button>
                      </Form>
                    </Card>
                  </Col>
                  <Col span={16}>
                    {anomalyResult ? (
                      <Card title="检测结果" size="small">
                        <Row gutter={16} style={{ marginBottom: 16 }}>
                          <Col span={6}>
                            <Statistic title="总行数" value={anomalyResult.total_rows} />
                          </Col>
                          <Col span={6}>
                            <Statistic
                              title="异常数量"
                              value={anomalyResult.anomaly_count}
                              valueStyle={{ color: anomalyResult.anomaly_count > 0 ? '#cf1322' : '#3f8600' }}
                            />
                          </Col>
                          <Col span={6}>
                            <Statistic
                              title="异常比例"
                              value={anomalyResult.anomaly_percentage}
                              suffix="%"
                              precision={2}
                            />
                          </Col>
                          <Col span={6}>
                            <Statistic title="检测方法" value={anomalyResult.method.toUpperCase()} />
                          </Col>
                        </Row>

                        <Divider>统计信息</Divider>
                        <Row gutter={16}>
                          {Object.entries(anomalyResult.statistics).map(([key, value]) => (
                            <Col span={6} key={key}>
                              <Statistic title={key} value={value} precision={2} />
                            </Col>
                          ))}
                        </Row>

                        {anomalyResult.anomalies.length > 0 && (
                          <>
                            <Divider>异常值列表 (前 20 条)</Divider>
                            <List
                              size="small"
                              dataSource={anomalyResult.anomalies.slice(0, 20)}
                              renderItem={(item) => (
                                <List.Item>
                                  <Text>索引 {item.index}: </Text>
                                  <Text strong code>{item.value.toFixed(4)}</Text>
                                  {item.z_score && (
                                    <Tag color="orange">Z-Score: {item.z_score.toFixed(2)}</Tag>
                                  )}
                                  {item.bound_violated && (
                                    <Tag color={item.bound_violated === 'upper' ? 'red' : 'blue'}>
                                      {item.bound_violated === 'upper' ? '超上限' : '低于下限'}
                                    </Tag>
                                  )}
                                </List.Item>
                              )}
                            />
                          </>
                        )}
                      </Card>
                    ) : (
                      <Card>
                        <div style={{ textAlign: 'center', padding: 60 }}>
                          <WarningOutlined style={{ fontSize: 48, color: '#faad14' }} />
                          <Paragraph style={{ marginTop: 16 }}>
                            选择数据源、表和列，然后点击「开始检测」进行异常检测
                          </Paragraph>
                          <Paragraph type="secondary">
                            支持 Z-Score 和 IQR 两种统计方法检测数值异常
                          </Paragraph>
                        </div>
                      </Card>
                    )}
                  </Col>
                </Row>
              ),
            },
            {
              key: 'audit',
              label: '审计日志',
              children: <Table columns={auditColumns} dataSource={auditLogs} rowKey="id" />,
            },
          ]}
        />
      </Card>

      <Modal
        title="创建告警规则"
        open={ruleModalOpen}
        onCancel={() => setRuleModalOpen(false)}
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateRule}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item name="metric_sql" label="指标 SQL" rules={[{ required: true }]}>
            <TextArea rows={3} placeholder="SELECT COUNT(*) as count FROM ..." />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="metric_name" label="指标名称" rules={[{ required: true }]}>
                <Input placeholder="count" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="condition" label="条件" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'gt', label: '大于 (>)' },
                    { value: 'gte', label: '大于等于 (>=)' },
                    { value: 'lt', label: '小于 (<)' },
                    { value: 'lte', label: '小于等于 (<=)' },
                    { value: 'eq', label: '等于 (==)' },
                    { value: 'ne', label: '不等于 (!=)' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="threshold" label="阈值" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="severity" label="严重级别" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'info', label: '信息' },
                    { value: 'warning', label: '警告' },
                    { value: 'critical', label: '严重' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="check_interval_minutes" label="检查间隔(分钟)" initialValue={5}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider>通知设置</Divider>

          <Form.Item name="notification_channels" label="通知渠道">
            <Select
              mode="multiple"
              placeholder="选择通知渠道"
              options={[
                { value: 'email', label: '邮件通知' },
                { value: 'webhook', label: 'Webhook' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="email_recipients"
            label="邮件收件人"
            tooltip="多个邮箱用逗号分隔"
          >
            <Input placeholder="admin@example.com, ops@example.com" />
          </Form.Item>
          <Form.Item name="webhook_url" label="Webhook URL">
            <Input placeholder="https://hooks.example.com/..." />
          </Form.Item>
        </Form>
      </Modal>
    </AuthGuard>
  );
}
