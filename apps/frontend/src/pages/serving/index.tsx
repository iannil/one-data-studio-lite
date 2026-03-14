/**
 * Model Serving List Page
 *
 * Lists inference services, A/B tests, and canary deployments.
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
  Tabs,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EditOutlined,
  CopyOutlined,
  ThunderboltOutlined,
  CloudServerOutlined,
  ExperimentOutlined,
  RocketOutlined,
  EyeOutlined,
  MoreOutlined,
  ReloadOutlined,
  FilterOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useServingStore,
  useServiceStats,
  useABTestStats,
  useCanaryStats,
  useServicesLoading,
  useServicesError,
} from '@/stores/serving';
import type {
  InferenceService,
  ABTestExperiment,
  CanaryDeployment,
  ServingStatus,
  CanaryPhase,
  ColumnsType,
} from '@/types/serving';

const { Text } = Typography;

const ServingListPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('services');

  const {
    // Services
    services,
    fetchServices,
    deleteService,
    scaleService,
    getServiceMetrics,
    updateTrafficDistribution,
    getTrafficDistribution,
    selectService,
    clearServiceSelection,
    setServicesError,
    clearServicesError,

    // A/B Tests
    abTests,
    fetchABTests,
    deleteABTest,
    pauseABTest,
    resumeABTest,

    // Canaries
    canaryDeployments,
    fetchCanaryDeployments,
    startCanaryDeployment,
    promoteCanary,
    rollbackCanary,
    pauseCanaryDeployment,
    resumeCanaryDeployment,
    deleteCanaryDeployment,
  } = useServingStore();

  const serviceStats = useServiceStats();
  const abTestStats = useABTestStats();
  const canaryStats = useCanaryStats();
  const isLoading = useServicesLoading();
  const servingError = useServicesError();

  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [metricsModalOpen, setMetricsModalOpen] = useState(false);
  const [selectedServiceMetrics, setSelectedServiceMetrics] = useState<any>({});
  const [selectedServiceName, setSelectedServiceName] = useState<string>('');

  useEffect(() => {
    fetchAllData();
  }, [activeTab]);

  useEffect(() => {
    if (servingError) {
      message.error(servingError);
      clearServicesError();
    }
  }, [servingError, clearServicesError]);

  const fetchAllData = () => {
    if (activeTab === 'services') {
      fetchServices();
    } else if (activeTab === 'abtests') {
      fetchABTests();
    } else if (activeTab === 'canaries') {
      fetchCanaryDeployments();
    }
  };

  // Handle view metrics
  const handleViewMetrics = useCallback(
    async (service: InferenceService) => {
      setSelectedServiceName(service.name);
      setMetricsModalOpen(true);

      try {
        const metrics = await getServiceMetrics(service.name);
        setSelectedServiceMetrics(metrics);
      } catch (err: any) {
        message.error('Failed to fetch metrics');
      }
    },
    [getServiceMetrics]
  );

  // Handle scale
  const handleScale = useCallback(
    async (service: InferenceService, replicas: number) => {
      try {
        await scaleService(service.name, replicas);
        message.success(`Service scaled to ${replicas} replicas`);
        fetchServices();
      } catch (err: any) {
        message.error(err.message || 'Failed to scale service');
      }
    },
    [scaleService, fetchServices]
  );

  // Handle delete service
  const handleDeleteService = useCallback(
    async (service: InferenceService) => {
      try {
        await deleteService(service.name);
        message.success('Service deleted successfully');
        fetchServices();
      } catch (err: any) {
        message.error(err.message || 'Failed to delete service');
      }
    },
    [deleteService, fetchServices]
  );

  // Status badge
  const getServiceStatusBadge = (status: ServingStatus) => {
    const statusConfig: Record<ServingStatus, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'default', icon: <WarningOutlined />, text: 'Pending' },
      deploying: { color: 'processing', icon: <ReloadOutlined spin />, text: 'Deploying' },
      running: { color: 'success', icon: <PlayCircleOutlined />, text: 'Running' },
      updating: { color: 'processing', icon: <ReloadOutlined spin />, text: 'Updating' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Failed' },
      stopped: { color: 'default', icon: <StopOutlined />, text: 'Stopped' },
      unknown: { color: 'default', icon: <WarningOutlined />, text: 'Unknown' },
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

  // Mode badge
  const getModeBadge = (mode: string) => {
    const modeConfig: Record<string, { color: string; text: string; icon: string }> = {
      raw: { color: 'blue', text: 'Single', icon: '⚡' },
      ab_testing: { color: 'purple', text: 'A/B Test', icon: '🧪' },
      canary: { color: 'orange', text: 'Canary', icon: '🐤' },
      shadow: { color: 'cyan', text: 'Shadow', icon: '👻' },
      mirrored: { color: 'green', text: 'Mirrored', icon: '🪞' },
    };

    const config = modeConfig[mode] || { color: 'default', text: mode, icon: '' };
    return <Tag color={config.color}>{config.icon} {config.text}</Tag>;
  };

  // Service table columns
  const serviceColumns: ColumnsType<InferenceService> = [
    {
      title: 'Service Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: InferenceService) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={() => {
              selectService(name);
              navigate(`/serving/services/${name}`);
            }}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          {record.description && (
            <Text style={{ fontSize: '12px', color: '#999' }}>{record.description}</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: ServingStatus) => getServiceStatusBadge(status),
    },
    {
      title: 'Mode',
      dataIndex: 'mode',
      key: 'mode',
      width: 120,
      render: (mode: string) => getModeBadge(mode),
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      width: 100,
      render: (platform: string) => <Tag>{platform.toUpperCase()}</Tag>,
    },
    {
      title: 'Replicas',
      key: 'replicas',
      width: 100,
      render: (_, record: InferenceService) => (
        <Space>
          <Tag>{record.min_replicas}-{record.max_replicas}</Tag>
          {record.autoscaling_enabled && <Tag color="blue">Auto</Tag>}
        </Space>
      ),
    },
    {
      title: 'Endpoint',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        <Text code style={{ fontSize: '12px' }}>{endpoint || '-'}</Text>
      ),
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
      width: 180,
      fixed: 'right',
      render: (_, record: InferenceService) => (
        <Space size="small">
          <Tooltip title="View Metrics">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewMetrics(record)}
            />
          </Tooltip>
          {record.status === 'running' && (
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'scale-1',
                    label: 'Scale to 1 replica',
                    onClick: () => handleScale(record, 1),
                  },
                  {
                    key: 'scale-3',
                    label: 'Scale to 3 replicas',
                    onClick: () => handleScale(record, 3),
                  },
                  {
                    key: 'scale-5',
                    label: 'Scale to 5 replicas',
                    onClick: () => handleScale(record, 5),
                  },
                ],
              }}
              trigger={['click']}
            >
              <Button type="text" icon={<ThunderboltOutlined />} />
            </Dropdown>
          )}
          <Dropdown
            menu={{
              items: [
                {
                  key: 'edit',
                  label: 'Edit Service',
                  icon: <EditOutlined />,
                  onClick: () => navigate(`/serving/services/${record.name}/edit`),
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  label: 'Delete Service',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => handleDeleteService(record),
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

  // A/B test table columns
  const abTestColumns: ColumnsType<ABTestExperiment> = [
    {
      title: 'Experiment Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ABTestExperiment) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={() => navigate(`/serving/ab-tests/${record.experiment_id}`)}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          <Text style={{ fontSize: '12px', color: '#999' }}>{record.experiment_id}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_, record: ABTestExperiment) => (
        <Space>
          {record.is_running ? (
            <Badge status="processing" text="Running" />
          ) : record.is_active ? (
            <Badge status="default" text="Paused" />
          ) : record.winner_variant_id ? (
            <Badge status="success" text="Completed" />
          ) : (
            <Badge status="default" text="Stopped" />
          )}
        </Space>
      ),
    },
    {
      title: 'Variants',
      key: 'variants',
      width: 100,
      render: (_, record: ABTestExperiment) => <Tag>{record.variants.length} variants</Tag>,
    },
    {
      title: 'Success Metric',
      dataIndex: 'success_metric',
      key: 'success_metric',
      width: 150,
      render: (metric: string) => <Tag color="blue">{metric}</Tag>,
    },
    {
      title: 'Samples',
      key: 'samples',
      width: 100,
      render: (_, record: ABTestExperiment) => (
        <Text>
          {record.variants.reduce((sum, v) => sum + v.request_count, 0)}
        </Text>
      ),
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
      width: 180,
      render: (_, record: ABTestExperiment) => (
        <Space size="small">
          {record.is_running && (
            <Tooltip title="Pause">
              <Button
                type="text"
                icon={<PauseCircleOutlined />}
                onClick={async () => {
                  await pauseABTest(record.experiment_id);
                  message.success('Experiment paused');
                  fetchABTests();
                }}
              />
            </Tooltip>
          )}
          {record.is_active && !record.is_running && (
            <Tooltip title="Resume">
              <Button
                type="text"
                icon={<PlayCircleOutlined />}
                onClick={async () => {
                  await resumeABTest(record.experiment_id);
                  message.success('Experiment resumed');
                  fetchABTests();
                }}
              />
            </Tooltip>
          )}
          <Dropdown
            menu={{
              items: [
                {
                  key: 'view',
                  label: 'View Details',
                  icon: <EyeOutlined />,
                  onClick: () => navigate(`/serving/ab-tests/${record.experiment_id}`),
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  label: 'Delete',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: async () => {
                    await deleteABTest(record.experiment_id);
                    message.success('Experiment deleted');
                    fetchABTests();
                  },
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

  // Canary phase badge
  const getCanaryPhaseBadge = (phase: CanaryPhase) => {
    const config: Record<CanaryPhase, { color: string; text: string }> = {
      initializing: { color: 'default', text: 'Initializing' },
      traffic_shift: { color: 'processing', text: 'Traffic Shift' },
      monitoring: { color: 'warning', text: 'Monitoring' },
      promoted: { color: 'success', text: 'Promoted' },
      rolled_back: { color: 'error', text: 'Rolled Back' },
      failed: { color: 'error', text: 'Failed' },
    };

    const c = config[phase];
    return <Badge status={c.color as any} text={c.text} />;
  };

  // Canary table columns
  const canaryColumns: ColumnsType<CanaryDeployment> = [
    {
      title: 'Deployment Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: CanaryDeployment) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={() => navigate(`/serving/canaries/${record.deployment_id}`)}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          <Text style={{ fontSize: '12px', color: '#999' }}>{record.service_name}</Text>
        </Space>
      ),
    },
    {
      title: 'Phase',
      dataIndex: 'phase',
      key: 'phase',
      width: 140,
      render: (phase: CanaryPhase) => getCanaryPhaseBadge(phase),
    },
    {
      title: 'Progress',
      key: 'progress',
      width: 150,
      render: (_, record: CanaryDeployment) => (
        <Space direction="vertical" size={2}>
          <Progress
            percent={Math.round(record.progress_percentage)}
            size="small"
            status={record.is_complete ? (record.phase === CanaryPhase.PROMOTED ? 'success' : 'exception') : 'active'}
          />
          <Text style={{ fontSize: '12px', color: '#999' }}>
            Step {record.current_step}/{record.total_steps} · {record.current_traffic_percentage}% traffic
          </Text>
        </Space>
      ),
    },
    {
      title: 'Models',
      key: 'models',
      width: 200,
      ellipsis: true,
      render: (_, record: CanaryDeployment) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: '12px' }}>Baseline: {record.baseline_model.substring(0, 30)}...</Text>
          <Text style={{ fontSize: '12px' }}>Canary: {record.canary_model.substring(0, 30)}...</Text>
        </Space>
      ),
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
      width: 180,
      render: (_, record: CanaryDeployment) => (
        <Space size="small">
          {record.is_running && (
            <>
              <Tooltip title="Promote">
                <Button
                  type="text"
                  icon={<CheckCircleOutlined />}
                  onClick={async () => {
                    await promoteCanary(record.deployment_id);
                    message.success('Canary promoted');
                    fetchCanaryDeployments();
                  }}
                />
              </Tooltip>
              <Tooltip title="Rollback">
                <Button
                  type="text"
                  icon={<CloseCircleOutlined />}
                  onClick={async () => {
                    await rollbackCanary(record.deployment_id);
                    message.warning('Canary rolled back');
                    fetchCanaryDeployments();
                  }}
                />
              </Tooltip>
            </>
          )}
          <Dropdown
            menu={{
              items: [
                {
                  key: 'view',
                  label: 'View Details',
                  icon: <EyeOutlined />,
                  onClick: () => navigate(`/serving/canaries/${record.deployment_id}`),
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  label: 'Delete',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: async () => {
                    await deleteCanaryDeployment(record.deployment_id);
                    message.success('Deployment deleted');
                    fetchCanaryDeployments();
                  },
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
                <CloudServerOutlined /> Model Serving
              </h1>
              <span style={{ color: '#999' }}>
                Manage inference services, A/B tests, and canary deployments
              </span>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchAllData}
                loading={isLoading}
              >
                Refresh
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/serving/new')}
              >
                New Service
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        {activeTab === 'services' ? (
          <>
            <Col span={4}>
              <Card>
                <Statistic title="Total Services" value={serviceStats.total} prefix={<CloudServerOutlined />} />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="Running"
                  value={serviceStats.running}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<PlayCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="Deploying"
                  value={serviceStats.deploying}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<ReloadOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="Failed"
                  value={serviceStats.failed}
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="Pending"
                  value={serviceStats.pending}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<WarningOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="Stopped"
                  value={serviceStats.stopped}
                  valueStyle={{ color: '#999' }}
                  prefix={<StopOutlined />}
                />
              </Card>
            </Col>
          </>
        ) : activeTab === 'abtests' ? (
          <>
            <Col span={6}>
              <Card>
                <Statistic title="Total Experiments" value={abTestStats.total} prefix={<ExperimentOutlined />} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Active"
                  value={abTestStats.active}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Running"
                  value={abTestStats.running}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<PlayCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Completed"
                  value={abTestStats.completed}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<RocketOutlined />}
                />
              </Card>
            </Col>
          </>
        ) : (
          <>
            <Col span={5}>
              <Card>
                <Statistic title="Total Deployments" value={canaryStats.total} prefix={<RocketOutlined />} />
              </Card>
            </Col>
            <Col span={5}>
              <Card>
                <Statistic
                  title="Running"
                  value={canaryStats.running}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<PlayCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="Promoted"
                  value={canaryStats.promoted}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={5}>
              <Card>
                <Statistic
                  title="Rolled Back"
                  value={canaryStats.rolledBack}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<WarningOutlined />}
                />
              </Card>
            </Col>
            <Col span={5}>
              <Card>
                <Statistic
                  title="Failed"
                  value={canaryStats.failed}
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
          </>
        )}
      </Row>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'services',
            label: (
              <span>
                <CloudServerOutlined />
                Inference Services ({serviceStats.total})
              </span>
            ),
            children: (
              <>
                {/* Filters */}
                <Card size="small" style={{ marginBottom: '16px' }}>
                  <Row gutter={16} align="middle">
                    <Col flex="auto">
                      <Input
                        placeholder="Search services..."
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
                        <Select.Option value="running">Running</Select.Option>
                        <Select.Option value="deploying">Deploying</Select.Option>
                        <Select.Option value="failed">Failed</Select.Option>
                      </Select>
                    </Col>
                  </Row>
                </Card>

                {/* Table */}
                <Card
                  bodyStyle={{ padding: 0 }}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
                >
                  <Table
                    columns={serviceColumns}
                    dataSource={services}
                    rowKey="name"
                    loading={isLoading}
                    pagination={{
                      defaultPageSize: 10,
                      showSizeChanger: true,
                      showTotal: (total) => `Total ${total} services`,
                    }}
                    scroll={{ y: 'calc(100vh - 520px)' }}
                  />
                </Card>
              </>
            ),
          },
          {
            key: 'abtests',
            label: (
              <span>
                <ExperimentOutlined />
                A/B Tests ({abTestStats.total})
              </span>
            ),
            children: (
              <Card
                bodyStyle={{ padding: 0 }}
                style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
              >
                <Table
                  columns={abTestColumns}
                  dataSource={abTests}
                  rowKey="experiment_id"
                  loading={isLoading}
                  pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `Total ${total} experiments`,
                  }}
                  scroll={{ y: 'calc(100vh - 460px)' }}
                  title={() => (
                    <Space>
                      <Button
                        type="primary"
                        size="small"
                        icon={<PlusOutlined />}
                        onClick={() => navigate('/serving/ab-tests/new')}
                      >
                        New A/B Test
                      </Button>
                    </Space>
                  )}
                />
              </Card>
            ),
          },
          {
            key: 'canaries',
            label: (
              <span>
                <RocketOutlined />
                Canary Deployments ({canaryStats.total})
              </span>
            ),
            children: (
              <Card
                bodyStyle={{ padding: 0 }}
                style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
              >
                <Table
                  columns={canaryColumns}
                  dataSource={canaryDeployments}
                  rowKey="deployment_id"
                  loading={isLoading}
                  pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `Total ${total} deployments`,
                  }}
                  scroll={{ y: 'calc(100vh - 460px)' }}
                  title={() => (
                    <Space>
                      <Button
                        type="primary"
                        size="small"
                        icon={<PlusOutlined />}
                        onClick={() => navigate('/serving/canaries/new')}
                      >
                        New Canary Deployment
                      </Button>
                    </Space>
                  )}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Metrics Modal */}
      <Modal
        title={
          <Space>
            Metrics
            {selectedServiceName && <Tag color="blue">{selectedServiceName}</Tag>}
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
          <Col span={12}>
            <Card size="small">
              <Statistic title="Request Count" value={selectedServiceMetrics.request_count || 0} />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="Success Rate"
                value={((selectedServiceMetrics.request_success_rate || 0) * 100).toFixed(2)}
                suffix="%"
                precision={2}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="Avg Latency"
                value={selectedServiceMetrics.avg_latency_ms || 0}
                suffix="ms"
                precision={1}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="P95 Latency"
                value={selectedServiceMetrics.p95_latency_ms || 0}
                suffix="ms"
                precision={1}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="P99 Latency"
                value={selectedServiceMetrics.p99_latency_ms || 0}
                suffix="ms"
                precision={1}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="Throughput"
                value={selectedServiceMetrics.throughput_per_second || 0}
                suffix="req/s"
                precision={1}
              />
            </Card>
          </Col>
        </Row>
      </Modal>
    </div>
  );
};

export default ServingListPage;
