/**
 * GPU Pool Monitoring Page
 *
 * Provides monitoring and management for GPU resources and VGPU allocations.
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
  Descriptions,
  Switch,
  Slider,
} from 'antd';
import {
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  FireOutlined,
  ThunderboltOutlined,
  BlocksOutlined,
  SettingOutlined,
  StopOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { TabsProps } from 'antd';
import { useGPUStore, selectHealthyGPUs, selectAvailableGPUs } from '../../stores/gpu';
import {
  GPUType,
  GPUAllocationStrategy,
  SchedulingPolicy,
  TaskPriority,
  UtilizationStatus,
  VGPU_MEMORY_PRESETS,
  VGPU_COUNT_PRESETS,
  GPU_TYPES_FOR_REQUEST,
  ALLOCATION_STRATEGY_LABELS,
  PRIORITY_COLORS,
  PRIORITY_LABELS,
  UTILIZATION_STATUS_COLORS,
  GPU_TYPE_COLORS,
  GPU_TYPE_ICONS,
  TEMPERATURE_THRESHOLDS,
} from '../../types/gpu';

const GPUPoolMonitorPage: React.FC = () => {
  const gpuStore = useGPUStore();

  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [createVGPUModalOpen, setCreateVGPUModalOpen] = useState(false);
  const [requestGPUModalOpen, setRequestGPUModalOpen] = useState(false);
  const [gpuDetailModalOpen, setGpuDetailModalOpen] = useState(false);
  const [createVGPUForm] = Form.useForm();
  const [requestGPUForm] = Form.useForm();

  // Fetch data on mount and set up refresh
  useEffect(() => {
    fetchAllData();
    if (autoRefresh) {
      const interval = setInterval(fetchAllData, 10000); // Poll every 10s
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        gpuStore.fetchPoolStatus(),
        gpuStore.fetchMonitoringSummary(),
        gpuStore.fetchGPUTypes(),
        gpuStore.listTasks(),
      ]);
    } catch (error) {
      console.error('Failed to fetch GPU data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateVGPU = async () => {
    try {
      const values = await createVGPUForm.validateFields();
      await gpuStore.createVGPUInstances({
        gpuId: values.gpu_id,
        count: values.count,
        memoryPerVgpu: values.memory_per_vgpu,
        cpuCoresPerVgpu: values.cpu_cores_per_vgpu || 1.0,
      });
      message.success('VGPU instances created successfully');
      setCreateVGPUModalOpen(false);
      createVGPUForm.resetFields();
      await fetchAllData();
    } catch (error: any) {
      message.error(`Failed to create VGPU instances: ${error.message || error}`);
    }
  };

  const handleRequestGPU = async () => {
    try {
      const values = await requestGPUForm.validateFields();
      const result = await gpuStore.requestGPU({
        resourceName: values.resource_name,
        vgpuCount: values.vgpu_count,
        gpuType: values.gpu_type,
        memoryMb: values.memory_mb,
        strategy: values.strategy,
        priority: values.priority,
        estimatedDurationMinutes: values.estimated_duration_minutes,
      });

      if (result.scheduled) {
        message.success(`GPU allocated successfully: ${result.allocation_id}`);
      } else {
        message.warning(`GPU request queued: ${result.reason}. Position: ${result.queue_position}`);
      }
      setRequestGPUModalOpen(false);
      requestGPUForm.resetFields();
      await fetchAllData();
    } catch (error: any) {
      message.error(`Failed to request GPU: ${error.message || error}`);
    }
  };

  const handleReleaseGPU = async (resourceName: string) => {
    Modal.confirm({
      title: 'Release GPU Allocation',
      content: `Are you sure you want to release GPU allocation for ${resourceName}?`,
      onOk: async () => {
        try {
          await gpuStore.releaseGPU(resourceName);
          message.success(`GPU allocation released for ${resourceName}`);
          await fetchAllData();
        } catch (error: any) {
          message.error(`Failed to release GPU: ${error.message || error}`);
        }
      },
    });
  };

  const handleCancelTask = async (taskId: string) => {
    Modal.confirm({
      title: 'Cancel Task',
      content: `Are you sure you want to cancel task ${taskId}?`,
      onOk: async () => {
        try {
          await gpuStore.cancelTask(taskId);
          message.success(`Task ${taskId} cancelled`);
          await fetchAllData();
        } catch (error: any) {
          message.error(`Failed to cancel task: ${error.message || error}`);
        }
      },
    });
  };

  const showGPUDetails = async (gpuId: string) => {
    try {
      await gpuStore.fetchGPUDetails(gpuId);
      gpuStore.selectGpu(gpuId);
      setGpuDetailModalOpen(true);
    } catch (error: any) {
      message.error(`Failed to fetch GPU details: ${error.message || error}`);
    }
  };

  // GPU columns
  const gpuColumns = [
    {
      title: 'GPU',
      dataIndex: 'gpu_id',
      key: 'gpu',
      render: (_: string, record: any) => (
        <Space>
          <span style={{ color: GPU_TYPE_COLORS[record.type] || '#999' }}>
            {GPU_TYPE_ICONS[record.type] || '🖥️'}
          </span>
          <a onClick={() => showGPUDetails(record.gpu_id)}>{record.gpu_id}</a>
        </Space>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: GPUType) => (
        <Tag color={GPU_TYPE_COLORS[type]}>{type}</Tag>
      ),
    },
    {
      title: 'Memory',
      key: 'memory',
      render: (_: any, record: any) => {
        const used = record.used_memory_mb;
        const total = record.total_memory_mb;
        const percent = (used / total) * 100;
        return (
          <Space direction="vertical" size="small" style={{ width: 120 }}>
            <Progress percent={Math.round(percent)} size="small" />
            <span className="text-xs text-gray-500">
              {(used / 1024).toFixed(1)} / {(total / 1024).toFixed(1)} GB
            </span>
          </Space>
        );
      },
    },
    {
      title: 'Utilization',
      dataIndex: 'utilization_percent',
      key: 'utilization',
      render: (utilization: number) => {
        const status =
          utilization < 50 ? UtilizationStatus.LOW : utilization < 80 ? UtilizationStatus.MEDIUM : UtilizationStatus.HIGH;
        return (
          <Tag color={UTILIZATION_STATUS_COLORS[status]} icon={<ThunderboltOutlined />}>
            {utilization.toFixed(1)}%
          </Tag>
        );
      },
    },
    {
      title: 'Temperature',
      dataIndex: 'temperature_celsius',
      key: 'temperature',
      render: (temp: number) => {
        const color = temp > TEMPERATURE_THRESHOLDS.CRITICAL ? 'error' : temp > TEMPERATURE_THRESHOLDS.WARNING ? 'warning' : 'success';
        const icon = temp > TEMPERATURE_THRESHOLDS.CRITICAL ? <FireOutlined /> : <CheckCircleOutlined />;
        return (
          <Tag color={color} icon={icon}>
            {temp.toFixed(0)}°C
          </Tag>
        );
      },
    },
    {
      title: 'VGPU',
      key: 'vgpu',
      render: (_: any, record: any) => (
        <Space>
          <span>{record.active_vgpus}/{record.vgpu_instances}</span>
          {record.mig_enabled && <Tag color="blue">MIG</Tag>}
        </Space>
      ),
    },
    {
      title: 'Health',
      dataIndex: 'healthy',
      key: 'healthy',
      render: (healthy: boolean) => (
        <Badge status={healthy ? 'success' : 'error'} text={healthy ? 'Healthy' : 'Unhealthy'} />
      ),
    },
  ];

  // Allocation columns
  const allocationColumns = [
    {
      title: 'Allocation ID',
      dataIndex: 'allocation_id',
      key: 'allocation_id',
      ellipsis: true,
    },
    {
      title: 'Resource',
      dataIndex: 'resource_name',
      key: 'resource_name',
    },
    {
      title: 'GPU',
      dataIndex: 'gpu_id',
      key: 'gpu_id',
    },
    {
      title: 'VGPU Count',
      dataIndex: 'vgpu_count',
      key: 'vgpu_count',
      render: (count: number) => <Tag>{count} VGPU</Tag>,
    },
    {
      title: 'Strategy',
      dataIndex: 'strategy',
      key: 'strategy',
      render: (strategy: GPUAllocationStrategy) => (
        <Tag>{ALLOCATION_STRATEGY_LABELS[strategy]}</Tag>
      ),
    },
    {
      title: 'Memory',
      dataIndex: 'memory_mb',
      key: 'memory_mb',
      render: (memory: number) => `${(memory / 1024).toFixed(1)} GB`,
    },
    {
      title: 'Allocated At',
      dataIndex: 'allocated_at',
      key: 'allocated_at',
      render: (ts: string) => new Date(ts).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, record: any) => (
        <Tooltip title="Release">
          <Button
            type="text"
            danger
            size="small"
            icon={<StopOutlined />}
            onClick={() => handleReleaseGPU(record.resource_name)}
          />
        </Tooltip>
      ),
    },
  ];

  // Task columns
  const taskColumns = [
    {
      title: 'Task ID',
      dataIndex: 'task_id',
      key: 'task_id',
      ellipsis: true,
    },
    {
      title: 'Resource',
      dataIndex: 'resource_name',
      key: 'resource_name',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const color = status === 'running' ? 'success' : status === 'completed' ? 'default' : 'processing';
        return <Tag color={color}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: TaskPriority) => (
        <Tag color={PRIORITY_COLORS[priority]}>{PRIORITY_LABELS[priority]}</Tag>
      ),
    },
    {
      title: 'VGPU Count',
      dataIndex: 'vgpu_count',
      key: 'vgpu_count',
    },
    {
      title: 'Strategy',
      dataIndex: 'strategy',
      key: 'strategy',
      render: (strategy: GPUAllocationStrategy) => ALLOCATION_STRATEGY_LABELS[strategy],
    },
    {
      title: 'Wait Time',
      dataIndex: 'wait_time_seconds',
      key: 'wait_time_seconds',
      render: (seconds: number) => {
        if (seconds < 60) return `${seconds.toFixed(0)}s`;
        return `${(seconds / 60).toFixed(1)}m`;
      },
    },
    {
      title: 'Run Time',
      dataIndex: 'run_time_seconds',
      key: 'run_time_seconds',
      render: (seconds: number) => {
        if (!seconds || seconds === 0) return '-';
        if (seconds < 60) return `${seconds.toFixed(0)}s`;
        return `${(seconds / 60).toFixed(1)}m`;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, record: any) => (
        record.status !== 'completed' && (
          <Tooltip title="Cancel">
            <Button
              type="text"
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleCancelTask(record.task_id)}
            />
          </Tooltip>
        )
      ),
    },
  ];

  const tabItems: TabsProps['items'] = [
    {
      key: 'overview',
      label: (
        <span>
          <BlocksOutlined />
          Overview
        </span>
      ),
      children: (
        <div>
          {/* Monitoring Summary */}
          <Row gutter={16} className="mb-6">
            <Col span={6}>
              <Card>
                <Statistic
                  title="Total GPUs"
                  value={gpuStore.poolStatus?.cluster_stats.total_gpus || 0}
                  prefix={<BlocksOutlined />}
                  suffix={
                    <span className="text-sm text-gray-500">
                      {gpuStore.poolStatus?.cluster_stats.healthy_gpus || 0} healthy
                    </span>
                  }
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Avg Utilization"
                  value={gpuStore.monitoringSummary?.avg_utilization_percent?.toFixed(1) || 0}
                  suffix="%"
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{
                    color:
                      (gpuStore.monitoringSummary?.avg_utilization_percent || 0) > 80
                        ? '#ff4d4f'
                        : undefined,
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Active Allocations"
                  value={gpuStore.monitoringSummary?.active_allocations || 0}
                  prefix={<CheckCircleOutlined />}
                />
                <div className="mt-2 text-xs text-gray-500">
                  {gpuStore.monitoringSummary?.total_vgpu_instances || 0} VGPU instances
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Pending Tasks"
                  value={gpuStore.monitoringSummary?.pending_tasks || 0}
                  prefix={<PlayCircleOutlined />}
                />
                <div className="mt-2 text-xs text-gray-500">
                  {gpuStore.monitoringSummary?.running_tasks || 0} running
                </div>
              </Card>
            </Col>
          </Row>

          {/* GPU Grid */}
          <Card
            title="GPU Pool"
            extra={
              <Space>
                <Switch
                  checked={autoRefresh}
                  onChange={setAutoRefresh}
                  checkedChildren="Auto"
                  unCheckedChildren="Manual"
                />
                <Button icon={<ReloadOutlined />} onClick={fetchAllData} loading={loading}>
                  Refresh
                </Button>
              </Space>
            }
          >
            <Table
              columns={gpuColumns}
              dataSource={gpuStore.gpus}
              rowKey="gpu_id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'allocations',
      label: (
        <span>
          <CheckCircleOutlined />
          Allocations
        </span>
      ),
      children: (
        <Card
          title="GPU Allocations"
          extra={
            <Space>
              <Button icon={<PlusOutlined />} onClick={() => setRequestGPUModalOpen(true)}>
                Request GPU
              </Button>
              <Button icon={<ReloadOutlined />} onClick={fetchAllData} loading={loading}>
                Refresh
              </Button>
            </Space>
          }
        >
          <Table
            columns={allocationColumns}
            dataSource={gpuStore.allocations}
            rowKey="allocation_id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'tasks',
      label: (
        <span>
          <PlayCircleOutlined />
          Tasks
        </span>
      ),
      children: (
        <Card
          title="GPU Tasks"
          extra={
            <Space>
              <Button icon={<PlusOutlined />} onClick={() => setRequestGPUModalOpen(true)}>
                Submit Task
              </Button>
              <Button icon={<ReloadOutlined />} onClick={fetchAllData} loading={loading}>
                Refresh
              </Button>
            </Space>
          }
        >
          <Table
            columns={taskColumns}
            dataSource={gpuStore.tasks}
            rowKey="task_id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'vgpu',
      label: (
        <span>
          <BlocksOutlined />
          VGPU Instances
        </span>
      ),
      children: (
        <Card
          title="Virtual GPU Instances"
          extra={
            <Space>
              <Button icon={<PlusOutlined />} onClick={() => setCreateVGPUModalOpen(true)}>
                Create VGPU
              </Button>
              <Button icon={<ReloadOutlined />} onClick={() => gpuStore.fetchVGPUInstances()} loading={loading}>
                Refresh
              </Button>
            </Space>
          }
        >
          <Table
            columns={[
              {
                title: 'VGPU ID',
                dataIndex: 'vgpu_id',
                key: 'vgpu_id',
              },
              {
                title: 'Parent GPU',
                dataIndex: 'parent_gpu_id',
                key: 'parent_gpu_id',
              },
              {
                title: 'Memory',
                dataIndex: 'memory_mb',
                key: 'memory_mb',
                render: (memory: number) => `${(memory / 1024).toFixed(1)} GB`,
              },
              {
                title: 'Allocated To',
                dataIndex: 'allocated_to',
                key: 'allocated_to',
                render: (allocated: string | null) => (
                  allocated ? <Tag color="blue">{allocated}</Tag> : <Tag>Available</Tag>
                ),
              },
              {
                title: 'Allocation Type',
                dataIndex: 'allocation_type',
                key: 'allocation_type',
                render: (type: GPUAllocationStrategy | null) =>
                  type ? <Tag>{ALLOCATION_STRATEGY_LABELS[type]}</Tag> : '-',
              },
              {
                title: 'Utilization',
                dataIndex: 'utilization_percent',
                key: 'utilization_percent',
                render: (utilization: number) => `${utilization.toFixed(1)}%`,
              },
            ]}
            dataSource={gpuStore.vgpuInstances}
            rowKey="vgpu_id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">GPU Pool Manager</h1>
          <p className="text-gray-500">Monitor and manage GPU resources and VGPU allocations</p>
        </div>
        <Space>
          <Switch
            checked={autoRefresh}
            onChange={setAutoRefresh}
            checkedChildren="Auto Refresh"
            unCheckedChildren="Manual"
          />
          <Button icon={<ReloadOutlined />} onClick={fetchAllData} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {/* Alert for unhealthy GPUs */}
      {gpuStore.gpus.some((g) => !g.healthy) && (
        <Card className="mb-4 bg-yellow-50 border-yellow-200">
          <Space>
            <WarningOutlined className="text-yellow-500" />
            <span className="font-medium">Warning: Some GPUs are unhealthy</span>
            <span className="text-sm text-gray-600">
              {gpuStore.gpus.filter((g) => !g.healthy).length} GPUs need attention
            </span>
          </Space>
        </Card>
      )}

      {/* Main Tabs */}
      <Tabs activeKey={activeTab} items={tabItems} onChange={setActiveTab} />

      {/* Create VGPU Modal */}
      <Modal
        title="Create Virtual GPU Instances"
        open={createVGPUModalOpen}
        onOk={handleCreateVGPU}
        onCancel={() => {
          setCreateVGPUModalOpen(false);
          createVGPUForm.resetFields();
        }}
      >
        <Form form={createVGPUForm} layout="vertical">
          <Form.Item
            name="gpu_id"
            label="Parent GPU"
            rules={[{ required: true }]}
          >
            <Select placeholder="Select a GPU">
              {gpuStore.gpus.map((gpu) => (
                <Select.Option key={gpu.gpu_id} value={gpu.gpu_id}>
                  {gpu.gpu_id} - {gpu.name} ({(gpu.available_memory_mb / 1024).toFixed(1)} GB available)
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="count"
            label="Number of VGPU Instances"
            rules={[{ required: true }]}
            initialValue={1}
          >
            <Slider min={1} max={8} marks={{ 1: '1', 4: '4', 8: '8' }} />
          </Form.Item>
          <Form.Item
            name="memory_per_vgpu"
            label="Memory per VGPU (MB)"
            rules={[{ required: true }]}
          >
            <Select>
              {VGPU_MEMORY_PRESETS.map((preset) => (
                <Select.Option key={preset.value} value={preset.value}>
                  {preset.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="cpu_cores_per_vgpu" label="CPU Cores per VGPU" initialValue={1.0}>
            <InputNumber min={0.1} max={128} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Request GPU Modal */}
      <Modal
        title="Request GPU Allocation"
        open={requestGPUModalOpen}
        onOk={handleRequestGPU}
        onCancel={() => {
          setRequestGPUModalOpen(false);
          requestGPUForm.resetFields();
        }}
        width={600}
      >
        <Form form={requestGPUForm} layout="vertical">
          <Form.Item
            name="resource_name"
            label="Resource Name"
            rules={[{ required: true }]}
            tooltip="Unique identifier for your resource (e.g., training-job-123)"
          >
            <Input placeholder="my-resource" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="vgpu_count" label="VGPU Count" initialValue={1}>
                <Select>
                  {VGPU_COUNT_PRESETS.map((preset) => (
                    <Select.Option key={preset.value} value={preset.value}>
                      {preset.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="strategy" label="Allocation Strategy" initialValue={GPUAllocationStrategy.EXCLUSIVE}>
                <Select>
                  <Select.Option value={GPUAllocationStrategy.EXCLUSIVE}>
                    {ALLOCATION_STRATEGY_LABELS[GPUAllocationStrategy.EXCLUSIVE]}
                  </Select.Option>
                  <Select.Option value={GPUAllocationStrategy.INTERLEAVED}>
                    {ALLOCATION_STRATEGY_LABELS[GPUAllocationStrategy.INTERLEAVED]}
                  </Select.Option>
                  <Select.Option value={GPUAllocationStrategy.MIG}>
                    {ALLOCATION_STRATEGY_LABELS[GPUAllocationStrategy.MIG]}
                  </Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="gpu_type" label="GPU Type (Optional)">
                <Select placeholder="Any GPU type" allowClear>
                  {GPU_TYPES_FOR_REQUEST.map((type) => (
                    <Select.Option key={type.value} value={type.value}>
                      {type.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="memory_mb" label="Memory per VGPU (MB, Optional)">
                <Select placeholder="Auto" allowClear>
                  {VGPU_MEMORY_PRESETS.map((preset) => (
                    <Select.Option key={preset.value} value={preset.value}>
                      {preset.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="priority" label="Priority" initialValue={TaskPriority.NORMAL}>
                <Select>
                  <Select.Option value={TaskPriority.LOW}>
                    {PRIORITY_LABELS[TaskPriority.LOW]}
                  </Select.Option>
                  <Select.Option value={TaskPriority.NORMAL}>
                    {PRIORITY_LABELS[TaskPriority.NORMAL]}
                  </Select.Option>
                  <Select.Option value={TaskPriority.HIGH}>
                    {PRIORITY_LABELS[TaskPriority.HIGH]}
                  </Select.Option>
                  <Select.Option value={TaskPriority.URGENT}>
                    {PRIORITY_LABELS[TaskPriority.URGENT]}
                  </Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="estimated_duration_minutes" label="Duration (Minutes, Optional)">
                <InputNumber min={1} max={10080} style={{ width: '100%' }} placeholder="e.g., 60" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* GPU Detail Modal */}
      <Modal
        title={
          <Space>
            <span>GPU Details: {gpuStore.selectedGpuDetails?.gpu_id}</span>
            {gpuStore.selectedGpuDetails?.healthy ? (
              <Badge status="success" text="Healthy" />
            ) : (
              <Badge status="error" text="Unhealthy" />
            )}
          </Space>
        }
        open={gpuDetailModalOpen}
        onCancel={() => {
          setGpuDetailModalOpen(false);
          gpuStore.selectGpu(null);
        }}
        width={800}
        footer={null}
      >
        {gpuStore.selectedGpuDetails && (
          <div>
            <Card title="Overview" size="small" className="mb-4">
              <Descriptions column={3} size="small">
                <Descriptions.Item label="Name">{gpuStore.selectedGpuDetails.name}</Descriptions.Item>
                <Descriptions.Item label="Type">
                  <Tag color={GPU_TYPE_COLORS[gpuStore.selectedGpuDetails.type as GPUType]}>
                    {gpuStore.selectedGpuDetails.type}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="CUDA Cores">
                  {gpuStore.selectedGpuDetails.cuda_cores.toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Total Memory">
                  {(gpuStore.selectedGpuDetails.total_memory_mb / 1024).toFixed(1)} GB
                </Descriptions.Item>
                <Descriptions.Item label="Available Memory">
                  {(gpuStore.selectedGpuDetails.available_memory_mb / 1024).toFixed(1)} GB
                </Descriptions.Item>
                <Descriptions.Item label="Utilization">
                  {gpuStore.selectedGpuDetails.utilization_percent.toFixed(1)}%
                </Descriptions.Item>
                <Descriptions.Item label="Temperature">
                  <Tag
                    color={
                      gpuStore.selectedGpuDetails.temperature_celsius > 85
                        ? 'error'
                        : gpuStore.selectedGpuDetails.temperature_celsius > 75
                        ? 'warning'
                        : 'success'
                    }
                  >
                    {gpuStore.selectedGpuDetails.temperature_celsius.toFixed(0)}°C
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Power">
                  {gpuStore.selectedGpuDetails.power_draw_watts.toFixed(0)}W
                </Descriptions.Item>
                <Descriptions.Item label="MIG Enabled">
                  {gpuStore.selectedGpuDetails.mig_enabled ? (
                    <Tag color="blue">Yes</Tag>
                  ) : (
                    <Tag>No</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Driver Info" size="small" className="mb-4">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="Driver Version">
                  {gpuStore.selectedGpuDetails.driver_version}
                </Descriptions.Item>
                <Descriptions.Item label="CUDA Version">
                  {gpuStore.selectedGpuDetails.cuda_version}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="VGPU Instances" size="small">
              <Table
                columns={[
                  {
                    title: 'VGPU ID',
                    dataIndex: 'vgpu_id',
                    key: 'vgpu_id',
                  },
                  {
                    title: 'Index',
                    dataIndex: 'vgpu_index',
                    key: 'vgpu_index',
                  },
                  {
                    title: 'Memory',
                    dataIndex: 'memory_mb',
                    key: 'memory_mb',
                    render: (memory: number) => `${(memory / 1024).toFixed(1)} GB`,
                  },
                  {
                    title: 'Status',
                    key: 'status',
                    render: (_: any, vgpu: any) =>
                      vgpu.is_available ? (
                        <Tag color="success">Available</Tag>
                      ) : (
                        <Tag color="blue">Allocated to {vgpu.allocated_to}</Tag>
                      ),
                  },
                  {
                    title: 'Utilization',
                    dataIndex: 'utilization_percent',
                    key: 'utilization_percent',
                    render: (utilization: number) => `${utilization.toFixed(1)}%`,
                  },
                ]}
                dataSource={gpuStore.selectedGpuDetails.vgpu_instances}
                rowKey="vgpu_id"
                pagination={false}
                size="small"
              />
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default GPUPoolMonitorPage;
