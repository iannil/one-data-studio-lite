/**
 * Celery Task Monitoring Component
 *
 * Displays real-time status of Celery workers, tasks, and queues.
 */
import { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Table,
  Button,
  Alert,
  Progress,
  Space,
  Tooltip,
  Badge,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined as WorkerOutlined,
  FunctionOutlined,
  CloudServerOutlined,
  LinkOutlined as ExternalLinkOutlined,
  SyncOutlined,
  StopOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { celeryApi } from '../services/api';

interface WorkerInfo {
  name: string;
  pools: string[];
  concurrency: number;
  max_tasks_per_child: number | null;
  active_tasks: number;
  scheduled_tasks: number;
}

interface CeleryStatus {
  enabled: boolean;
  workers_online: number;
  tasks_active: number;
  tasks_scheduled: number;
  queues: Record<string, { pending: number; processing: number }>;
  beat_running: boolean;
}

interface QueueInfo {
  name: string;
  pending: number;
  processing: number;
  total: number;
}

export function CeleryMonitor() {
  const [status, setStatus] = useState<CeleryStatus | null>(null);
  const [workers, setWorkers] = useState<WorkerInfo[]>([]);
  const [queues, setQueues] = useState<QueueInfo[]>([]);
  const [flowerUrl, setFlowerUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async () => {
    try {
      setRefreshing(true);
      setError(null);

      const [statusRes, workersRes, queuesRes, flowerRes] = await Promise.all([
        celeryApi.getStatus(),
        celeryApi.getWorkers(),
        celeryApi.getQueues(),
        celeryApi.getFlowerUrl(),
      ]);

      setStatus(statusRes.data);
      setWorkers(workersRes.data);
      setFlowerUrl(flowerRes.data.url);

      // Transform queue data
      const queueList: QueueInfo[] = Object.entries(queuesRes.data.queues || {}).map(
        ([name, info]: [string, any]) => ({
          name,
          pending: info.pending || 0,
          processing: info.processing || 0,
          total: (info.pending || 0) + (info.processing || 0),
        })
      );
      setQueues(queueList);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch Celery status');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card loading={true} title="Celery Task Monitoring">
        <div style={{ height: 200 }} />
      </Card>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error loading Celery status"
        description={error}
        type="error"
        showIcon
        action={
          <Button size="small" onClick={fetchStatus}>
            Retry
          </Button>
        }
      />
    );
  }

  if (!status?.enabled) {
    return (
      <Alert
        message="Celery is not enabled"
        description="Set USE_CELERY=true to enable Celery task processing"
        type="warning"
        showIcon
      />
    );
  }

  const totalTasks = status.tasks_active + status.tasks_scheduled;
  const workerUtilization = workers.length > 0
    ? Math.round((workers.reduce((sum, w) => sum + w.active_tasks, 0) /
        workers.reduce((sum, w) => sum + w.concurrency, 1)) * 100)
    : 0;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Header */}
      <Card
        title="Celery Task Monitoring"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              loading={refreshing}
              onClick={fetchStatus}
            >
              Refresh
            </Button>
            <Button
              icon={<ExternalLinkOutlined />}
              target="_blank"
              href={flowerUrl}
            >
              Open Flower
            </Button>
          </Space>
        }
      >
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="Workers Online"
              value={status.workers_online}
              prefix={<WorkerOutlined />}
              valueStyle={{ color: status.workers_online > 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Active Tasks"
              value={status.tasks_active}
              prefix={<FunctionOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Scheduled Tasks"
              value={status.tasks_scheduled}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Beat Status"
              value={status.beat_running ? 'Running' : 'Stopped'}
              prefix={status.beat_running ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              valueStyle={{ color: status.beat_running ? '#3f8600' : '#cf1322' }}
            />
          </Col>
        </Row>

        {workers.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
              <span>Worker Utilization</span>
              <span>{workerUtilization}%</span>
            </div>
            <Progress
              percent={workerUtilization}
              status={workerUtilization > 80 ? 'exception' : workerUtilization > 50 ? 'active' : 'success'}
            />
          </div>
        )}
      </Card>

      {/* Workers Table */}
      <Card
        title={<Space><WorkerOutlined /> Workers</Space>}
      >
        <Table
          dataSource={workers}
          rowKey="name"
          size="small"
          pagination={false}
          columns={[
            {
              title: 'Worker Name',
              dataIndex: 'name',
              key: 'name',
              ellipsis: true,
              render: (name: string) => (
                <Tooltip title={name}>
                  <code>{name.split('@')[0]}</code>
                </Tooltip>
              ),
            },
            {
              title: 'Pool Type',
              dataIndex: 'pools',
              key: 'pools',
              render: (pools: string[]) => (
                <Tag color="blue">{pools[0] || 'prefork'}</Tag>
              ),
            },
            {
              title: 'Concurrency',
              dataIndex: 'concurrency',
              key: 'concurrency',
              render: (value: number) => (
                <Badge count={value} style={{ backgroundColor: '#52c41a' }} />
              ),
            },
            {
              title: 'Active Tasks',
              dataIndex: 'active_tasks',
              key: 'active_tasks',
              render: (value: number) => (
                <Tag color="processing">{value}</Tag>
              ),
            },
            {
              title: 'Scheduled Tasks',
              dataIndex: 'scheduled_tasks',
              key: 'scheduled_tasks',
              render: (value: number) => (
                <Tag color="warning">{value}</Tag>
              ),
            },
            {
              title: 'Utilization',
              key: 'utilization',
              render: (_: any, record: WorkerInfo) => {
                const util = record.concurrency > 0
                  ? Math.round((record.active_tasks / record.concurrency) * 100)
                  : 0;
                return (
                  <Progress
                    percent={util}
                    size="small"
                    status={util > 80 ? 'exception' : 'normal'}
                  />
                );
              },
            },
          ]}
        />
      </Card>

      {/* Queues Table */}
      <Card
        title={<Space><CloudServerOutlined /> Queues</Space>}
      >
        <Table
          dataSource={queues}
          rowKey="name"
          size="small"
          pagination={false}
          columns={[
            {
              title: 'Queue Name',
              dataIndex: 'name',
              key: 'name',
              render: (name: string) => (
                <Tag color="geekblue">{name}</Tag>
              ),
            },
            {
              title: 'Pending',
              dataIndex: 'pending',
              key: 'pending',
              render: (value: number) => (
                <Statistic value={value} valueStyle={{ fontSize: 14 }} />
              ),
            },
            {
              title: 'Processing',
              dataIndex: 'processing',
              key: 'processing',
              render: (value: number) => (
                <Statistic value={value} valueStyle={{ fontSize: 14, color: '#1890ff' }} />
              ),
            },
            {
              title: 'Total',
              dataIndex: 'total',
              key: 'total',
              render: (value: number) => (
                <Statistic value={value} valueStyle={{ fontSize: 14, fontWeight: 'bold' }} />
              ),
            },
          ]}
        />
      </Card>
    </Space>
  );
}

export default CeleryMonitor;
