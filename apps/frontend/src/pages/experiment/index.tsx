/**
 * Experiment List Page
 *
 * Lists all MLflow experiments with search, filter, and create functionality.
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
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  RestoreOutlined,
  BarChartOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useExperimentStore } from '@/stores/experiment';
import type { Experiment } from '@/stores/experiment';

const { Search } = Input;

const ExperimentListPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const {
    experiments,
    loading,
    error,
    fetchExperiments,
    createExperiment,
    deleteExperiment,
    restoreExperiment,
    clearError,
  } = useExperimentStore();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    fetchExperiments(undefined, value || undefined);
  };

  const handleCreate = async () => {
    const values = form.getFieldsValue();
    setCreating(true);
    try {
      await createExperiment({
        name: values.name,
        description: values.description,
      });
      message.success('Experiment created successfully');
      setCreateModalOpen(false);
      form.resetFields();
    } catch (err) {
      message.error('Failed to create experiment');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (exp: Experiment) => {
    try {
      await deleteExperiment(exp.id);
      message.success('Experiment deleted');
    } catch (err) {
      message.error('Failed to delete experiment');
    }
  };

  const handleRestore = async (exp: Experiment) => {
    try {
      await restoreExperiment(exp.id);
      message.success('Experiment restored');
    } catch (err) {
      message.error('Failed to restore experiment');
    }
  };

  const getStatusTag = (exp: Experiment) => {
    if (exp.lifecycle_stage === 'deleted') {
      return <Tag color="red">Deleted</Tag>;
    }
    return <Tag color="green">Active</Tag>;
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Experiment) => (
        <Space>
          <a onClick={() => navigate(`/experiments/${record.id}`)}>{name}</a>
          {getStatusTag(record)}
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
      title: 'Runs',
      dataIndex: 'run_count',
      key: 'run_count',
      width: 100,
      render: (count: number) => (
        <Tag color="blue">{count || 0}</Tag>
      ),
    },
    {
      title: 'Best Metric',
      key: 'best_metric',
      ellipsis: true,
      render: (_: any, record: Experiment) => {
        const best = record.best_run;
        if (!best) return '-';
        const metricKeys = Object.keys(best.metrics || {});
        if (metricKeys.length === 0) return '-';
        const key = metricKeys[0];
        const value = best.metrics![key];
        return (
          <Tooltip title={`Run: ${best.run_name || best.run_id.substring(0, 8)}`}>
            <span>{key}: {value?.toFixed(4)}</span>
          </Tooltip>
        );
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (timestamp: number) => {
        if (!timestamp) return '-';
        return new Date(timestamp).toLocaleString();
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: Experiment) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/experiments/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="View Runs">
            <Button
              type="text"
              icon={<BarChartOutlined />}
              onClick={() => navigate(`/experiments/${record.id}/runs`)}
            />
          </Tooltip>
          {record.lifecycle_stage === 'deleted' ? (
            <Popconfirm
              title="Restore this experiment?"
              onConfirm={() => handleRestore(record)}
            >
              <Button type="text" icon={<RestoreOutlined />} />
            </Popconfirm>
          ) : (
            <Popconfirm
              title="Delete this experiment?"
              description="This will soft delete the experiment. You can restore it later."
              onConfirm={() => handleDelete(record)}
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // Calculate stats
  const activeExperiments = experiments.filter((e) => e.lifecycle_stage !== 'deleted');
  const totalRuns = activeExperiments.reduce((sum, e) => sum + (e.run_count || 0), 0);

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <h1 style={{ margin: 0 }}>Experiments</h1>
            <p style={{ margin: '8px 0 0 0', color: '#666' }}>
              Track and compare your ML experiments
            </p>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalOpen(true)}
            >
              New Experiment
            </Button>
          </Col>
        </Row>
      </div>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Experiments"
              value={activeExperiments.length}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Runs"
              value={totalRuns}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Deleted Experiments"
              value={experiments.length - activeExperiments.length}
              valueStyle={{ color: experiments.length - activeExperiments.length > 0 ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      {/* Search */}
      <Card style={{ marginBottom: '16px' }}>
        <Search
          placeholder="Search experiments by name..."
          allowClear
          enterButton={<SearchOutlined />}
          onSearch={handleSearch}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ maxWidth: '400px' }}
        />
      </Card>

      {/* Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={experiments}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} experiments`,
          }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="Create Experiment"
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
            label="Experiment Name"
            rules={[
              { required: true, message: 'Please enter experiment name' },
              { max: 256, message: 'Name too long' },
            ]}
          >
            <Input placeholder="My Experiment" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea
              rows={4}
              placeholder="Describe the purpose of this experiment..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ExperimentListPage;
