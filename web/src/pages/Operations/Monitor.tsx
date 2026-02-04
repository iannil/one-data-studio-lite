import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Typography,
  Space,
  Alert,
  Table,
  Button,
} from 'antd';
import {
  MonitorOutlined,
  CloudServerOutlined,
  ApiOutlined,
  ReloadOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { Title } = Typography;

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'warning' | 'error';
  uptime: string;
  responseTime: number;
  errorRate: number;
  lastCheck: string;
}

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'normal' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
}

const SERVICE_HEALTH: ServiceHealth[] = [
  {
    name: 'Portal 服务',
    status: 'healthy',
    uptime: '99.9%',
    responseTime: 45,
    errorRate: 0.01,
    lastCheck: '2026-02-01 10:30:00',
  },
  {
    name: 'NL2SQL 服务',
    status: 'healthy',
    uptime: '99.5%',
    responseTime: 230,
    errorRate: 0.05,
    lastCheck: '2026-02-01 10:30:00',
  },
  {
    name: 'AI 清洗服务',
    status: 'warning',
    uptime: '98.2%',
    responseTime: 850,
    errorRate: 1.2,
    lastCheck: '2026-02-01 10:29:50',
  },
  {
    name: '元数据同步',
    status: 'healthy',
    uptime: '99.8%',
    responseTime: 120,
    errorRate: 0.02,
    lastCheck: '2026-02-01 10:30:00',
  },
  {
    name: '数据 API 网关',
    status: 'healthy',
    uptime: '99.9%',
    responseTime: 65,
    errorRate: 0.01,
    lastCheck: '2026-02-01 10:30:00',
  },
  {
    name: '敏感数据检测',
    status: 'healthy',
    uptime: '99.7%',
    responseTime: 180,
    errorRate: 0.03,
    lastCheck: '2026-02-01 10:30:00',
  },
];

const SYSTEM_METRICS: SystemMetric[] = [
  { name: 'CPU 使用率', value: 45, unit: '%', status: 'normal', trend: 'stable' },
  { name: '内存使用率', value: 72, unit: '%', status: 'normal', trend: 'up' },
  { name: '磁盘使用率', value: 58, unit: '%', status: 'normal', trend: 'stable' },
  { name: '网络吞吐', value: 125, unit: 'MB/s', status: 'normal', trend: 'up' },
];

const ALERTS = [
  { id: '1', type: 'warning', message: 'AI 清洗服务响应时间较高', time: '2026-02-01 10:25:00' },
  { id: '2', type: 'info', message: '数据同步任务完成', time: '2026-02-01 10:20:00' },
];

const Monitor: React.FC = () => {
  const [services] = useState<ServiceHealth[]>(SERVICE_HEALTH);
  const [metrics, setMetrics] = useState<SystemMetric[]>(SYSTEM_METRICS);
  const [alerts] = useState(ALERTS);
  const [loading, setLoading] = useState(false);

  const handleRefresh = () => {
    setLoading(true);
    // Simulate refresh
    setTimeout(() => {
      setMetrics((prev) =>
        prev.map((m) => ({
          ...m,
          value: Math.min(100, Math.max(0, m.value + Math.random() * 10 - 5)),
        }))
      );
      setLoading(false);
    }, 1000);
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) =>
        prev.map((m) => ({
          ...m,
          value: Math.min(100, Math.max(0, m.value + Math.random() * 6 - 3)),
        }))
      );
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusTag = (status: ServiceHealth['status']) => {
    const config = {
      healthy: { color: 'success', text: '正常', icon: <CheckCircleOutlined /> },
      warning: { color: 'warning', text: '警告', icon: <WarningOutlined /> },
      error: { color: 'error', text: '异常', icon: <WarningOutlined /> },
    };
    const { color, text, icon } = config[status];
    return (
      <Tag color={color} icon={icon}>
        {text}
      </Tag>
    );
  };

  const getMetricStatus = (status: SystemMetric['status']) => {
    const config = {
      normal: { color: '#52c41a' },
      warning: { color: '#faad14' },
      critical: { color: '#f5222d' },
    };
    return config[status].color;
  };

  const columns = [
    { title: '服务名称', dataIndex: 'name', key: 'name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ServiceHealth['status']) => getStatusTag(status),
    },
    {
      title: '响应时间',
      dataIndex: 'responseTime',
      key: 'responseTime',
      width: 120,
      render: (time: number) => (
        <span style={{ color: time > 500 ? '#f5222d' : time > 200 ? '#faad14' : '#52c41a' }}>
          {time} ms
        </span>
      ),
    },
    {
      title: '错误率',
      dataIndex: 'errorRate',
      key: 'errorRate',
      width: 100,
      render: (rate: number) => (
        <span style={{ color: rate > 1 ? '#f5222d' : rate > 0.1 ? '#faad14' : '#52c41a' }}>
          {rate}%
        </span>
      ),
    },
    { title: '可用性', dataIndex: 'uptime', key: 'uptime', width: 100 },
    { title: '最后检查', dataIndex: 'lastCheck', key: 'lastCheck' },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <MonitorOutlined /> 系统监控
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 告警信息 */}
        {alerts.length > 0 && (
          <Card size="small" title={<Space><WarningOutlined /> 系统告警</Space>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {alerts.map((alert) => (
                <Alert
                  key={alert.id}
                  message={alert.message}
                  description={alert.time}
                  type={alert.type === 'warning' ? 'warning' : 'info'}
                  showIcon
                  closable
                />
              ))}
            </Space>
          </Card>
        )}

        {/* 系统资源概览 */}
        <Card
          size="small"
          title={
            <Space>
              <CloudServerOutlined /> 系统资源
              <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={handleRefresh}>
                刷新
              </Button>
            </Space>
          }
        >
          <Row gutter={16}>
            {metrics.map((metric) => (
              <Col span={6} key={metric.name}>
                <Card size="small">
                  <Statistic
                    title={metric.name}
                    value={metric.value}
                    suffix={metric.unit}
                    valueStyle={{ color: getMetricStatus(metric.status) }}
                  />
                  <Progress
                    percent={metric.unit === '%' ? metric.value : Math.min(100, (metric.value / 200) * 100)}
                    strokeColor={getMetricStatus(metric.status)}
                    showInfo={false}
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </Card>

        {/* 服务健康状态 */}
        <Card size="small" title={<Space><ApiOutlined /> 服务健康状态</Space>}>
          <Table
            columns={columns}
            dataSource={services.map((s) => ({ ...s, key: s.name }))}
            pagination={false}
            size="small"
          />
        </Card>

        {/* 快捷操作 */}
        <Row gutter={16}>
          <Col span={8}>
            <Card size="small" title="DolphinScheduler">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic title="运行中工作流" value={12} suffix="个" />
                <Statistic title="今日成功" value={156} suffix="次" />
                <Button size="small" block>查看详情</Button>
              </Space>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="SeaTunnel">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic title="活跃同步任务" value={8} suffix="个" />
                <Statistic title="今日处理量" value={125.6} suffix="GB" />
                <Button size="small" block>查看详情</Button>
              </Space>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="DataHub">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic title="已注册数据集" value={234} suffix="个" />
                <Statistic title="元数据抓取" value={15} suffix="次/日" />
                <Button size="small" block>查看详情</Button>
              </Space>
            </Card>
          </Col>
        </Row>
      </Space>
    </div>
  );
};

export default Monitor;
