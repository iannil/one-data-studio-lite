import React, { useState } from 'react';
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
  Alert,
  Modal,
  Switch,
  Tabs,
  Row,
  Col,
} from 'antd';
import {
  LinkOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type LinkStatus = 'active' | 'paused' | 'error';
type SourceType = 'datasource' | 'table' | 'task';
type TargetType = 'seatunnel' | 'dolphinscheduler' | 'hop';

interface EtlLink {
  id: string;
  name: string;
  description?: string;
  sourceType: SourceType;
  sourceUrn: string;
  targetType: TargetType;
  targetTaskId: string;
  triggerCondition: string;
  status: LinkStatus;
  autoSync: boolean;
  lastSync?: string;
  syncCount: number;
  createdAt: string;
}

const DEMO_LINKS: EtlLink[] = [
  {
    id: '1',
    name: 'MySQL 用户表到 SeaTunnel',
    description: 'MySQL user 表变更自动触发 SeaTunnel 同步任务',
    sourceType: 'table',
    sourceUrn: 'mysql:db_user.user_info',
    targetType: 'seatunnel',
    targetTaskId: 'sync_user_001',
    triggerCondition: 'schema_change OR data_insert > 100',
    status: 'active',
    autoSync: true,
    lastSync: '2026-01-31 10:30:00',
    syncCount: 15,
    createdAt: '2026-01-20 10:00:00',
  },
  {
    id: '2',
    name: 'DataHub 元数据到 DolphinScheduler',
    description: '元数据变更联动更新 DS 工作流定义',
    sourceType: 'table',
    sourceUrn: 'datahub:warehouse.orders',
    targetType: 'dolphinscheduler',
    targetTaskId: 'process_orders',
    triggerCondition: 'schema_change',
    status: 'active',
    autoSync: true,
    lastSync: '2026-01-30 18:45:00',
    syncCount: 3,
    createdAt: '2026-01-15 09:00:00',
  },
  {
    id: '3',
    name: 'Kafka 到 Hop 工作流',
    description: 'Kafka 主题消息触发 Hop ETL 流程',
    sourceType: 'datasource',
    sourceUrn: 'kafka:topic.user_events',
    targetType: 'hop',
    targetTaskId: 'process_events',
    triggerCondition: 'message_count > 1000',
    status: 'paused',
    autoSync: false,
    syncCount: 0,
    createdAt: '2026-01-25 14:20:00',
  },
];

const SOURCE_TYPE_OPTIONS = [
  { label: '数据源', value: 'datasource' },
  { label: '数据表', value: 'table' },
  { label: 'ETL 任务', value: 'task' },
];

const TARGET_TYPE_OPTIONS = [
  { label: 'SeaTunnel', value: 'seatunnel' },
  { label: 'DolphinScheduler', value: 'dolphinscheduler' },
  { label: 'Apache Hop', value: 'hop' },
];

const TRIGGER_CONDITIONS = [
  { label: '表结构变更', value: 'schema_change' },
  { label: '数据新增', value: 'data_insert' },
  { label: '数据更新', value: 'data_update' },
  { label: '数据删除', value: 'data_delete' },
  { label: '自定义条件', value: 'custom' },
];

const EtlLink: React.FC = () => {
  const [links, setLinks] = useState<EtlLink[]>(DEMO_LINKS);
  const [histories, setHistories] = useState<any[]>([
    { id: '1', linkId: '1', linkName: 'MySQL 用户表到 SeaTunnel', triggeredAt: '2026-01-31 10:30:00', status: 'success', message: '同步完成，处理 1523 条记录' },
    { id: '2', linkId: '2', linkName: 'DataHub 元数据到 DS', triggeredAt: '2026-01-30 18:45:00', status: 'success', message: '工作流定义已更新' },
  ]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingLink, setEditingLink] = useState<EtlLink | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingLink(null);
    form.resetFields();
    form.setFieldsValue({
      sourceType: 'table',
      targetType: 'seatunnel',
      status: 'active',
      autoSync: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (link: EtlLink) => {
    setEditingLink(link);
    form.setFieldsValue(link);
    setModalVisible(true);
  };

  const handleDelete = (id: string) => {
    setLinks(links.filter((l) => l.id !== id));
    message.success('删除成功');
  };

  const handleToggleStatus = (id: string) => {
    setLinks((prev) =>
      prev.map((l) =>
        l.id === id
          ? { ...l, status: l.status === 'active' ? ('paused' as const) : ('active' as const) }
          : l
      )
    );
    message.success('状态已更新');
  };

  const handleManualTrigger = (id: string) => {
    message.success('已手动触发联动执行');
    // Simulate trigger
    setTimeout(() => {
      const newHistory = {
        id: Date.now().toString(),
        linkId: id,
        linkName: links.find((l) => l.id === id)?.name || '未知',
        triggeredAt: new Date().toLocaleString('zh-CN'),
        status: 'success',
        message: '手动触发执行完成',
      };
      setHistories([newHistory, ...histories]);
    }, 1000);
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingLink) {
        setLinks((prev) =>
          prev.map((l) =>
            l.id === editingLink.id ? { ...l, ...values } : l
          )
        );
        message.success('更新成功');
      } else {
        const newLink: EtlLink = {
          id: Date.now().toString(),
          name: values.name,
          description: values.description,
          sourceType: values.sourceType,
          sourceUrn: values.sourceUrn,
          targetType: values.targetType,
          targetTaskId: values.targetTaskId,
          triggerCondition: values.triggerCondition,
          status: values.status,
          autoSync: values.autoSync,
          syncCount: 0,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setLinks([newLink, ...links]);
        message.success('创建成功');
      }
      setModalVisible(false);
    });
  };

  const getStatusTag = (status: LinkStatus) => {
    const config = {
      active: { color: 'success', text: '启用' },
      paused: { color: 'default', text: '暂停' },
      error: { color: 'error', text: '错误' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    { title: '规则名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '源类型',
      dataIndex: 'sourceType',
      key: 'sourceType',
      width: 100,
      render: (type: SourceType) => {
        const opt = SOURCE_TYPE_OPTIONS.find((o) => o.value === type);
        return <Tag color="blue">{opt?.label || type}</Tag>;
      },
    },
    { title: '源 URN', dataIndex: 'sourceUrn', key: 'sourceUrn', ellipsis: true },
    {
      title: '目标类型',
      dataIndex: 'targetType',
      key: 'targetType',
      width: 120,
      render: (type: TargetType) => {
        const opt = TARGET_TYPE_OPTIONS.find((o) => o.value === type);
        return <Tag color="green">{opt?.label || type}</Tag>;
      },
    },
    { title: '目标任务 ID', dataIndex: 'targetTaskId', key: 'targetTaskId', width: 150 },
    {
      title: '触发条件',
      dataIndex: 'triggerCondition',
      key: 'triggerCondition',
      ellipsis: true,
      width: 200,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: LinkStatus, record: EtlLink) => (
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
      title: '自动同步',
      dataIndex: 'autoSync',
      key: 'autoSync',
      width: 100,
      render: (auto: boolean) => (
        <Tag color={auto ? 'success' : 'default'}>{auto ? '是' : '否'}</Tag>
      ),
    },
    { title: '同步次数', dataIndex: 'syncCount', key: 'syncCount', width: 100 },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, record: EtlLink) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleManualTrigger(record.id)}
            disabled={record.status !== 'active'}
          >
            触发
          </Button>
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
    { title: '规则名称', dataIndex: 'linkName', key: 'linkName' },
    { title: '触发时间', dataIndex: 'triggeredAt', key: 'triggeredAt' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'success' ? 'success' : 'error'}>
          {status === 'success' ? '成功' : '失败'}
        </Tag>
      ),
    },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
  ];

  const tabItems = [
    {
      key: 'links',
      label: `联动规则 (${links.length})`,
      children: (
        <Card
          size="small"
          title="ETL 数据联动规则"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建规则
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={links.map((l) => ({ ...l, key: l.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1300 }}
          />
        </Card>
      ),
    },
    {
      key: 'history',
      label: '联动历史',
      children: (
        <Card size="small" title="执行历史记录">
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
        <LinkOutlined /> ETL 数据联动
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="数据联动说明"
          description="配置数据源变更与 ETL 任务的联动规则，当数据发生变更时自动触发关联的 SeaTunnel、DolphinScheduler 或 Hop 任务执行。"
          type="info"
          showIcon
          icon={<ThunderboltOutlined />}
        />
        <Tabs items={tabItems} />
      </Space>

      <Modal
        title={editingLink ? '编辑联动规则' : '新建联动规则'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="如：MySQL 用户表到 SeaTunnel" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="sourceType"
                label="源类型"
                rules={[{ required: true }]}
              >
                <Select options={SOURCE_TYPE_OPTIONS} placeholder="选择源类型" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="targetType"
                label="目标类型"
                rules={[{ required: true }]}
              >
                <Select options={TARGET_TYPE_OPTIONS} placeholder="选择目标类型" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="sourceUrn"
            label="源 URN"
            rules={[{ required: true, message: '请输入源 URN' }]}
          >
            <Input placeholder="如：mysql:db_user.user_info" />
          </Form.Item>

          <Form.Item
            name="targetTaskId"
            label="目标任务 ID"
            rules={[{ required: true, message: '请输入目标任务 ID' }]}
          >
            <Input placeholder="如：sync_user_001" />
          </Form.Item>

          <Form.Item
            name="triggerCondition"
            label="触发条件"
            rules={[{ required: true, message: '请输入触发条件' }]}
          >
            <Input placeholder="如：schema_change OR data_insert > 100" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="autoSync"
                label="自动同步"
                valuePropName="checked"
              >
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="status"
                label="启用状态"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="规则描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default EtlLink;
