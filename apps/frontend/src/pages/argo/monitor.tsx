/**
 * Argo Workflows Monitor Page
 *
 * Monitor and manage Argo workflows.
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
  Descriptions,
  Typography,
  Timeline,
  Spin,
  Empty,
  Progress,
} from 'antd';
import {
  ReloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  MoreOutlined,
  RocketOutlined,
  ClusterOutlined,
  FileTextOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  WorkflowPhase,
  WorkflowListItem,
  WorkflowStatus,
  WORKFLOW_PHASE_COLORS,
  WORKFLOW_PHASE_ICONS,
  ClusterInfo,
} from '@/types/argo';
import { api } from '@/services/api';

const { Text, Title, Paragraph } = Typography;
const { Search } = Input;

const ArgoMonitorPage: React.FC = () => {
  const navigate = useNavigate();

  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowListItem | null>(null);
  const [nodes, setNodes] = useState<Record<string, any>>({});
  const [clusterInfo, setClusterInfo] = useState<ClusterInfo | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [logsModalOpen, setLogsModalOpen] = useState(false);

  const [namespace, setNamespace] = useState('default');
  const [phaseFilter, setPhaseFilter] = useState<string[]>([]);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    fetchWorkflows();
    fetchClusterInfo();
  }, [namespace, phaseFilter]);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (phaseFilter.length > 0) {
        params.append('phases', phaseFilter.join(','));
      }

      const response = await api.get(`/argo/workflows?${params.toString()}`);
      setWorkflows(response.data || []);
    } catch (error: any) {
      message.error('Failed to fetch workflows');
    } finally {
      setLoading(false);
    }
  };

  const fetchClusterInfo = async () => {
    try {
      const response = await api.get('/argo/cluster/info');
      setClusterInfo(response.data);
    } catch (error) {
      console.error('Failed to fetch cluster info');
    }
  };

  const fetchWorkflowDetails = async (name: string) => {
    try {
      const response = await api.get(`/argo/workflows/${name}?namespace=${namespace}`);
      setSelectedWorkflow(response.data);
    } catch (error: any) {
      message.error('Failed to fetch workflow details');
    }
  };

  const fetchWorkflowNodes = async (name: string) => {
    try {
      const response = await api.get(`/argo/workflows/${name}/nodes?namespace=${namespace}`);
      setNodes(response.data.nodes);
    } catch (error: any) {
      message.error('Failed to fetch workflow nodes');
    }
  };

  const fetchWorkflowLogs = async (name: string, nodeId?: string) => {
    setLogsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('namespace', namespace);
      if (nodeId) params.append('node_id', nodeId);

      const response = await api.get(`/argo/workflows/${name}/logs?${params.toString()}`);
      setLogs(response.data.logs || []);
    } catch (error: any) {
      message.error('Failed to fetch workflow logs');
    } finally {
      setLogsLoading(false);
    }
  };

  const handleRetry = async (name: string) => {
    try {
      await api.post(`/argo/workflows/${name}/retry?namespace=${namespace}`);
      message.success('Workflow retry initiated');
      fetchWorkflows();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to retry workflow');
    }
  };

  const handleStop = async (name: string) => {
    try {
      await api.post(`/argo/workflows/${name}/stop?namespace=${namespace}`);
      message.success('Workflow stopped');
      fetchWorkflows();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to stop workflow');
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await api.delete(`/argo/workflows/${name}?namespace=${namespace}`);
      message.success('Workflow deleted');
      fetchWorkflows();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to delete workflow');
    }
  };

  const handleViewDetails = async (workflow: WorkflowListItem) => {
    await fetchWorkflowDetails(workflow.metadata.name);
    await fetchWorkflowNodes(workflow.metadata.name);
    setDetailsModalOpen(true);
  };

  const handleViewLogs = async (name: string) => {
    await fetchWorkflowLogs(name);
    setLogsModalOpen(true);
  };

  // Get phase badge
  const getPhaseBadge = (phase: WorkflowPhase) => {
    const icon = WORKFLOW_PHASE_ICONS[phase];
    return (
      <Badge
        status={WORKFLOW_PHASE_COLORS[phase] as any}
        text={
          <Space size={4}>
            {icon}
            {phase}
          </Space>
        }
      />
    );
  };

  // Calculate stats
  const stats = {
    total: workflows.length,
    pending: workflows.filter((w) => w.status.phase === WorkflowPhase.PENDING).length,
    running: workflows.filter((w) => w.status.phase === WorkflowPhase.RUNNING).length,
    succeeded: workflows.filter((w) => w.status.phase === WorkflowPhase.SUCCEEDED).length,
    failed: workflows.filter((w) => w.status.phase === WorkflowPhase.FAILED).length,
    error: workflows.filter((w) => w.status.phase === WorkflowPhase.ERROR).length,
  };

  // Table columns
  const columns = [
    {
      title: 'Workflow Name',
      dataIndex: ['metadata', 'name'],
      key: 'name',
      render: (name: string, record: WorkflowListItem) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => handleViewDetails(record)} style={{ fontWeight: 500 }}>
            {name}
          </a>
          <Text style={{ fontSize: '12px', color: '#999' }}>
            {record.metadata.uid.slice(0, 8)}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Phase',
      dataIndex: ['status', 'phase'],
      key: 'phase',
      width: 140,
      render: (phase: WorkflowPhase) => getPhaseBadge(phase),
    },
    {
      title: 'Namespace',
      dataIndex: ['metadata', 'namespace'],
      key: 'namespace',
      width: 120,
      render: (ns: string) => <Tag>{ns}</Tag>,
    },
    {
      title: 'Created',
      dataIndex: ['metadata', 'creationTimestamp'],
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: 'Started',
      dataIndex: ['status', 'startedAt'],
      key: 'started_at',
      width: 180,
      render: (date: string) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 120,
      render: (_, record: WorkflowListItem) => {
        const started = record.status.startedAt ? new Date(record.status.startedAt).getTime() : null;
        const finished = record.status.finishedAt ? new Date(record.status.finishedAt).getTime() : null;
        if (!started) return '-';
        const end = finished || Date.now();
        const duration = Math.floor((end - started) / 1000);
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        return `${minutes}m ${seconds}s`;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record: WorkflowListItem) => {
        const phase = record.status.phase;
        const isRunning = phase === WorkflowPhase.RUNNING;
        const isFailed = phase === WorkflowPhase.FAILED || phase === WorkflowPhase.ERROR;

        return (
          <Space size="small">
            <Tooltip title="View Details">
              <Button
                type="text"
                icon={<EyeOutlined />}
                onClick={() => handleViewDetails(record)}
              />
            </Tooltip>
            <Tooltip title="View Logs">
              <Button
                type="text"
                icon={<FileTextOutlined />}
                onClick={() => handleViewLogs(record.metadata.name)}
              />
            </Tooltip>
            {isRunning && (
              <Tooltip title="Stop">
                <Popconfirm
                  title="Stop this workflow?"
                  onConfirm={() => handleStop(record.metadata.name)}
                >
                  <Button type="text" icon={<StopOutlined />} />
                </Popconfirm>
              </Tooltip>
            )}
            {(isFailed || phase === WorkflowPhase.SKIPPED) && (
              <Tooltip title="Retry">
                <Button
                  type="text"
                  icon={<ReloadOutlined />}
                  onClick={() => handleRetry(record.metadata.name)}
                />
              </Tooltip>
            )}
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'delete',
                    label: 'Delete',
                    icon: <DeleteOutlined />,
                    danger: true,
                    onClick: () => handleDelete(record.metadata.name),
                  },
                ],
              }}
            >
              <Button type="text" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  // Render timeline for nodes
  const renderNodeTimeline = () => {
    const nodeItems = Object.entries(nodes).map(([nodeId, node]) => {
      const phase = node.phase;
      let icon = <ClockCircleOutlined />;
      let color = 'gray';

      if (phase === 'Succeeded') {
        icon = <CheckCircleOutlined />;
        color = 'green';
      } else if (phase === 'Failed' || phase === 'Error') {
        icon = <CloseCircleOutlined />;
        color = 'red';
      } else if (phase === 'Running') {
        icon = <ReloadOutlined spin />;
        color = 'blue';
      }

      return {
        dot: icon,
        color: color,
        children: (
          <Space direction="vertical" size={0}>
            <Text strong>{node.name}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {node.phase} {node.startedAt && `• ${new Date(node.startedAt).toLocaleTimeString()}`}
            </Text>
            {node.message && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {node.message}
              </Text>
            )}
          </Space>
        ),
      };
    });

    return <Timeline items={nodeItems} />;
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <Title level={2} style={{ margin: 0 }}>
                <RocketOutlined /> Argo Workflows
              </Title>
              <Text type="secondary">
                Monitor and manage Argo workflows on Kubernetes
              </Text>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ClusterOutlined />}
                onClick={() => navigate('/workflows/new')}
              >
                Submit Workflow
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Cluster Info */}
      {clusterInfo && (
        <Card style={{ marginBottom: 24 }} size="small">
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Space>
                <Text strong>Argo Server:</Text>
                <Tag color="blue">{clusterInfo.version}</Tag>
                <Text type="secondary">Namespace: {clusterInfo.namespace}</Text>
              </Space>
            </Col>
            <Col>
              <Space split={<Divider type="vertical" />}>
                <Tooltip title="Workflow Templates">
                  <Tag color={clusterInfo.capabilities.workflow_templates ? 'green' : 'red'}>
                    Templates
                  </Tag>
                </Tooltip>
                <Tooltip title="Cron Workflows">
                  <Tag color={clusterInfo.capabilities.cron_workflows ? 'green' : 'red'}>
                    Cron
                  </Tag>
                </Tooltip>
                <Tooltip title="Cluster Templates">
                  <Tag color={clusterInfo.capabilities.cluster_workflow_templates ? 'green' : 'red'}>
                    Cluster
                  </Tag>
                </Tooltip>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card>
            <Statistic title="Total Workflows" value={stats.total} prefix={<ClusterOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Running"
              value={stats.running}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ReloadOutlined spin />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Succeeded"
              value={stats.succeeded}
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
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="Pending" value={stats.pending} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Error"
              value={stats.error}
              valueStyle={{ color: '#faad14' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Search
              placeholder="Search workflows..."
              allowClear
              onSearch={setSearchText}
              style={{ width: 300 }}
            />
          </Col>
          <Col>
            <Select
              placeholder="Namespace"
              value={namespace}
              onChange={setNamespace}
              style={{ width: 150 }}
            >
              <Select.Option value="default">default</Select.Option>
              <Select.Option value="argo">argo</Select.Option>
              <Select.Option value="production">production</Select.Option>
            </Select>
          </Col>
          <Col>
            <Select
              mode="multiple"
              placeholder="Phase Filter"
              value={phaseFilter}
              onChange={setPhaseFilter}
              style={{ width: 200 }}
              options={[
                { label: 'Pending', value: 'Pending' },
                { label: 'Running', value: 'Running' },
                { label: 'Succeeded', value: 'Succeeded' },
                { label: 'Failed', value: 'Failed' },
                { label: 'Error', value: 'Error' },
              ]}
            />
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchWorkflows}
              loading={loading}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card
        bodyStyle={{ padding: 0 }}
        title={
          <Space>
            <Text>Workflows</Text>
            <Text type="secondary">({stats.total} total)</Text>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={workflows}
          rowKey={(record) => record.metadata.uid}
          loading={loading}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} workflows`,
          }}
          scroll={{ y: 'calc(100vh - 600px)' }}
        />
      </Card>

      {/* Details Modal */}
      <Modal
        title={
          <Space>
            Workflow Details
            {selectedWorkflow && (
              <Tag color="blue">{selectedWorkflow.metadata.name}</Tag>
            )}
          </Space>
        }
        open={detailsModalOpen}
        onCancel={() => setDetailsModalOpen(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setDetailsModalOpen(false)}>
            Close
          </Button>,
        ]}
      >
        {selectedWorkflow && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="Name" span={2}>
                {selectedWorkflow.metadata.name}
              </Descriptions.Item>
              <Descriptions.Item label="Namespace">
                {selectedWorkflow.metadata.namespace}
              </Descriptions.Item>
              <Descriptions.Item label="UID">
                <Text code>{selectedWorkflow.metadata.uid}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Phase">
                {getPhaseBadge(selectedWorkflow.status.phase)}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {new Date(selectedWorkflow.metadata.creationTimestamp).toLocaleString()}
              </Descriptions.Item>
              {selectedWorkflow.status.startedAt && (
                <Descriptions.Item label="Started">
                  {new Date(selectedWorkflow.status.startedAt).toLocaleString()}
                </Descriptions.Item>
              )}
              {selectedWorkflow.status.finishedAt && (
                <Descriptions.Item label="Finished">
                  {new Date(selectedWorkflow.status.finishedAt).toLocaleString()}
                </Descriptions.Item>
              )}
              {selectedWorkflow.status.message && (
                <Descriptions.Item label="Message" span={2}>
                  <Text type={selectedWorkflow.status.phase === WorkflowPhase.FAILED ? 'danger' : 'secondary'}>
                    {selectedWorkflow.status.message}
                  </Text>
                </Descriptions.Item>
              )}
            </Descriptions>

            {Object.keys(nodes).length > 0 && (
              <>
                <Divider orientation="left">Workflow Nodes</Divider>
                {renderNodeTimeline()}
              </>
            )}
          </Space>
        )}
      </Modal>

      {/* Logs Modal */}
      <Modal
        title={
          <Space>
            Logs
            {selectedWorkflow && <Tag>{selectedWorkflow.metadata.name}</Tag>}
          </Space>
        }
        open={logsModalOpen}
        onCancel={() => setLogsModalOpen(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setLogsModalOpen(false)}>
            Close
          </Button>,
        ]}
      >
        <Spin spinning={logsLoading}>
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
            {logs.length > 0 ? logs.map((log, i) => (
              <div key={i}>{typeof log === 'string' ? log : JSON.stringify(log)}</div>
            )) : 'No logs available'}
          </pre>
        </Spin>
      </Modal>
    </div>
  );
};

export default ArgoMonitorPage;
