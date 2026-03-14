/**
 * Model Registry List Page
 *
 * Lists all registered ML models with search, filter, and registration functionality.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Tag,
  Tooltip,
  Popconfirm,
  Card,
  Row,
  Col,
  Statistic,
  message,
  Tabs,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  EditOutlined,
  DeploymentIcon,
  RocketOutlined,
  TagOutlined,
  ClusterOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import { useModelStore } from '@/stores/model';
import type { RegisteredModel } from '@/stores/model';

const { Search } = Input;

const ModelListPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const {
    models,
    deployments,
    loading,
    error,
    fetchModels,
    createRegisteredModel,
    deleteModel,
    renameModel,
    fetchDeployments,
    clearError,
  } = useModelStore();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [selectedModel, setSelectedModel] = useState<RegisteredModel | null>(null);
  const [activeTab, setActiveTab] = useState('models');

  useEffect(() => {
    fetchModels();
    fetchDeployments();
  }, [fetchModels, fetchDeployments]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    fetchModels(value || undefined);
  };

  const handleCreate = async () => {
    const values = form.getFieldsValue();
    setCreating(true);
    try {
      await createRegisteredModel(
        values.name,
        values.description,
        values.tags ? JSON.parse(values.tags) : undefined,
      );
      message.success('Model registered successfully');
      setCreateModalOpen(false);
      form.resetFields();
    } catch (err) {
      message.error('Failed to register model');
    } finally {
      setCreating(false);
    }
  };

  const handleRename = async () => {
    if (!selectedModel) return;
    setRenaming(true);
    try {
      const values = form.getFieldsValue();
      await renameModel(selectedModel.name, values.new_name);
      message.success('Model renamed successfully');
      setRenameModalOpen(false);
      form.resetFields();
      setSelectedModel(null);
    } catch (err) {
      message.error('Failed to rename model');
    } finally {
      setRenaming(false);
    }
  };

  const handleDelete = async (model: RegisteredModel) => {
    try {
      await deleteModel(model.name);
      message.success('Model deleted');
    } catch (err) {
      message.error('Failed to delete model');
    }
  };

  const handleView = (model: RegisteredModel) => {
    navigate(`/models/${model.name}`);
  };

  const handleDeploy = (model: RegisteredModel) => {
    navigate(`/models/${model.name}/deploy`);
  };

  const getStageTag = (model: RegisteredModel) => {
    if (model.production_version) {
      return <Tag color="green">Production: {model.production_version}</Tag>;
    }
    if (model.staging_version) {
      return <Tag color="blue">Staging: {model.staging_version}</Tag>;
    }
    if (model.latest_version) {
      return <Tag color="default">v{model.latest_version}</Tag>;
    }
    return <Tag color="default">No versions</Tag>;
  };

  const modelColumns = [
    {
      title: 'Model Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: RegisteredModel) => (
        <Space>
          <a onClick={() => handleView(record)} style={{ fontWeight: 500 }}>
            {name}
          </a>
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: 'Latest Version',
      key: 'version',
      render: (_: any, record: RegisteredModel) => getStageTag(record),
    },
    {
      title: 'Created',
      dataIndex: 'creation_time',
      key: 'creation_time',
      width: 180,
      render: (timestamp: number) => new Date(timestamp).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: RegisteredModel) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleView(record)}
            />
          </Tooltip>
          <Tooltip title="Deploy">
            <Button
              type="text"
              icon={<DeploymentIcon />}
              onClick={() => handleDeploy(record)}
            />
          </Tooltip>
          <Tooltip title="Rename">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedModel(record);
                setRenameModalOpen(true);
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this model?"
            description="This will delete the model and all its versions."
            onConfirm={() => handleDelete(record)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const deploymentColumns = [
    {
      title: 'Deployment Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <Space>
          <RocketOutlined />
          <a onClick={() => navigate(`/models/deployments/${record.id}`)}>
            {name}
          </a>
        </Space>
      ),
    },
    {
      title: 'Model',
      dataIndex: 'model_name',
      key: 'model_name',
      render: (name: string, record: any) => (
        <span>{name}:{record.model_version}</span>
      ),
    },
    {
      title: 'Framework',
      dataIndex: 'framework',
      key: 'framework',
      render: (framework: string) => <Tag>{framework}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: {
          deploying: 'blue',
          running: 'green',
          failed: 'red',
          stopped: 'default',
        };
        return <Tag color={colors[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: 'Replicas',
      dataIndex: 'replicas',
      key: 'replicas',
      width: 80,
    },
    {
      title: 'GPU',
      key: 'gpu',
      render: (_: any, record: any) => {
        if (record.gpu_enabled) {
          return (
            <Tag color="purple">{record.gpu_type || 'GPU'}: {record.gpu_count}</Tag>
          );
        }
        return '-';
      },
    },
    {
      title: 'Traffic',
      dataIndex: 'traffic_percentage',
      key: 'traffic_percentage',
      width: 80,
      render: (pct: number) => <Tag>{pct}%</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/models/deployments/${record.id}`)}
          >
            View
          </Button>
        </Space>
      ),
    },
  ];

  // Calculate stats
  const modelCount = models.length;
  const deploymentCount = deployments.length;
  const runningDeployments = deployments.filter((d) => d.status === 'running').length;
  const deployedModels = models.filter((m) => m.production_version || m.staging_version).length;

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <h1 style={{ margin: 0 }}>Model Registry</h1>
            <p style={{ margin: '8px 0 0 0', color: '#666' }}>
              Register, version, and deploy ML models
            </p>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalOpen(true)}
            >
              Register Model
            </Button>
          </Col>
        </Row>
      </div>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Registered Models"
              value={modelCount}
              prefix={<ClusterOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Deployed Models"
              value={deployedModels}
              prefix={<DeploymentIcon />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Deployments"
              value={runningDeployments}
              valueStyle={{ color: runningDeployments > 0 ? '#52c41a' : undefined }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Deployments"
              value={deploymentCount}
            />
          </Card>
        </Col>
      </Row>

      {/* Search */}
      <Card style={{ marginBottom: '16px' }}>
        <Search
          placeholder="Search models by name..."
          allowClear
          enterButton={<SearchOutlined />}
          onSearch={handleSearch}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ maxWidth: '400px' }}
        />
      </Card>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab={`Registered Models (${modelCount})`} key="models">
            <Table
              columns={modelColumns}
              dataSource={models}
              rowKey="name"
              loading={loading}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `Total ${total} models`,
              }}
            />
          </TabPane>

          <TabPane tab={`Deployments (${deploymentCount})`} key="deployments">
            <Table
              columns={deploymentColumns}
              dataSource={deployments}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `Total ${total} deployments`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Create Modal */}
      <Modal
        title="Register New Model"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={creating}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Model Name"
            rules={[
              { required: true, message: 'Please enter model name' },
              { pattern: '^[a-zA-Z0-9._-]+$', message: 'Only letters, numbers, dots, hyphens, and underscores' },
            ]}
          >
            <Input placeholder="my-model" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea
              rows={3}
              placeholder="Describe the model..."
            />
          </Form.Item>

          <Form.Item name="tags" label="Tags (JSON format)">
            <Input.TextArea
              rows={2}
              placeholder='{"task": "classification", "framework": "sklearn"}'
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Rename Modal */}
      <Modal
        title="Rename Model"
        open={renameModalOpen}
        onOk={handleRename}
        onCancel={() => {
          setRenameModalOpen(false);
          form.resetFields();
          setSelectedModel(null);
        }}
        confirmLoading={renaming}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="new_name"
            label="New Name"
            rules={[{ required: true, message: 'Please enter new name' }]}
            initialValue={selectedModel?.name}
          >
            <Input placeholder="new-model-name" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ModelListPage;
