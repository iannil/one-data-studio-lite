/**
 * GPU Monitor Panel Component
 *
 * Displays real-time GPU metrics for training jobs including:
 * - Utilization percentage
 * - Memory usage
 * - Temperature
 * - Power consumption
 * - Alerts
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Alert,
  Space,
  Typography,
  Button,
  Tooltip,
  Badge,
  Spin,
} from 'antd';
import {
  ThunderboltOutlined,
  DatabaseOutlined,
  FireOutlined,
  ZapOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  WifiOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface GPUMetric {
  gpu_id: number;
  name: string;
  utilization_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_used_percent: number;
  temperature_celsius: number;
  power_draw_watts: number;
  is_healthy: boolean;
  utilization_status: 'low' | 'medium' | 'high';
}

interface GPUMonitorPanelProps {
  jobId?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  showWebSocketOption?: boolean;
}

const GPUMonitorPanel: React.FC<GPUMonitorPanelProps> = ({
  jobId,
  autoRefresh = false,
  refreshInterval = 5000,
  showWebSocketOption = false,
}) => {
  const [gpuMetrics, setGPUMetrics] = useState<GPUMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [usingWebSocket, setUsingWebSocket] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch GPU metrics
  const fetchGPUMetrics = useCallback(async () => {
    if (usingWebSocket) return; // Don't fetch if using WebSocket

    setLoading(true);
    setError(null);

    try {
      const endpoint = jobId
        ? `/training/jobs/${jobId}/gpu/summary`
        : '/training/gpu/metrics';

      const response = await fetch(`/api/v1${endpoint}`);
      if (!response.ok) throw new Error('Failed to fetch GPU metrics');

      const data = await response.json();

      if (jobId) {
        // For job-specific monitoring
        setSummary(data);
        setGPUMetrics([]);
      } else {
        // For global GPU monitoring
        setGPUMetrics(data.gpus || []);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [jobId, usingWebSocket]);

  // Fetch alerts for job
  const fetchAlerts = useCallback(async () => {
    if (!jobId) return;

    try {
      const response = await fetch(`/api/v1/training/jobs/${jobId}/gpu/alerts`);
      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  }, [jobId]);

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = jobId
      ? `ws://localhost:3101/api/v1/training/ws/jobs/${jobId}/metrics`
      : `ws://localhost:3101/api/v1/training/ws/gpu/metrics`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setUsingWebSocket(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event_type === 'gpu_update') {
        setGPUMetrics(data.data.gpus || []);
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
      setUsingWebSocket(false);
    };

    ws.onclose = () => {
      setUsingWebSocket(false);
    };
  }, [jobId]);

  // Disconnect WebSocket
  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setUsingWebSocket(false);
  }, []);

  // Toggle WebSocket mode
  const toggleWebSocket = () => {
    if (usingWebSocket) {
      disconnectWebSocket();
    } else {
      connectWebSocket();
    }
  };

  // Initial fetch and auto-refresh setup
  useEffect(() => {
    fetchGPUMetrics();
    if (jobId) fetchAlerts();

    if (autoRefresh && !usingWebSocket) {
      refreshTimerRef.current = setInterval(fetchGPUMetrics, refreshInterval);
    }

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [fetchGPUMetrics, autoRefresh, refreshInterval, usingWebSocket, jobId]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      disconnectWebSocket();
    };
  }, [disconnectWebSocket]);

  // Get status color for utilization
  const getUtilizationColor = (percent: number) => {
    if (percent >= 80) return '#52c41a';
    if (percent >= 50) return '#1890ff';
    if (percent >= 20) return '#faad14';
    return '#ff4d4f';
  };

  // Get temperature status
  const getTemperatureStatus = (temp: number) => {
    if (temp >= 90) return { color: 'error', icon: <CloseCircleOutlined />, text: 'Critical' };
    if (temp >= 80) return { color: 'warning', icon: <WarningOutlined />, text: 'High' };
    if (temp >= 60) return { color: 'processing', icon: <FireOutlined />, text: 'Normal' };
    return { color: 'success', icon: <CheckCircleOutlined />, text: 'Cool' };
  };

  // Format memory
  const formatMemory = (mb: number) => {
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${mb} MB`;
  };

  // Render GPU card
  const renderGPUCard = (gpu: GPUMetric) => {
    const tempStatus = getTemperatureStatus(gpu.temperature_celsius);

    return (
      <Col key={gpu.gpu_id} xs={24} sm={12} lg={8} xl={6}>
        <Card
          size="small"
          title={
            <Space>
              <span>GPU {gpu.gpu_id}</span>
              <Tag color={gpu.is_healthy ? 'green' : 'red'}>
                {gpu.is_healthy ? 'Healthy' : 'Warning'}
              </Tag>
            </Space>
          }
          extra={
            <Tag color="blue">{gpu.utilization_status}</Tag>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {/* Utilization */}
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                <ThunderboltOutlined /> Utilization
              </Text>
              <Progress
                percent={Math.round(gpu.utilization_percent)}
                strokeColor={getUtilizationColor(gpu.utilization_percent)}
                size="small"
              />
            </div>

            {/* Memory */}
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                <DatabaseOutlined /> Memory
              </Text>
              <Progress
                percent={Math.round(gpu.memory_used_percent)}
                format={() => `${formatMemory(gpu.memory_used_mb)} / ${formatMemory(gpu.memory_total_mb)}`}
                size="small"
              />
            </div>

            {/* Temperature */}
            <Row gutter={8}>
              <Col span={12}>
                <Statistic
                  title={<Text type="secondary" style={{ fontSize: '12px' }}><FireOutlined /> Temp</Text>}
                  value={gpu.temperature_celsius}
                  suffix="°C"
                  valueStyle={{ fontSize: '18px', color: tempStatus.color === 'error' ? '#ff4d4f' : undefined }}
                  prefix={tempStatus.icon}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={<Text type="secondary" style={{ fontSize: '12px' }}><ZapOutlined /> Power</Text>}
                  value={gpu.power_draw_watts}
                  suffix="W"
                  valueStyle={{ fontSize: '18px' }}
                />
              </Col>
            </Row>
          </Space>
        </Card>
      </Col>
    );
  };

  // Render summary stats for job monitoring
  const renderSummaryStats = () => {
    if (!summary) return null;

    return (
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Duration"
              value={summary.duration_seconds ? (summary.duration_seconds / 60).toFixed(1) : 0}
              suffix="min"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Samples"
              value={summary.samples_count || 0}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small}>
            <Statistic
              title="Avg Utilization"
              value={summary.avg_utilization_percent?.toFixed(1) || 0}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Max Temp"
              value={summary.max_temperature_celsius?.toFixed(1) || 0}
              suffix="°C"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Peak Memory"
              value={summary.peak_memory_usage_percent?.toFixed(1) || 0}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Alerts"
              value={summary.alerts_count || 0}
              valueStyle={{ color: (summary.alerts_count || 0) > 0 ? '#ff4d4f' : undefined }}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  // Render alerts
  const renderAlerts = () => {
    if (alerts.length === 0) return null;

    return (
      <Alert
        type="warning"
        message="GPU Alerts"
        description={
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {alerts.slice(0, 5).map((alert, idx) => (
              <li key={idx}>
                <Tag color={alert.severity}>{alert.severity}</Tag>
                GPU {alert.gpu_id}: {alert.message}
              </li>
            ))}
          </ul>
        }
        closable
        style={{ marginBottom: 16 }}
      />
    );
  };

  if (loading && gpuMetrics.length === 0) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <Badge status={usingWebSocket ? 'processing' : 'default'} />
          <span>{jobId ? `GPU Monitoring - Job ${jobId}` : 'GPU Cluster Status'}</span>
          {usingWebSocket && <Tag color="green"><WifiOutlined /> Live</Tag>}
        </Space>
      }
      extra={
        <Space>
          {showWebSocketOption && (
            <Tooltip title={usingWebSocket ? 'Switch to polling' : 'Switch to live updates'}>
              <Button
                type={usingWebSocket ? 'primary' : 'default'}
                size="small"
                icon={<WifiOutlined />}
                onClick={toggleWebSocket}
              >
                {usingWebSocket ? 'Live' : 'Live'}
              </Button>
            </Tooltip>
          )}
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={fetchGPUMetrics}
            loading={loading}
            disabled={usingWebSocket}
          >
            Refresh
          </Button>
        </Space>
      }
    >
      {error && (
        <Alert
          type="error"
          message="Error loading GPU metrics"
          description={error}
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {renderAlerts()}
      {renderSummaryStats()}

      {gpuMetrics.length === 0 && !summary ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          No GPU data available. {jobId ? 'Start monitoring to see GPU metrics.' : 'No GPUs detected.'}
        </div>
      ) : (
        <Row gutter={16}>
          {gpuMetrics.map((gpu) => renderGPUCard(gpu))}
        </Row>
      )}
    </Card>
  );
};

export default GPUMonitorPanel;
