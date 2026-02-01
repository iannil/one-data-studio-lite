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
  Steps,
} from 'antd';
import {
  MergeCellsOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type FusionStatus = 'draft' | 'running' | 'completed' | 'failed';

interface FusionTask {
  id: string;
  name: string;
  sourceTables: string[];
  targetTable: string;
  fusionType: 'union' | 'join' | 'merge' | 'aggregate';
  status: FusionStatus;
  enabled: boolean;
  createdAt: string;
  lastRun?: string;
  recordCount?: number;
}

const FUSION_TYPE_OPTIONS = [
  { label: '合并 (Union)', value: 'union', desc: '将多个表的数据合并到一起' },
  { label: '关联 (Join)', value: 'join', desc: '基于关键字段关联多个表' },
  { label: '融合 (Merge)', value: 'merge', desc: '基于主键进行增量融合' },
  { label: '聚合 (Aggregate)', value: 'aggregate', desc: '按维度聚合多个表数据' },
];

const DEMO_TASKS: FusionTask[] = [
  {
    id: '1',
    name: '多渠道用户数据合并',
    sourceTables: ['user_app', 'user_web', 'user_miniapp'],
    targetTable: 'user_unified',
    fusionType: 'merge',
    status: 'completed',
    enabled: true,
    createdAt: '2026-01-28 10:00:00',
    lastRun: '2026-01-30 02:00:00',
    recordCount: 1523456,
  },
  {
    id: '2',
    name: '订单与用户信息关联',
    sourceTables: ['orders', 'users', 'products'],
    targetTable: 'order_detail_enriched',
    fusionType: 'join',
    status: 'running',
    enabled: true,
    createdAt: '2026-01-29 14:30:00',
    lastRun: '2026-01-30 03:30:00',
  },
  {
    id: '3',
    name: '销售数据全量汇总',
    sourceTables: ['sales_online', 'sales_offline', 'sales_partner'],
    targetTable: 'sales_total',
    fusionType: 'union',
    status: 'draft',
    enabled: false,
    createdAt: '2026-01-30 09:15:00',
  },
];

const DataFusion: React.FC = () => {
  const [tasks, setTasks] = useState<FusionTask[]>(DEMO_TASKS);
  const [modalVisible, setModalVisible] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewTask, setPreviewTask] = useState<FusionTask | null>(null);
  const [editingTask, setEditingTask] = useState<FusionTask | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingTask(null);
    form.resetFields();
    form.setFieldsValue({
      fusionType: 'merge',
      enabled: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (task: FusionTask) => {
    setEditingTask(task);
    form.setFieldsValue({
      name: task.name,
      sourceTables: task.sourceTables,
      targetTable: task.targetTable,
      fusionType: task.fusionType,
      enabled: task.enabled,
    });
    setModalVisible(true);
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingTask) {
        setTasks((prev) =>
          prev.map((t) =>
            t.id === editingTask.id
              ? { ...t, ...values, sourceTables: values.sourceTables.split(',').map((s: string) => s.trim()) }
              : t
          )
        );
        message.success('更新成功');
      } else {
        const newTask: FusionTask = {
          id: Date.now().toString(),
          name: values.name,
          sourceTables: values.sourceTables.split(',').map((s: string) => s.trim()),
          targetTable: values.targetTable,
          fusionType: values.fusionType,
          status: 'draft',
          enabled: values.enabled,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setTasks([newTask, ...tasks]);
        message.success('创建成功');
      }
      setModalVisible(false);
    });
  };

  const handleRun = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, status: 'running' as const } : t
      )
    );
    message.success('融合任务已启动');

    // Simulate completion
    setTimeout(() => {
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? {
                ...t,
                status: 'completed' as const,
                lastRun: new Date().toLocaleString('zh-CN'),
                recordCount: Math.floor(Math.random() * 1000000) + 100000,
              }
            : t
        )
      );
      message.success('融合任务完成');
    }, 3000);
  };

  const handleDelete = (taskId: string) => {
    setTasks(tasks.filter((t) => t.id !== taskId));
    message.success('任务已删除');
  };

  const handleToggleEnabled = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, enabled: !t.enabled } : t
      )
    );
  };

  const handlePreview = (task: FusionTask) => {
    setPreviewTask(task);
    setPreviewVisible(true);
  };

  const getStatusTag = (status: FusionStatus) => {
    const config = {
      draft: { color: 'default', text: '草稿' },
      running: { color: 'blue', text: '运行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const getFusionTypeTag = (type: FusionTask['fusionType']) => {
    const config = {
      union: { color: 'purple', text: 'Union' },
      join: { color: 'blue', text: 'Join' },
      merge: { color: 'green', text: 'Merge' },
      aggregate: { color: 'orange', text: 'Aggregate' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '融合类型',
      dataIndex: 'fusionType',
      key: 'fusionType',
      width: 100,
      render: (type: FusionTask['fusionType']) => getFusionTypeTag(type),
    },
    {
      title: '源表',
      dataIndex: 'sourceTables',
      key: 'sourceTables',
      width: 200,
      render: (tables: string[]) => (
        <>
          {tables.slice(0, 2).map((t, i) => (
            <Tag key={i} color="geekblue">
              {t}
            </Tag>
          ))}
          {tables.length > 2 && (
            <Tag>+{tables.length - 2}</Tag>
          )}
        </>
      ),
    },
    {
      title: '目标表',
      dataIndex: 'targetTable',
      key: 'targetTable',
      width: 150,
      render: (table: string) => <Tag color="cyan">{table}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: FusionStatus, record: FusionTask) => (
        <Space>
          {getStatusTag(status)}
          <Switch
            size="small"
            checked={record.enabled}
            onChange={() => handleToggleEnabled(record.id)}
            disabled={status === 'running'}
          />
        </Space>
      ),
    },
    {
      title: '记录数',
      dataIndex: 'recordCount',
      key: 'recordCount',
      width: 100,
      render: (count?: number) => (count ? count.toLocaleString() : '-'),
    },
    {
      title: '最后运行',
      dataIndex: 'lastRun',
      key: 'lastRun',
      width: 150,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right' as const,
      render: (_: unknown, record: FusionTask) => (
        <Space size="small">
          {record.status !== 'running' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleRun(record.id)}
              disabled={!record.enabled}
            >
              运行
            </Button>
          )}
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            详情
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
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const currentStep = editingTask ? 1 : 0;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <MergeCellsOutlined /> 数据融合配置
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="数据融合说明"
          description={
            <>
              <Text>
                数据融合模块支持多源数据的合并、关联、融合与聚合操作。
              </Text>
              <br />
              <Text type="secondary">
                当前为演示模式，实际使用需要配置数据融合引擎服务。
              </Text>
            </>
          }
          type="info"
          showIcon
        />

        <Card
          size="small"
          title="融合任务列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建融合任务
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={tasks.map((t) => ({ ...t, key: t.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1200 }}
          />
        </Card>
      </Space>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingTask ? '编辑融合任务' : '新建融合任务'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={700}
      >
        <Steps current={currentStep} size="small" style={{ marginBottom: 24 }}>
          <Steps.Step title="基本信息" />
          <Steps.Step title="配置规则" />
          <Steps.Step title="预览确认" />
        </Steps>

        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="如：多渠道用户数据合并" />
          </Form.Item>

          <Form.Item
            name="fusionType"
            label="融合类型"
            rules={[{ required: true, message: '请选择融合类型' }]}
          >
            <Select options={FUSION_TYPE_OPTIONS.map((o) => ({ label: o.label, value: o.value }))} />
          </Form.Item>

          <Form.Item
            name="sourceTables"
            label="源表（逗号分隔）"
            rules={[{ required: true, message: '请输入源表名' }]}
          >
            <Input placeholder="如：user_app, user_web, user_miniapp" />
          </Form.Item>

          <Form.Item
            name="targetTable"
            label="目标表"
            rules={[{ required: true, message: '请输入目标表名' }]}
          >
            <Input placeholder="如：user_unified" />
          </Form.Item>

          <Form.Item
            name="enabled"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="融合规则描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情预览弹窗 */}
      <Modal
        title="融合任务详情"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {previewTask && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Card size="small" title="基本信息">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>任务名称：{previewTask.name}</Text>
                <Text>融合类型：{getFusionTypeTag(previewTask.fusionType)}</Text>
                <Text>状态：{getStatusTag(previewTask.status)}</Text>
                <Text>启用：{previewTask.enabled ? '是' : '否'}</Text>
              </Space>
            </Card>

            <Card size="small" title="数据表配置">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>源表：</Text>
                <Space wrap>
                  {previewTask.sourceTables.map((t, i) => (
                    <Tag key={i} color="geekblue">
                      {t}
                    </Tag>
                  ))}
                </Space>
                <Text>目标表：{previewTask.targetTable}</Text>
              </Space>
            </Card>

            <Card size="small" title="运行信息">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>创建时间：{previewTask.createdAt}</Text>
                <Text>最后运行：{previewTask.lastRun || '-'}</Text>
                <Text>记录数：{previewTask.recordCount?.toLocaleString() || '-'}</Text>
              </Space>
            </Card>
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default DataFusion;
