/**
 * Experiment Detail Page
 *
 * Shows experiment details with runs list, metrics charts, and artifacts.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Tag,
  Button,
  Space,
  Tooltip,
  Statistic,
  Progress,
  Select,
  message,
  Tabs,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Divider,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  BarChartOutlined,
  EyeOutlined,
  DownloadOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Divider } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useExperimentStore } from '@/stores/experiment';
import type { Run, Experiment } from '@/stores/experiment';

const { TabPane } = Tabs;
const { Search } = Input;

const ExperimentDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const { experimentId } = useParams<{ experimentId: string }>();

  const {
    currentExperiment,
    runs,
    loading,
    fetchExperiment,
    fetchRuns,
    deleteRun,
    setRunStatus,
    getMetricSummary,
    getMetricCorrelation,
    clearError,
  } = useExperimentStore();

  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [runStatusFilter, setRunStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [metricSummary, setMetricSummary] = useState<any>(null);
  const [metricCorrelation, setMetricCorrelation] = useState<any>(null);
  const [compareModalOpen, setCompareModalOpen] = useState(false);

  useEffect(() => {
    if (experimentId) {
      fetchExperiment(experimentId);
      fetchRuns(experimentId);
    }
  }, [experimentId, fetchExperiment, fetchRuns]);

  const handleStatusChange = (value: string) => {
    setRunStatusFilter(value);
    fetchRuns(experimentId!, 100, value || undefined);
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleRunStatus = async (run: Run, status: 'FINISHED' | 'FAILED' | 'KILLED') => {
    try {
      await setRunStatus(run.run_id, status);
      message.success(`Run marked as ${status}`);
    } catch (err) {
      message.error('Failed to update run status');
    }
  };

  const handleViewRun = (run: Run) => {
    setSelectedRun(run);
    setDetailDrawerOpen(true);
  };

  const handleDeleteRun = async (run: Run) => {
    try {
      await deleteRun(run.run_id);
      message.success('Run deleted');
    } catch (err) {
      message.error('Failed to delete run');
    }
  };

  const handleCompareRuns = async () => {
    if (selectedRunIds.length < 2) {
      message.warning('Select at least 2 runs to compare');
      return;
    }
    setCompareModalOpen(true);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <PlayCircleOutlined style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'killed':
        return <StopOutlined style={{ color: '#faad14' }} />;
      default:
        return <ThunderboltOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  const getStatusTag = (status: string) => {
    const colors: Record<string, string> = {
      running: 'blue',
      completed: 'green',
      failed: 'red',
      killed: 'orange',
      scheduled: 'default',
    };
    return <Tag color={colors[status] || 'default'}>{status}</Tag>;
  };

  const filteredRuns = runs.filter((run) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      run.run_name?.toLowerCase().includes(term) ||
      run.run_id.toLowerCase().includes(term)
    );
  });

  const columns = [
    {
      title: '',
      width: 50,
      render: (_: any, run: Run) => (
        <input
          type="checkbox"
          checked={selectedRunIds.includes(run.run_id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedRunIds([...selectedRunIds, run.run_id]);
            } else {
              setSelectedRunIds(selectedRunIds.filter((id) => id !== run.run_id));
            }
          }}
        />
      ),
    },
    {
      title: 'Run Name',
      dataIndex: 'run_name',
      key: 'run_name',
      render: (name: string, run: Run) => (
        <Space>
          {getStatusIcon(run.status)}
          <a onClick={() => handleViewRun(run)}>
            {name || run.run_id.substring(0, 8)}
          </a>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: 'Metrics',
      key: 'metrics',
      ellipsis: true,
      render: (_: any, run: Run) => {
        const metrics = run.metrics || {};
        const entries = Object.entries(metrics).slice(0, 3);
        return (
          <Space size="small">
            {entries.map(([key, value]) => (
              <Tag key={key}>
                {key}: {typeof value === 'number' ? value.toFixed(4) : value}
              </Tag>
            ))}
            {Object.keys(metrics).length > 3 && (
              <Tag>+{Object.keys(metrics).length - 3}</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 120,
      render: (_: any, run: Run) => {
        if (!run.start_time) return '-';
        const end = run.end_time || Date.now();
        const duration = end - run.start_time;
        if (duration < 60000) {
          return `${Math.floor(duration / 1000)}s`;
        }
        return `${Math.floor(duration / 60000)}m`;
      },
    },
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (timestamp: number) => {
        if (!timestamp) return '-';
        return new Date(timestamp).toLocaleString();
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_: any, run: Run) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewRun(run)}
            />
          </Tooltip>
          {run.status === 'running' && (
            <Tooltip title="Stop Run">
              <Button
                type="text"
                icon={<StopOutlined />}
                onClick={() => handleRunStatus(run, 'KILLED')}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const bestRun = currentExperiment?.best_run;
  const metricKeys = bestRun?.metrics ? Object.keys(bestRun.metrics) : [];

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/experiments')}
          >
            Back
          </Button>
        </Col>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>
            {currentExperiment?.name}
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            {currentExperiment?.description || 'No description'}
          </p>
        </Col>
      </Row>

      {/* Stats */}
  <Row gutter={16} style={{ marginBottom: '24px' }}>
    <Col span={6}>
      <Card>
        <Statistic
          title="Total Runs"
          value={runs.length}
          prefix={<BarChartOutlined />}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card>
        <Statistic
          title="Running"
          value={runs.filter((r) => r.status === 'running').length}
          valueStyle={{ color: '#1890ff' }}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card>
        <Statistic
          title="Completed"
          value={runs.filter((r) => r.status === 'completed').length}
          valueStyle={{ color: '#52c41a' }}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card>
        <Statistic
          title="Failed"
          value={runs.filter((r) => r.status === 'failed').length}
          valueStyle={{ color: runs.filter((r) => r.status === 'failed').length > 0 ? '#ff4d4f' : undefined }}
        />
      </Card>
    </Col>
  </Row>

      {/* Best Run Summary */}
      {bestRun && (
        <Card
          title="Best Run"
          style={{ marginBottom: '16px' }}
          extra={
            <Button
              type="link"
              onClick={() => handleViewRun(bestRun)}
              icon={<EyeOutlined />}
            >
              View Details
            </Button>
          }
        >
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="Run"
                value={bestRun.run_name || bestRun.run_id.substring(0, 8)}
              />
            </Col>
            {metricKeys.slice(0, 3).map((key) => (
              <Col span={8} key={key}>
                <Statistic
                  title={key}
                  value={bestRun.metrics![key]}
                  precision={4}
                />
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* Controls */}
      <Card style={{ marginBottom: '16px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space>
              <Search
                placeholder="Search runs..."
                allowClear
                onSearch={handleSearch}
                onChange={(e) => handleSearch(e.target.value)}
                style={{ width: 250 }}
              />
              <Select
                placeholder="Filter by status"
                allowClear
                style={{ width: 150 }}
                onChange={handleStatusChange}
                value={runStatusFilter}
              >
                <Select.Option value="running">Running</Select.Option>
                <Select.Option value="completed">Completed</Select.Option>
                <Select.Option value="failed">Failed</Select.Option>
                <Select.Option value="killed">Killed</Select.Option>
              </Select>
              <Tag>{selectedRunIds.length} selected</Tag>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<LineChartOutlined />}
              onClick={handleCompareRuns}
              disabled={selectedRunIds.length < 2}
            >
              Compare ({selectedRunIds.length})
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Runs Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredRuns}
          rowKey="run_id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} runs`,
          }}
        />
      </Card>

      {/* Run Detail Drawer */}
      <Drawer
        title="Run Details"
        placement="right"
        width={600}
        open={detailDrawerOpen}
        onClose={() => {
          setDetailDrawerOpen(false);
          setSelectedRun(null);
        }}
      >
        {selectedRun && (
          <Tabs defaultActiveKey="overview">
            <TabPane tab="Overview" key="overview">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Run ID">
                  {selectedRun.run_id}
                </Descriptions.Item>
                <Descriptions.Item label="Run Name">
                  {selectedRun.run_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Status">
                  {getStatusTag(selectedRun.status)}
                </Descriptions.Item>
                <Descriptions.Item label="Start Time">
                  {selectedRun.start_time
                    ? new Date(selectedRun.start_time).toLocaleString()
                    : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="End Time">
                  {selectedRun.end_time
                    ? new Date(selectedRun.end_time).toLocaleString()
                    : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Artifact URI">
                  {selectedRun.artifact_uri || '-'}
                </Descriptions.Item>
              </Descriptions>

              <Divider />

              <h4>Parameters</h4>
              {selectedRun.params && Object.keys(selectedRun.params).length > 0 ? (
                <Descriptions column={1} bordered size="small">
                  {Object.entries(selectedRun.params).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              ) : (
                <p style={{ color: '#999' }}>No parameters logged</p>
              )}
            </TabPane>

            <TabPane tab="Metrics" key="metrics">
              {selectedRun.metrics && Object.keys(selectedRun.metrics).length > 0 ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {Object.entries(selectedRun.metrics).map(([key, value]) => (
                    <Card key={key} size="small">
                      <Row justify="space-between">
                        <Col>
                          <strong>{key}</strong>
                        </Col>
                        <Col>
                          <Tag color="blue">{typeof value === 'number' ? value.toFixed(6) : value}</Tag>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                </Space>
              ) : (
                <p style={{ color: '#999' }}>No metrics logged</p>
              )}
            </TabPane>

            <TabPane tab="Artifacts" key="artifacts">
              {selectedRun.artifacts && selectedRun.artifacts.length > 0 ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {selectedRun.artifacts.map((artifact) => (
                    <Card key={artifact.path} size="small">
                      <Row justify="space-between" align="middle">
                        <Col>
                          {artifact.is_dir ? (
                            <>&#128193; {artifact.path}</>
                          ) : (
                            <>&#128442; {artifact.path}</>
                          )}
                        </Col>
                        <Col>
                          <Button
                            type="text"
                            icon={<DownloadOutlined />}
                            size="small"
                          >
                            {artifact.size ? `${(artifact.size / 1024).toFixed(1)} KB` : ''}
                          </Button>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                </Space>
              ) : (
                <p style={{ color: '#999' }}>No artifacts</p>
              )}
            </TabPane>
          </Tabs>
        )}
      </Drawer>

      {/* Compare Modal */}
      <Modal
        title={`Compare ${selectedRunIds.length} Runs`}
        open={compareModalOpen}
        onCancel={() => setCompareModalOpen(false)}
        footer={null}
        width={1000}
      >
        <p>Comparison view will be implemented with metrics comparison charts.</p>
        <p>Selected runs: {selectedRunIds.join(', ')}</p>
      </Modal>
    </div>
  );
};

export default ExperimentDetailPage;
