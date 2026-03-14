/**
 * Hyperparameter Optimization Studies List Page
 *
 * Lists all hyperparameter optimization studies with search, filter, and create functionality.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Tooltip,
  Popconfirm,
  message,
  Row,
  Col,
  Statistic,
  Progress,
  Badge,
  Modal,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  LineChartOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useHyperoptStore } from '@/stores/hyperopt';
import type { OptimizationStudy, StudyStatus } from '@/stores/hyperopt';

const { Search } = Input;

const HyperoptListPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    studies,
    loading,
    error,
    fetchStudies,
    deleteStudy,
    clearError,
  } = useHyperoptStore();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedStudy, setSelectedStudy] = useState<OptimizationStudy | null>(null);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleDelete = async (study: OptimizationStudy) => {
    try {
      await deleteStudy(study.study_id);
      message.success('Study deleted successfully');
      setDeleteModalOpen(false);
      setSelectedStudy(null);
    } catch (err) {
      message.error('Failed to delete study');
    }
  };

  const getStatusBadge = (status: StudyStatus) => {
    const statusConfig: Record<StudyStatus, { color: string; icon: React.ReactNode; text: string }> = {
      created: { color: 'default', icon: <ExperimentOutlined />, text: 'Created' },
      running: { color: 'processing', icon: <ThunderboltOutlined spin />, text: 'Running' },
      completed: { color: 'success', icon: <CheckCircleOutlined />, text: 'Completed' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Failed' },
      cancelled: { color: 'default', icon: <PauseCircleOutlined />, text: 'Cancelled' },
    };

    const config = statusConfig[status];
    return (
      <Badge
        status={config.color as any}
        text={
          <Space size={4}>
            {config.icon}
            {config.text}
          </Space>
        }
      />
    );
  };

  const getDirectionTag = (direction: string) => {
    return direction === 'maximize' ? (
      <Tag color="green">Maximize</Tag>
    ) : (
      <Tag color="orange">Minimize</Tag>
    );
  };

  const getSamplerTag = (sampler: string) => {
    const colors: Record<string, string> = {
      tpe: 'blue',
      random: 'default',
      cmaes: 'purple',
      grid: 'cyan',
    };
    const names: Record<string, string> = {
      tpe: 'TPE',
      random: 'Random',
      cmaes: 'CMA-ES',
      grid: 'Grid',
    };
    return <Tag color={colors[sampler] || 'default'}>{names[sampler] || sampler}</Tag>;
  };

  const columns = [
    {
      title: 'Study Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: OptimizationStudy) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={() => navigate(`/experiments/hyperopt/${record.study_id}`)}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          <span style={{ fontSize: '12px', color: '#999' }}>
            {record.study_id}
          </span>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: StudyStatus) => getStatusBadge(status),
    },
    {
      title: 'Metric',
      key: 'metric',
      width: 150,
      render: (_: any, record: OptimizationStudy) => (
        <Space size="small">
          {getDirectionTag(record.direction)}
          <span>{record.metric}</span>
        </Space>
      ),
    },
    {
      title: 'Best Value',
      dataIndex: 'best_value',
      key: 'best_value',
      width: 120,
      render: (value: number | null) => {
        if (value === null) return '-';
        return <Tag color="blue">{typeof value === 'number' ? value.toFixed(4) : value}</Tag>;
      },
    },
    {
      title: 'Progress',
      key: 'progress',
      width: 150,
      render: (_: any, record: OptimizationStudy) => {
        const percent = record.progress * 100;
        const completed = record.completed_trials;
        const total = record.n_trials;
        return (
          <Space direction="vertical" size={0}>
            <Progress percent={percent} size="small" status={record.status === 'failed' ? 'exception' : undefined} />
            <span style={{ fontSize: '12px', color: '#999' }}>
              {completed} / {total} trials
            </span>
          </Space>
        );
      },
    },
    {
      title: 'Sampler',
      dataIndex: 'sampler',
      key: 'sampler',
      width: 100,
      render: (sampler: string) => getSamplerTag(sampler),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_: any, record: OptimizationStudy) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/experiments/hyperopt/${record.study_id}`)}
            />
          </Tooltip>
          {record.status === 'created' && (
            <Tooltip title="Start Optimization">
              <Button
                type="text"
                icon={<PlayCircleOutlined />}
                onClick={() => navigate(`/experiments/hyperopt/${record.study_id}`)}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="Delete this study?"
            description="This will delete the study and all its trials. This action cannot be undone."
            onConfirm={() => handleDelete(record)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Filter studies
  const filteredStudies = studies.filter((study) => {
    const matchesSearch = !searchTerm ||
      study.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      study.study_id.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || study.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Calculate stats
  const totalStudies = studies.length;
  const runningStudies = studies.filter((s) => s.status === 'running').length;
  const completedStudies = studies.filter((s) => s.status === 'completed').length;
  const totalTrials = studies.reduce((sum, s) => sum + s.completed_trials, 0);

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <h1 style={{ margin: 0 }}>
              <RocketOutlined /> Hyperparameter Optimization
            </h1>
            <p style={{ margin: '8px 0 0 0', color: '#666' }}>
              Optimize your model hyperparameters with Optuna
            </p>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/experiments/hyperopt/new')}
            >
              New Study
            </Button>
          </Col>
        </Row>
      </div>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Studies"
              value={totalStudies}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Running"
              value={runningStudies}
              valueStyle={{ color: '#1890ff' }}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Completed"
              value={completedStudies}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Trials"
              value={totalTrials}
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: '16px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Search
              placeholder="Search studies by name..."
              allowClear
              enterButton={<SearchOutlined />}
              onSearch={handleSearch}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ maxWidth: 300 }}
            />
          </Col>
          <Col>
            <Select
              placeholder="Filter by status"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 150 }}
            >
              <Select.Option value="all">All Status</Select.Option>
              <Select.Option value="created">Created</Select.Option>
              <Select.Option value="running">Running</Select.Option>
              <Select.Option value="completed">Completed</Select.Option>
              <Select.Option value="failed">Failed</Select.Option>
            </Select>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredStudies}
          rowKey="study_id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} studies`,
          }}
        />
      </Card>
    </div>
  );
};

export default HyperoptListPage;
