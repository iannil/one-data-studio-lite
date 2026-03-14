/**
 * Training Jobs List Page
 *
 * Lists all distributed training jobs with management actions.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Tooltip,
  Popconfirm,
  message,
  Modal,
  Row,
  Col,
  Statistic,
  Badge,
  Dropdown,
  Divider,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EditOutlined,
  CopyOutlined,
  DownloadOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  MoreOutlined,
  ReloadOutlined,
  FilterOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useTrainingStore,
  useTrainingStats,
  useTrainingLoading,
  useTrainingError,
} from '@/stores/training';
import type {
  TrainingJob,
  TrainingStatus,
  TrainingBackend,
  ColumnsType,
} from '@/types/training';

const TrainingListPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    jobs,
    selectedJobIds,
    loading,
    error,
    fetchJobs,
    cancelJob,
    deleteJob,
    getJobLogs,
    getJobMetrics,
    selectJob,
    selectMultipleJobs,
    clearSelection,
    setFilters,
    setSort,
    setError,
    clearError,
  } = useTrainingStore();

  const stats = useTrainingStats();
  const isLoading = useTrainingLoading();
  const trainingError = useTrainingError();

  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [backendFilter, setBackendFilter] = useState<string>('all');
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [metricsModalOpen, setMetricsModalOpen] = useState(false);
  const [selectedJobForLogs, setSelectedJobForLogs] = useState<TrainingJob | null>(null);
  const [selectedJobMetrics, setSelectedJobMetrics] = useState<Record<string, any>>({});
  const [jobLogs, setJobLogs] = useState('');

  useEffect(() => {
    fetchJobs().catch((err) => {
      if (trainingError) message.error(trainingError);
    });
  }, [fetchJobs]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  // Handle filters
  useEffect(() => {
    setFilters({
      status: statusFilter === 'all' ? undefined : (statusFilter as TrainingStatus),
      backend: backendFilter === 'all' ? undefined : (backendFilter as TrainingBackend),
      search: searchText || undefined,
    });
  }, [statusFilter, backendFilter, searchText, setFilters]);

  // Handle view logs
  const handleViewLogs = useCallback(
    async (job: TrainingJob) => {
      setSelectedJobForLogs(job);
      setLogsModalOpen(true);

      try {
        const logs = await getJobLogs(job.job_id, false, 500);
        setJobLogs(logs);
      } catch (err: any) {
        message.error('Failed to fetch logs');
      }
    },
    [getJobLogs]
  );

  // Handle view metrics
  const handleViewMetrics = useCallback(
    async (job: TrainingJob) => {
      setSelectedJobForLogs(job);
      setMetricsModalOpen(true);

      try {
        const metrics = await getJobMetrics(job.job_id);
        setSelectedJobMetrics(metrics || {});
      } catch (err: any) {
        message.error('Failed to fetch metrics');
      }
    },
    [getJobMetrics]
  );

  // Handle cancel
  const handleCancel = useCallback(
    async (job: TrainingJob) => {
      try {
        await cancelJob(job.job_id);
        message.success('Job cancelled successfully');
        fetchJobs();
      } catch (err: any) {
        message.error(err.message || 'Failed to cancel job');
      }
    },
    [cancelJob, fetchJobs]
  );

  // Handle delete
  const handleDelete = useCallback(
    async (job: TrainingJob) => {
      try {
        await deleteJob(job.job_id);
        message.success('Job deleted successfully');
        fetchJobs();
      } catch (err: any) {
        message.error(err.message || 'Failed to delete job');
      }
    },
    [deleteJob, fetchJobs]
  );

  // Status badge
  const getStatusBadge = (status: TrainingStatus) => {
    const statusConfig: Record<TrainingStatus, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: 'Pending' },
      starting: { color: 'processing', icon: <ReloadOutlined spin />, text: 'Starting' },
      running: { color: 'processing', icon: <ThunderboltOutlined />, text: 'Running' },
      completed: { color: 'success', icon: <CheckCircleOutlined />, text: 'Completed' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Failed' },
      cancelled: { color: 'default', icon: <StopOutlined />, text: 'Cancelled' },
      paused: { color: 'warning', icon: <PauseCircleOutlined />, text: 'Paused' },
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

  // Backend badge
  const getBackendBadge = (backend: TrainingBackend) => {
    const backendConfig: Record<TrainingBackend, { color: string; text: string }> = {
      pytorch: { color: 'orange', text: 'PyTorch' },
      tensorflow: { color: 'blue', text: 'TensorFlow' },
      jax: { color: 'cyan', text: 'JAX' },
      huggingface: { color: 'yellow', text: 'HuggingFace' },
    };

    const config = backendConfig[backend];
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // Duration display
  const formatDuration = (seconds: number | undefined) => {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  // Table columns
  const columns: ColumnsType<TrainingJob> = [
    {
      title: 'Job Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: TrainingJob) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={() => {
              selectJob(record.job_id);
              navigate(`/training/jobs/${record.job_id}`);
            }}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          <span style={{ fontSize: '12px', color: '#999' }}>
            {record.job_id}
          </span>
        </Space>
      ),
      sorter: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: TrainingStatus) => getStatusBadge(status),
      filters: [
        { text: 'Pending', value: 'pending' },
        { text: 'Running', value: 'running' },
        { text: 'Completed', value: 'completed' },
        { text: 'Failed', value: 'failed' },
      ],
    },
    {
      title: 'Framework',
      dataIndex: 'backend',
      key: 'backend',
      width: 120,
      render: (backend: TrainingBackend) => getBackendBadge(backend),
      filters: [
        { text: 'PyTorch', value: 'pytorch' },
        { text: 'TensorFlow', value: 'tensorflow' },
      ],
    },
    {
      title: 'Nodes',
      key: 'nodes',
      width: 100,
      render: (_, record: TrainingJob) => (
        <Tag>{record.num_nodes} × {record.num_processes_per_node}</Tag>
      ),
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      width: 120,
      render: (duration: number) => formatDuration(duration),
      sorter: true,
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
      sorter: true,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record: TrainingJob) => (
        <Space size="small">
          <Tooltip title="View Logs">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewLogs(record)}
            />
          </Tooltip>
          <Tooltip title="View Metrics">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => handleViewMetrics(record)}
              disabled={record.status !== 'running' && record.status !== 'completed'}
            />
          </Tooltip>
          {record.is_running && (
            <Tooltip title="Cancel">
              <Button
                type="text"
                icon={<StopOutlined />}
                onClick={() => handleCancel(record)}
              />
            </Tooltip>
          )}
          <Dropdown
            menu={{
              items: [
                {
                  key: 'clone',
                  label: 'Clone Job',
                  icon: <CopyOutlined />,
                  onClick: () => {
                    navigate(`/training/new?clone=${record.job_id}`);
                  },
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  label: 'Delete',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => handleDelete(record),
                },
              ],
            }}
            trigger={['click']}
          >
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col>
            <Space direction="vertical" size={0}>
              <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
                <RocketOutlined /> Training Jobs
              </h1>
              <span style={{ color: '#999' }}>
                Manage distributed training jobs
              </span>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/training/new')}
            >
              New Training Job
            </Button>
          </Col>
        </Row>
      </div>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Jobs"
              value={stats.total}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Running"
              value={stats.running}
              valueStyle={{ color: '#1890ff' }}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Completed"
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Failed"
              value={stats.failed}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Pending"
              value={stats.pending}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="GPU Hours"
              value={jobs.reduce((acc, job) => {
                if (job.duration && job.config?.resources?.gpu_count) {
                  return acc + (job.duration * job.config.resources.gpu_count / 3600);
                }
                return acc;
              }, 0).toFixed(1)}
              suffix="hrs"
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: '16px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input
              placeholder="Search training jobs..."
              prefix={<FilterOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              style={{ maxWidth: 300 }}
            />
          </Col>
          <Col>
            <Select
              placeholder="Status"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">All Status</Select.Option>
              <Select.Option value="pending">Pending</Select.Option>
              <Select.Option value="running">Running</Select.Option>
              <Select.Option value="completed">Completed</Select.Option>
              <Select.Option value="failed">Failed</Select.Option>
            </Select>
          </Col>
          <Col>
            <Select
              placeholder="Framework"
              value={backendFilter}
              onChange={setBackendFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">All Frameworks</Select.Option>
              <Select.Option value="pytorch">PyTorch</Select.Option>
              <Select.Option value="tensorflow">TensorFlow</Select.Option>
            </Select>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchJobs()}
              loading={isLoading}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card
        bodyStyle={{ padding: 0 }}
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
      >
        <Table
          columns={columns}
          dataSource={jobs}
          rowKey="job_id"
          loading={isLoading}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} jobs`,
          }}
          scroll={{ y: 'calc(100vh - 520px)' }}
          rowSelection={{
            selectedRowKeys: selectedJobIds,
            onChange: (selectedRowKeys) => {
              selectMultipleJobs(selectedRowKeys as string[]);
            },
          }}
        />
      </Card>

      {/* Logs Modal */}
      <Modal
        title={
          <Space>
            Logs
            {selectedJobForLogs && <Tag color="blue">{selectedJobForLogs.name}</Tag>}
          </Space>
        }
        open={logsModalOpen}
        onCancel={() => setLogsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setLogsModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        <pre
          style={{
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: '16px',
            borderRadius: '4px',
            maxHeight: '500px',
            overflow: 'auto',
            fontSize: '12px',
          }}
        >
          {jobLogs || 'No logs available'}
        </pre>
      </Modal>

      {/* Metrics Modal */}
      <Modal
        title={
          <Space>
            Metrics
            {selectedJobForLogs && <Tag color="green">{selectedJobForLogs.name}</Tag>}
          </Space>
        }
        open={metricsModalOpen}
        onCancel={() => setMetricsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setMetricsModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={600}
      >
        <Row gutter={[16, 16]}>
          {Object.entries(selectedJobMetrics).map(([key, value]) => (
            <Col key={key} span={12}>
              <Card size="small">
                <Statistic
                  title={key}
                  value={value}
                  precision={typeof value === 'number' ? 4 : 0}
                />
              </Card>
            </Col>
          ))}
        </Row>
        {Object.keys(selectedJobMetrics).length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
            No metrics available
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TrainingListPage;
