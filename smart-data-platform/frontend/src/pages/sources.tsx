'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Card,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tag,
  Popconfirm,
  Tooltip,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { sourcesApi } from '@/services/api';
import type { DataSource } from '@/types';

const { Title } = Typography;

const SOURCE_TYPES = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'oracle', label: 'Oracle' },
  { value: 'sqlserver', label: 'SQL Server' },
  { value: 'csv', label: 'CSV 文件' },
  { value: 'excel', label: 'Excel 文件' },
  { value: 'api', label: 'REST API' },
];

export default function SourcesPage() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [form] = Form.useForm();

  const fetchSources = async () => {
    setLoading(true);
    try {
      const response = await sourcesApi.list();
      setSources(response.data);
    } catch (error) {
      message.error('获取数据源列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleCreate = () => {
    setEditingSource(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record: DataSource) => {
    setEditingSource(record);
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      type: record.type,
      ...record.connection_config,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await sourcesApi.delete(id);
      message.success('删除成功');
      fetchSources();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleTest = async (id: string) => {
    try {
      const response = await sourcesApi.test(id);
      if (response.data.success) {
        message.success('连接测试成功');
      } else {
        message.error(`连接测试失败: ${response.data.message}`);
      }
      fetchSources();
    } catch (error) {
      message.error('连接测试失败');
    }
  };

  const handleScan = async (id: string) => {
    try {
      await sourcesApi.scan(id, { include_row_count: true });
      message.success('元数据扫描完成');
    } catch (error) {
      message.error('元数据扫描失败');
    }
  };

  const handleSubmit = async (values: any) => {
    const { name, description, type, ...connectionConfig } = values;
    const data = {
      name,
      description,
      type,
      connection_config: connectionConfig,
    };

    try {
      if (editingSource) {
        await sourcesApi.update(editingSource.id, data);
        message.success('更新成功');
      } else {
        await sourcesApi.create(data);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchSources();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns: ColumnsType<DataSource> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        const item = SOURCE_TYPES.find((t) => t.value === type);
        return item?.label || type;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
          active: { color: 'success', icon: <CheckCircleOutlined /> },
          inactive: { color: 'default', icon: null },
          error: { color: 'error', icon: <ExclamationCircleOutlined /> },
          testing: { color: 'processing', icon: <SyncOutlined spin /> },
        };
        const config = statusConfig[status] || statusConfig.inactive;
        return <Tag color={config.color} icon={config.icon}>{status}</Tag>;
      },
    },
    {
      title: '最后连接',
      dataIndex: 'last_connected_at',
      key: 'last_connected_at',
      render: (date) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="测试连接">
            <Button size="small" icon={<SyncOutlined />} onClick={() => handleTest(record.id)} />
          </Tooltip>
          <Tooltip title="扫描元数据">
            <Button size="small" icon={<SearchOutlined />} onClick={() => handleScan(record.id)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const selectedType = Form.useWatch('type', form);

  return (
    <AuthGuard>
      <Card
        title={<Title level={4}>数据源管理</Title>}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            添加数据源
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={sources}
          rowKey="id"
          loading={loading}
        />
      </Card>

      <Modal
        title={editingSource ? '编辑数据源' : '添加数据源'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={SOURCE_TYPES} />
          </Form.Item>

          {['postgresql', 'mysql', 'oracle', 'sqlserver'].includes(selectedType) && (
            <>
              <Form.Item name="host" label="主机" rules={[{ required: true }]}>
                <Input placeholder="localhost" />
              </Form.Item>
              <Form.Item name="port" label="端口" rules={[{ required: true }]}>
                <Input type="number" placeholder="5432" />
              </Form.Item>
              <Form.Item name="database" label="数据库" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}

          {['csv', 'excel'].includes(selectedType) && (
            <Form.Item name="file_path" label="文件路径" rules={[{ required: true }]}>
              <Input placeholder="/path/to/file.csv" />
            </Form.Item>
          )}

          {selectedType === 'api' && (
            <>
              <Form.Item name="base_url" label="API 地址" rules={[{ required: true }]}>
                <Input placeholder="https://api.example.com" />
              </Form.Item>
              <Form.Item name="token" label="API Token">
                <Input.Password />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </AuthGuard>
  );
}
