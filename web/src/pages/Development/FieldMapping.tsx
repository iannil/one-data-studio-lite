import React, { useEffect, useState } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Form,
  Modal,
  Input,
  Select,
  message,
  Typography,
  Space,
  Switch,
  Alert,
  Popconfirm,
} from 'antd';
import {
  LinkOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import {
  getMappingsV1,
  createMappingV1,
  updateMappingV1,
  deleteMappingV1,
  triggerSyncV1,
  type ETLMapping,
  type ChangeType,
} from '../../api/metadata-sync';

const { Title, Text } = Typography;

const TASK_TYPE_OPTIONS = [
  { label: 'DolphinScheduler', value: 'dolphinscheduler' },
  { label: 'SeaTunnel', value: 'seatunnel' },
  { label: 'Apache Hop', value: 'hop' },
];

const CHANGE_TYPE_OPTIONS = [
  { label: 'CREATE', value: 'CREATE' },
  { label: 'UPDATE', value: 'UPDATE' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'SCHEMA_CHANGE', value: 'SCHEMA_CHANGE' },
];

const FieldMapping: React.FC = () => {
  const [mappings, setMappings] = useState<ETLMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMapping, setEditingMapping] = useState<ETLMapping | null>(null);
  const [form] = Form.useForm();

  const fetchMappings = async () => {
    setLoading(true);
    try {
      const resp = await getMappingsV1();
      if (resp.success) {
        setMappings(resp.data || []);
      } else {
        message.error(resp.message || '获取映射列表失败');
      }
    } catch {
      message.error('获取映射列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings();
  }, []);

  const handleCreate = () => {
    setEditingMapping(null);
    form.resetFields();
    form.setFieldsValue({
      trigger_on: ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
      auto_update_config: true,
      enabled: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: ETLMapping) => {
    setEditingMapping(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      const resp = await deleteMappingV1(id);
      if (resp.success) {
        message.success('删除成功');
        fetchMappings();
      } else {
        message.error(resp.message || '删除失败');
      }
    } catch {
      message.error('删除失败');
    }
  };

  const handleToggleEnabled = async (record: ETLMapping, enabled: boolean) => {
    try {
      const resp = await updateMappingV1(record.id!, { enabled });
      if (resp.success) {
        message.success(`${enabled ? '启用' : '禁用'}成功`);
        fetchMappings();
      } else {
        message.error(resp.message || '操作失败');
      }
    } catch {
      message.error('操作失败');
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const resp = await triggerSyncV1();
      if (resp.success) {
        message.success('同步触发成功');
        if (resp.data?.affected_tasks?.length) {
          message.info(`影响任务: ${resp.data.affected_tasks.join(', ')}`);
        }
      } else {
        message.error(resp.message || '同步失败');
      }
    } catch {
      message.error('同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      const isEdit = !!editingMapping;

      if (isEdit) {
        const resp = await updateMappingV1(editingMapping!.id!, values);
        if (resp.success) {
          message.success('更新成功');
          setModalVisible(false);
          fetchMappings();
        } else {
          message.error(resp.message || '更新失败');
        }
      } else {
        const resp = await createMappingV1(values);
        if (resp.success) {
          message.success('创建成功');
          setModalVisible(false);
          fetchMappings();
        } else {
          message.error(resp.message || '创建失败');
        }
      }
    } catch {
      // Form validation failed
    }
  };

  const columns = [
    {
      title: '源 URN',
      dataIndex: 'source_urn',
      key: 'source_urn',
      ellipsis: true,
      width: 250,
    },
    {
      title: '任务类型',
      dataIndex: 'target_task_type',
      key: 'target_task_type',
      width: 120,
      render: (type: string) => {
        const colors: Record<string, string> = {
          dolphinscheduler: 'blue',
          seatunnel: 'cyan',
          hop: 'purple',
        };
        return <Tag color={colors[type]}>{type}</Tag>;
      },
    },
    {
      title: '任务 ID',
      dataIndex: 'target_task_id',
      key: 'target_task_id',
      width: 150,
    },
    {
      title: '触发条件',
      dataIndex: 'trigger_on',
      key: 'trigger_on',
      width: 200,
      render: (types: ChangeType[]) => (
        <>
          {types?.map((t) => (
            <Tag key={t} color="geekblue" style={{ marginBottom: 4 }}>
              {t}
            </Tag>
          ))}
        </>
      ),
    },
    {
      title: '自动更新配置',
      dataIndex: 'auto_update_config',
      key: 'auto_update_config',
      width: 100,
      render: (auto: boolean) => (
        <Tag color={auto ? 'green' : 'default'}>{auto ? '是' : '否'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record: ETLMapping) => (
        <Switch
          checked={enabled}
          onChange={(v) => handleToggleEnabled(record, v)}
          size="small"
        />
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right' as const,
      render: (_: unknown, record: ETLMapping) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除此映射规则吗？"
            onConfirm={() => handleDelete(record.id!)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <LinkOutlined /> 字段映射管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="元数据联动说明"
          description="当 DataHub 中元数据发生变更时，可自动触发关联的 ETL 任务更新。配置映射规则后，元数据变更将自动同步到 DolphinScheduler、SeaTunnel 或 Apache Hop 任务。"
          type="info"
          showIcon
          icon={<CheckCircleOutlined />}
        />

        <Card
          size="small"
          title="映射规则列表"
          extra={
            <Space>
              <Button
                icon={<SyncOutlined />}
                loading={syncing}
                onClick={handleSync}
              >
                手动同步
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新建映射
              </Button>
            </Space>
          }
        >
          <Table
            columns={columns}
            dataSource={mappings.map((m, i) => ({ ...m, key: m.id || i }))}
            loading={loading}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1000 }}
          />
        </Card>
      </Space>

      <Modal
        title={editingMapping ? '编辑映射规则' : '新建映射规则'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          preserve={false}
        >
          <Form.Item
            name="source_urn"
            label="源 URN"
            rules={[
              { required: true, message: '请输入源 URN' },
              {
                pattern: /^urn:li:dataset:\(.+\)$/,
                message: 'URN 格式应为: urn:li:dataset:(...)',
              },
            ]}
          >
            <Input
              placeholder="urn:li:dataset:(urn:li:dataPlatform:hive,example_db,example_table,PROD)"
            />
          </Form.Item>

          <Form.Item
            name="target_task_type"
            label="目标任务类型"
            rules={[{ required: true, message: '请选择目标任务类型' }]}
          >
            <Select options={TASK_TYPE_OPTIONS} placeholder="选择 ETL 引擎" />
          </Form.Item>

          <Form.Item
            name="target_task_id"
            label="目标任务 ID"
            rules={[{ required: true, message: '请输入目标任务 ID' }]}
          >
            <Input placeholder="任务 ID，如: 12345 或 workflow-name" />
          </Form.Item>

          <Form.Item
            name="trigger_on"
            label="触发条件"
            rules={[{ required: true, message: '请选择触发条件' }]}
          >
            <Select
              mode="multiple"
              options={CHANGE_TYPE_OPTIONS}
              placeholder="选择触发变更类型"
            />
          </Form.Item>

          <Form.Item
            name="auto_update_config"
            label="自动更新配置"
            valuePropName="checked"
          >
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>

          <Form.Item
            name="enabled"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="映射规则描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FieldMapping;
