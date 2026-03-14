/**
 * Kubernetes Operator Monitoring Page
 *
 * Provides monitoring and management for Kubernetes resources managed by operators.
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Tabs,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Tooltip,
  message,
  Progress,
  Badge,
} from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  ExpandOutlined,
  RocketOutlined,
  BookOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { TabsProps } from 'antd';
import { useOperatorStore } from '../../stores/operator';
import {
  ResourceState,
  OperatorType,
  NotebookResource,
  TrainingJobResource,
  InferenceServiceResource,
  ClusterStatus,
  RESOURCE_STATE_COLORS,
  RESOURCE_STATE_ICONS,
  DEFAULT_NOTEBOOK_IMAGES,
  GPU_PRESETS,
  STORAGE_PRESETS,
  CPU_PRESETS,
  MEMORY_PRESETS,
} from '../../types/operator';

const OperatorMonitorPage: React.FC = () => {
  const operatorStore = useOperatorStore();

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<OperatorType>(OperatorType.NOTEBOOK);
  const [clusterStatus, setClusterStatus] = useState<ClusterStatus | null>(null);
  const [selectedResource, setSelectedResource] = useState<any>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [scaleModalOpen, setScaleModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [scaleForm] = Form.useForm();

  // Fetch cluster status on mount
  useEffect(() => {
    fetchClusterStatus();
    fetchAllResources();
    const interval = setInterval(fetchAllResources, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [activeTab]);

  const fetchClusterStatus = async () => {
    try {
      const status = await operatorStore.fetchClusterStatus();
      setClusterStatus(status);
    } catch (error) {
      console.error('Failed to fetch cluster status:', error);
    }
  };

  const fetchAllResources = async () => {
    setLoading(true);
    try {
      await Promise.all([
        operatorStore.fetchNotebooks(),
        operatorStore.fetchTrainingJobs(),
        operatorStore.fetchInferenceServices(),
      ]);
    } catch (error) {
      console.error('Failed to fetch resources:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (type: OperatorType, name: string) => {
    try {
      if (type === OperatorType.NOTEBOOK) {
        await operatorStore.startNotebook(name);
      }
      message.success(`${type} ${name} started successfully`);
      await fetchAllResources();
    } catch (error) {
      message.error(`Failed to start ${type}: ${error}`);
    }
  };

  const handleStop = async (type: OperatorType, name: string) => {
    try {
      if (type === OperatorType.NOTEBOOK) {
        await operatorStore.stopNotebook(name);
      }
      message.success(`${type} ${name} stopped successfully`);
      await fetchAllResources();
    } catch (error) {
      message.error(`Failed to stop ${type}: ${error}`);
    }
  };

  const handleDelete = async (type: OperatorType, name: string) => {
    Modal.confirm({
      title: 'Confirm Delete',
      content: `Are you sure you want to delete ${type} ${name}?`,
      onOk: async () => {
        try {
          if (type === OperatorType.NOTEBOOK) {
            await operatorStore.deleteNotebook(name);
          } else if (type === OperatorType.TRAINING_JOB) {
            await operatorStore.deleteTrainingJob(name);
          } else if (type === OperatorType.INFERENCE_SERVICE) {
            await operatorStore.deleteInferenceService(name);
          }
          message.success(`${type} ${name} deleted successfully`);
          await fetchAllResources();
        } catch (error) {
          message.error(`Failed to delete ${type}: ${error}`);
        }
      },
    });
  };

  const handleScale = async () => {
    try {
      const values = await scaleForm.validateFields();
      await operatorStore.scaleInferenceService(selectedResource.name, values.replicas);
      message.success(`Service scaled to ${values.replicas} replicas`);
      setScaleModalOpen(false);
      await fetchAllResources();
    } catch (error) {
      message.error(`Failed to scale service: ${error}`);
    }
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      if (activeTab === OperatorType.NOTEBOOK) {
        await operatorStore.createNotebook(values);
      } else if (activeTab === OperatorType.TRAINING_JOB) {
        await operatorStore.createTrainingJob(values);
      } else if (activeTab === OperatorType.INFERENCE_SERVICE) {
        await operatorStore.createInferenceService(values);
      }
      message.success(`${activeTab} created successfully`);
      setCreateModalOpen(false);
      createForm.resetFields();
      await fetchAllResources();
    } catch (error) {
      message.error(`Failed to create ${activeTab}: ${error}`);
    }
  };

  const showDetail = (resource: any) => {
    setSelectedResource(resource);
    setDetailModalOpen(true);
  };

  const showScaleModal = (resource: InferenceServiceResource) => {
    setSelectedResource(resource);
    scaleForm.setFieldsValue({ replicas: resource.spec.replicas });
    setScaleModalOpen(true);
  };

  const getStateColor = (state: ResourceState) => {
    const colorMap: Record<ResourceState, string> = {
      [ResourceState.PENDING]: 'default',
      [ResourceState.CREATING]: 'processing',
      [ResourceState.RUNNING]: 'success',
      [ResourceState.UPDATING]: 'processing',
      [ResourceState.DELETING]: 'warning',
      [ResourceState.COMPLETED]: 'default',
      [ResourceState.FAILED]: 'error',
      [ResourceState.UNKNOWN]: 'default',
    };
    return colorMap[state] || 'default';
  };

  const getStateIcon = (state: ResourceState) => {
    return RESOURCE_STATE_ICONS[state] || '❓';
  };

  // Calculate statistics
  const notebooks = operatorStore.notebooks;
  const trainingJobs = operatorStore.trainingJobs;
  const inferenceServices = operatorStore.inferenceServices;

  const notebookStats = {
    total: notebooks.length,
    running: notebooks.filter((n) => n.status.phase === ResourceState.RUNNING).length,
    pending: notebooks.filter((n) => n.status.phase === ResourceState.PENDING).length,
    failed: notebooks.filter((n) => n.status.phase === ResourceState.FAILED).length,
  };

  const trainingStats = {
    total: trainingJobs.length,
    running: trainingJobs.filter((j) => j.status.phase === ResourceState.RUNNING).length,
    completed: trainingJobs.filter((j) => j.status.phase === ResourceState.COMPLETED).length,
    failed: trainingJobs.filter((j) => j.status.phase === ResourceState.FAILED).length,
  };

  const inferenceStats = {
    total: inferenceServices.length,
    running: inferenceServices.filter((s) => s.status.phase === ResourceState.RUNNING).length,
    totalReplicas: inferenceServices.reduce((sum, s) => sum + (s.status.replicas || 0), 0),
    readyReplicas: inferenceServices.reduce((sum, s) => sum + (s.status.readyReplicas || 0), 0),
  };

  // Notebook columns
  const notebookColumns = [
    {
      title: 'Name',
      dataIndex: ['metadata', 'name'],
      key: 'name',
      render: (name: string, record: NotebookResource) => (
        <Space>
          <a onClick={() => showDetail(record)}>{name}</a>
          {record.status.jupyterURL && (
            <Tooltip title="Open Jupyter">
              <Button type="link" size="small" icon={<BookOutlined />} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Namespace',
      dataIndex: ['metadata', 'namespace'],
      key: 'namespace',
    },
    {
      title: 'State',
      dataIndex: ['status', 'phase'],
      key: 'phase',
      render: (phase: ResourceState) => (
        <Tag color={getStateColor(phase)} icon={<span>{getStateIcon(phase)}</span>}>
          {phase}
        </Tag>
      ),
    },
    {
      title: 'Ready',
      key: 'ready',
      render: (_: any, record: NotebookResource) => (
        <span>
          {record.status.readyReplicas || 0} / {record.status.replicas || 0}
        </span>
      ),
    },
    {
      title: 'Image',
      dataIndex: ['spec', 'image'],
      key: 'image',
      ellipsis: true,
      render: (image: string) => (
        <Tooltip title={image}>
          <span>{image.split('/').pop()?.split(':')[0] || image}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Resources',
      key: 'resources',
      render: (_: any, record: NotebookResource) => (
        <Space size="small">
          <Tooltip title="CPU">
            <Tag>{record.spec.cpu}</Tag>
          </Tooltip>
          <Tooltip title="Memory">
            <Tag>{record.spec.memory}</Tag>
          </Tooltip>
          {record.spec.gpu && (
            <Tooltip title="GPU">
              <Tag color="blue">{record.spec.gpu} GPU</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: ['metadata', 'creationTimestamp'],
      key: 'created',
      render: (ts: string) => new Date(ts).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      render: (_: any, record: NotebookResource) => (
        <Space>
          {record.status.phase === ResourceState.RUNNING ? (
            <Tooltip title="Stop">
              <Button
                type="text"
                danger
                size="small"
                icon={<StopOutlined />}
                onClick={() => handleStop(OperatorType.NOTEBOOK, record.metadata.name)}
              />
            </Tooltip>
          ) : (
            <Tooltip title="Start">
              <Button
                type="text"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStart(OperatorType.NOTEBOOK, record.metadata.name)}
              />
            </Tooltip>
          )}
          <Tooltip title="Details">
            <Button
              type="text"
              size="small"
              icon={<ExpandOutlined />}
              onClick={() => showDetail(record)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(OperatorType.NOTEBOOK, record.metadata.name)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Training job columns
  const trainingColumns = [
    {
      title: 'Name',
      dataIndex: ['metadata', 'name'],
      key: 'name',
      render: (name: string, record: TrainingJobResource) => (
        <a onClick={() => showDetail(record)}>{name}</a>
      ),
    },
    {
      title: 'Namespace',
      dataIndex: ['metadata', 'namespace'],
      key: 'namespace',
    },
    {
      title: 'State',
      dataIndex: ['status', 'phase'],
      key: 'phase',
      render: (phase: ResourceState) => (
        <Tag color={getStateColor(phase)} icon={<span>{getStateIcon(phase)}</span>}>
          {phase}
        </Tag>
      ),
    },
    {
      title: 'Backend',
      dataIndex: ['spec', 'backend'],
      key: 'backend',
      render: (backend: string) => <Tag color="purple">{backend}</Tag>,
    },
    {
      title: 'Strategy',
      dataIndex: ['spec', 'strategy'],
      key: 'strategy',
    },
    {
      title: 'Nodes',
      key: 'nodes',
      render: (_: any, record: TrainingJobResource) => (
        <span>
          {record.spec.numNodes} × {record.spec.numProcessesPerNode}
        </span>
      ),
    },
    {
      title: 'GPU',
      dataIndex: ['spec', 'resources', 'gpu'],
      key: 'gpu',
      render: (gpu: number) => (gpu ? <Tag color="blue">{gpu} GPU</Tag> : '-'),
    },
    {
      title: 'Started',
      dataIndex: ['status', 'startedAt'],
      key: 'started',
      render: (ts?: string) => (ts ? new Date(ts).toLocaleString() : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_: any, record: TrainingJobResource) => (
        <Space>
          <Tooltip title="Details">
            <Button
              type="text"
              size="small"
              icon={<ExpandOutlined />}
              onClick={() => showDetail(record)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(OperatorType.TRAINING_JOB, record.metadata.name)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Inference service columns
  const inferenceColumns = [
    {
      title: 'Name',
      dataIndex: ['metadata', 'name'],
      key: 'name',
      render: (name: string, record: InferenceServiceResource) => (
        <Space>
          <a onClick={() => showDetail(record)}>{name}</a>
          {record.status.serviceURL && (
            <Tooltip title="Open Service">
              <Button type="link" size="small" icon={<RocketOutlined />} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Namespace',
      dataIndex: ['metadata', 'namespace'],
      key: 'namespace',
    },
    {
      title: 'State',
      dataIndex: ['status', 'phase'],
      key: 'phase',
      render: (phase: ResourceState) => (
        <Tag color={getStateColor(phase)} icon={<span>{getStateIcon(phase)}</span>}>
          {phase}
        </Tag>
      ),
    },
    {
      title: 'Replicas',
      key: 'replicas',
      render: (_: any, record: InferenceServiceResource) => {
        const ready = record.status.readyReplicas || 0;
        const total = record.status.replicas || 0;
        const percent = total > 0 ? (ready / total) * 100 : 0;
        return (
          <Space direction="vertical" size="small" style={{ width: 100 }}>
            <span>
              {ready} / {total}
            </span>
            <Progress percent={percent} size="small" status={ready === total ? 'success' : 'active'} />
          </Space>
        );
      },
    },
    {
      title: 'Predictor',
      dataIndex: ['spec', 'predictorType'],
      key: 'predictor',
      render: (type: string) => <Tag color="cyan">{type}</Tag>,
    },
    {
      title: 'Framework',
      dataIndex: ['spec', 'framework'],
      key: 'framework',
      render: (framework?: string) => (framework ? <Tag>{framework}</Tag> : '-'),
    },
    {
      title: 'Autoscaling',
      key: 'autoscaling',
      render: (_: any, record: InferenceServiceResource) => (
        <Space size="small">
          {record.spec.autoscalingEnabled ? (
            <Tag color="green">Enabled</Tag>
          ) : (
            <Tag>Disabled</Tag>
          )}
          <span>
            {record.spec.minReplicas}-{record.spec.maxReplicas}
          </span>
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: ['metadata', 'creationTimestamp'],
      key: 'created',
      render: (ts: string) => new Date(ts).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: InferenceServiceResource) => (
        <Space>
          <Tooltip title="Scale">
            <Button
              type="text"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => showScaleModal(record)}
            />
          </Tooltip>
          <Tooltip title="Details">
            <Button
              type="text"
              size="small"
              icon={<ExpandOutlined />}
              onClick={() => showDetail(record)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(OperatorType.INFERENCE_SERVICE, record.metadata.name)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const tabItems: TabsProps['items'] = [
    {
      key: OperatorType.NOTEBOOK,
      label: (
        <span>
          <BookOutlined />
          Notebooks ({notebookStats.total})
        </span>
      ),
      children: (
        <Table
          columns={notebookColumns}
          dataSource={notebooks}
          rowKey={(r) => r.metadata.uid}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      ),
    },
    {
      key: OperatorType.TRAINING_JOB,
      label: (
        <span>
          <ThunderboltOutlined />
          Training Jobs ({trainingStats.total})
        </span>
      ),
      children: (
        <Table
          columns={trainingColumns}
          dataSource={trainingJobs}
          rowKey={(r) => r.metadata.uid}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      ),
    },
    {
      key: OperatorType.INFERENCE_SERVICE,
      label: (
        <span>
          <RocketOutlined />
          Inference Services ({inferenceStats.total})
        </span>
      ),
      children: (
        <Table
          columns={inferenceColumns}
          dataSource={inferenceServices}
          rowKey={(r) => r.metadata.uid}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      ),
    },
  ];

  const renderCreateForm = () => {
    if (activeTab === OperatorType.NOTEBOOK) {
      return (
        <>
          <Form.Item name="name" label="Notebook Name" rules={[{ required: true }]}>
            <Input placeholder="my-notebook" />
          </Form.Item>
          <Form.Item name="image" label="Container Image" rules={[{ required: true }]}>
            <Select>
              {DEFAULT_NOTEBOOK_IMAGES.map((img) => (
                <Select.Option key={img.value} value={img.value}>
                  {img.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="cpu" label="CPU" initialValue="1000m">
                <Select>
                  {CPU_PRESETS.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="memory" label="Memory" initialValue="2Gi">
                <Select>
                  {MEMORY_PRESETS.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="gpu" label="GPU" initialValue={0}>
                <Select>
                  {GPU_PRESETS.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="storage" label="Storage" initialValue="10Gi">
            <Select>
              {STORAGE_PRESETS.map((opt) => (
                <Select.Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="auto_stop" label="Auto Stop" valuePropName="checked" initialValue={true}>
            <Select>
              <Select.Option value={true}>Yes</Select.Option>
              <Select.Option value={false}>No</Select.Option>
            </Select>
          </Form.Item>
        </>
      );
    } else if (activeTab === OperatorType.TRAINING_JOB) {
      return (
        <>
          <Form.Item name="name" label="Job Name" rules={[{ required: true }]}>
            <Input placeholder="my-training-job" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="backend" label="Backend" rules={[{ required: true }]} initialValue="pytorch">
                <Select>
                  <Select.Option value="pytorch">PyTorch</Select.Option>
                  <Select.Option value="tensorflow">TensorFlow</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="strategy" label="Strategy" rules={[{ required: true }]} initialValue="ddp">
                <Select>
                  <Select.Option value="ddp">DDP</Select.Option>
                  <Select.Option value="mirrored">Mirrored</Select.Option>
                  <Select.Option value="single">Single Node</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="entry_point" label="Entry Point" rules={[{ required: true }]}>
            <Input placeholder="train.py" />
          </Form.Item>
          <Form.Item name="model_uri" label="Model URI" rules={[{ required: true }]}>
            <Input placeholder="s3://my-bucket/models/" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="num_nodes" label="Number of Nodes" initialValue={1}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="num_processes_per_node" label="Processes per Node" initialValue={1}>
                <InputNumber min={1} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </>
      );
    } else if (activeTab === OperatorType.INFERENCE_SERVICE) {
      return (
        <>
          <Form.Item name="name" label="Service Name" rules={[{ required: true }]}>
            <Input placeholder="my-inference-service" />
          </Form.Item>
          <Form.Item name="model_uri" label="Model URI" rules={[{ required: true }]}>
            <Input placeholder="s3://my-bucket/models/my-model" />
          </Form.Item>
          <Form.Item name="predictor_type" label="Predictor Type" initialValue="custom">
            <Select>
              <Select.Option value="custom">Custom</Select.Option>
              <Select.Option value="tensorflow">TensorFlow</Select.Option>
              <Select.Option value="pytorch">PyTorch</Select.Option>
              <Select.Option value="sklearn">Scikit-learn</Select.Option>
              <Select.Option value="xgboost">XGBoost</Select.Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="replicas" label="Replicas" initialValue={1}>
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="min_replicas" label="Min Replicas" initialValue={1}>
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_replicas" label="Max Replicas" initialValue={3}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="autoscaling_enabled" label="Enable Autoscaling" valuePropName="checked">
            <Select>
              <Select.Option value={true}>Yes</Select.Option>
              <Select.Option value={false}>No</Select.Option>
            </Select>
          </Form.Item>
        </>
      );
    }
    return null;
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Kubernetes Operator Monitor</h1>
          <p className="text-gray-500">Manage platform resources via Kubernetes operators</p>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAllResources} loading={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            Create Resource
          </Button>
        </Space>
      </div>

      {/* Statistics */}
      <Row gutter={16} className="mb-6">
        <Col span={6}>
          <Card>
            <Statistic
              title="Notebooks"
              value={notebookStats.total}
              prefix={<BookOutlined />}
              suffix={
                <span className="text-sm text-gray-500">
                  {notebookStats.running} running
                </span>
              }
            />
            <div className="mt-2 space-x-1">
              <Badge status="success" text={notebookStats.running} />
              <Badge status="processing" text={notebookStats.pending} />
              <Badge status="error" text={notebookStats.failed} />
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Training Jobs"
              value={trainingStats.total}
              prefix={<ThunderboltOutlined />}
              suffix={
                <span className="text-sm text-gray-500">
                  {trainingStats.running} running
                </span>
              }
            />
            <div className="mt-2 space-x-1">
              <Badge status="success" text={trainingStats.running} />
              <Badge status="default" text={trainingStats.completed} />
              <Badge status="error" text={trainingStats.failed} />
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Inference Services"
              value={inferenceStats.total}
              prefix={<RocketOutlined />}
              suffix={
                <span className="text-sm text-gray-500">
                  {inferenceStats.totalReplicas} replicas
                </span>
              }
            />
            <div className="mt-2">
              <Progress
                percent={
                  inferenceStats.totalReplicas > 0
                    ? Math.round((inferenceStats.readyReplicas / inferenceStats.totalReplicas) * 100)
                    : 0
                }
                size="small"
                status="active"
              />
              <span className="text-xs text-gray-500">
                {inferenceStats.readyReplicas} / {inferenceStats.totalReplicas} ready
              </span>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Cluster Status"
              value={clusterStatus ? 'Healthy' : 'Unknown'}
              prefix={
                clusterStatus ? (
                  <Badge status="success" />
                ) : (
                  <Badge status="processing" />
                )
              }
            />
            {clusterStatus && (
              <div className="mt-2 text-xs text-gray-500">
                <div>CRDs: {Object.values(clusterStatus.crds).filter((v) => v.installed).length} / 3</div>
                <div>
                  Operators:{' '}
                  {Object.values(clusterStatus.operators).filter((o) => o.running).length} / 3
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Resource Tabs */}
      <Card>
        <Tabs activeKey={activeTab} items={tabItems} onChange={(key) => setActiveTab(key as OperatorType)} />
      </Card>

      {/* Detail Modal */}
      <Modal
        title={
          <Space>
            <span>{selectedResource?.metadata?.name}</span>
            {selectedResource?.status?.phase && (
              <Tag color={getStateColor(selectedResource.status.phase)}>
                {selectedResource.status.phase}
              </Tag>
            )}
          </Space>
        }
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        width={800}
        footer={null}
      >
        {selectedResource && (
          <div className="space-y-4">
            <Card title="Metadata" size="small">
              <Row gutter={16}>
                <Col span={12}>
                  <div className="text-sm text-gray-500">Name</div>
                  <div>{selectedResource.metadata.name}</div>
                </Col>
                <Col span={12}>
                  <div className="text-sm text-gray-500">Namespace</div>
                  <div>{selectedResource.metadata.namespace}</div>
                </Col>
                <Col span={12}>
                  <div className="text-sm text-gray-500">UID</div>
                  <div className="text-xs">{selectedResource.metadata.uid}</div>
                </Col>
                <Col span={12}>
                  <div className="text-sm text-gray-500">Created</div>
                  <div>
                    {selectedResource.metadata.creationTimestamp &&
                      new Date(selectedResource.metadata.creationTimestamp).toLocaleString()}
                  </div>
                </Col>
              </Row>
            </Card>

            <Card title="Status" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <div className="text-sm text-gray-500">Phase</div>
                  <div>
                    <Tag color={getStateColor(selectedResource.status.phase)}>
                      {selectedResource.status.phase}
                    </Tag>
                  </div>
                </Col>
                <Col span={8}>
                  <div className="text-sm text-gray-500">Replicas</div>
                  <div>
                    {selectedResource.status.readyReplicas || 0} / {selectedResource.status.replicas || 0}
                  </div>
                </Col>
                <Col span={8}>
                  <div className="text-sm text-gray-500">Generation</div>
                  <div>{selectedResource.status.observedGeneration}</div>
                </Col>
              </Row>
              {selectedResource.status.conditions && selectedResource.status.conditions.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-sm font-medium">Conditions</div>
                  {selectedResource.status.conditions.map((cond: any, idx: number) => (
                    <Tag key={idx} color={cond.status === 'True' ? 'success' : 'warning'} className="mb-1">
                      {cond.type}: {cond.status}
                      {cond.reason && ` (${cond.reason})`}
                    </Tag>
                  ))}
                </div>
              )}
              {selectedResource.status.errorMessage && (
                <div className="mt-4">
                  <div className="mb-1 text-sm font-medium text-red-500">Error</div>
                  <div className="text-sm text-red-500">{selectedResource.status.errorMessage}</div>
                </div>
              )}
            </Card>

            <Card title="Specification" size="small">
              <pre className="overflow-auto bg-gray-50 p-3 text-xs">
                {JSON.stringify(selectedResource.spec, null, 2)}
              </pre>
            </Card>

            {selectedResource.status.jupyterURL && (
              <Card title="Access URLs" size="small">
                <Space direction="vertical">
                  <div>
                    <span className="mr-2 text-sm text-gray-500">Jupyter:</span>
                    <a href={selectedResource.status.jupyterURL} target="_blank" rel="noopener noreferrer">
                      {selectedResource.status.jupyterURL}
                    </a>
                  </div>
                  {selectedResource.status.tensorboardURL && (
                    <div>
                      <span className="mr-2 text-sm text-gray-500">TensorBoard:</span>
                      <a
                        href={selectedResource.status.tensorboardURL}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {selectedResource.status.tensorboardURL}
                      </a>
                    </div>
                  )}
                </Space>
              </Card>
            )}

            {selectedResource.status.serviceURL && (
              <Card title="Service URL" size="small">
                <a href={selectedResource.status.serviceURL} target="_blank" rel="noopener noreferrer">
                  {selectedResource.status.serviceURL}
                </a>
              </Card>
            )}
          </div>
        )}
      </Modal>

      {/* Scale Modal */}
      <Modal
        title={`Scale ${selectedResource?.metadata?.name || 'Service'}`}
        open={scaleModalOpen}
        onOk={handleScale}
        onCancel={() => setScaleModalOpen(false)}
      >
        <Form form={scaleForm} layout="vertical">
          <Form.Item
            name="replicas"
            label="Number of Replicas"
            rules={[{ required: true, type: 'number', min: 0, max: 100 }]}
          >
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Modal */}
      <Modal
        title={`Create ${activeTab
          .split('-')
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ')}`}
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        width={600}
      >
        <Form form={createForm} layout="vertical">
          {renderCreateForm()}
        </Form>
      </Modal>
    </div>
  );
};

export default OperatorMonitorPage;
