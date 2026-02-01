import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Select,
  message,
  Typography,
  Space,
  Alert,
  Statistic,
  Row,
  Col,
  Progress,
} from 'antd';
import {
  ApiOutlined,
  ReloadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

type ApiStatus = 'online' | 'degraded' | 'offline';
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

interface ApiEndpoint {
  id: string;
  name: string;
  path: string;
  method: HttpMethod;
  service: string;
  status: ApiStatus;
  qps: number;
  avgResponseTime: number;
  errorRate: number;
  p95: number;
  p99: number;
  lastCalled: string;
}

const DEMO_ENDPOINTS: ApiEndpoint[] = [
  {
    id: '1',
    name: '用户登录',
    path: '/api/v1/auth/login',
    method: 'POST',
    service: 'portal:8010',
    status: 'online',
    qps: 125,
    avgResponseTime: 45,
    errorRate: 0.01,
    p95: 80,
    p99: 120,
    lastCalled: '2026-02-01 10:30:25',
  },
  {
    id: '2',
    name: '自然语言转 SQL',
    path: '/api/v1/nl2sql/query',
    method: 'POST',
    service: 'nl2sql:8011',
    status: 'online',
    qps: 45,
    avgResponseTime: 1250,
    errorRate: 0.05,
    p95: 2000,
    p99: 3500,
    lastCalled: '2026-02-01 10:30:20',
  },
  {
    id: '3',
    name: '数据质量分析',
    path: '/api/v1/cleaning/analyze',
    method: 'POST',
    service: 'ai_cleaning:8012',
    status: 'degraded',
    qps: 23,
    avgResponseTime: 3200,
    errorRate: 2.1,
    p95: 5000,
    p99: 8000,
    lastCalled: '2026-02-01 10:29:55',
  },
  {
    id: '4',
    name: '元数据查询',
    path: '/api/v1/metadata/search',
    method: 'GET',
    service: 'metadata_sync:8013',
    status: 'online',
    qps: 78,
    avgResponseTime: 85,
    errorRate: 0,
    p95: 150,
    p99: 220,
    lastCalled: '2026-02-01 10:30:15',
  },
  {
    id: '5',
    name: '数据资产列表',
    path: '/api/v1/assets/list',
    method: 'GET',
    service: 'data_api:8014',
    status: 'online',
    qps: 156,
    avgResponseTime: 35,
    errorRate: 0,
    p95: 60,
    p99: 95,
    lastCalled: '2026-02-01 10:30:22',
  },
];

const METHOD_COLORS: Record<HttpMethod, string> = {
  GET: 'green',
  POST: 'blue',
  PUT: 'orange',
  DELETE: 'red',
};

const ApiGateway: React.FC = () => {
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>(DEMO_ENDPOINTS);
  const [selectedService, setSelectedService] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);

  const handleRefresh = async () => {
    setLoading(true);
    // Simulate refresh
    setTimeout(() => {
      setEndpoints((prev) =>
        prev.map((e) => ({
          ...e,
          qps: Math.max(0, e.qps + Math.floor(Math.random() * 20 - 10)),
          avgResponseTime: Math.max(10, e.avgResponseTime + Math.floor(Math.random() * 100 - 50)),
        }))
      );
      setLoading(false);
      message.success('数据已刷新');
    }, 1000);
  };

  const getServiceOption = (service: string) => {
    const match = service.match(/(\w+):\d+/);
    return match ? match[1] : service;
  };

  const getStatusTag = (status: ApiStatus) => {
    const config = {
      online: { color: 'success', text: '正常' },
      degraded: { color: 'warning', text: '降级' },
      offline: { color: 'error', text: '离线' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const getMethodTag = (method: HttpMethod) => (
    <Tag color={METHOD_COLORS[method]}>{method}</Tag>
  );

  const columns = [
    {
      title: '接口名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '方法和路径',
      key: 'path',
      width: 250,
      render: (_: unknown, record: ApiEndpoint) => (
        <Space>
          {getMethodTag(record.method)}
          <Text code>{record.path}</Text>
        </Space>
      ),
    },
    {
      title: '服务',
      dataIndex: 'service',
      key: 'service',
      width: 120,
      render: (service: string) => <Tag>{getServiceOption(service)}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ApiStatus) => getStatusTag(status),
    },
    {
      title: 'QPS',
      dataIndex: 'qps',
      key: 'qps',
      width: 80,
      render: (qps: number) => <Text strong>{qps}</Text>,
    },
    {
      title: '平均响应',
      dataIndex: 'avgResponseTime',
      key: 'avgResponseTime',
      width: 100,
      render: (time: number) => (
        <span style={{ color: time > 1000 ? '#f5222d' : time > 500 ? '#faad14' : '#52c41a' }}>
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
    {
      title: 'P95/P99',
      key: 'latency',
      width: 100,
      render: (_: unknown, record: ApiEndpoint) => (
        <Space size="small">
          <Text type="secondary">{record.p95}</Text>
          <Text type="secondary">{record.p99}</Text>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: ApiEndpoint) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedEndpoint(record);
            setDetailVisible(true);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  const filteredEndpoints = endpoints.filter((e) => {
    if (selectedService !== 'all' && !e.service.includes(selectedService)) {
      return false;
    }
    if (selectedStatus !== 'all' && e.status !== selectedStatus) {
      return false;
    }
    return true;
  });

  const totalQps = filteredEndpoints.reduce((sum, e) => sum + e.qps, 0);
  const avgResponseTime = filteredEndpoints.length > 0
    ? filteredEndpoints.reduce((sum, e) => sum + e.avgResponseTime, 0) / filteredEndpoints.length
    : 0;
  const errorEndpoints = filteredEndpoints.filter((e) => e.errorRate > 1).length;

  const serviceOptions = [
    { label: '全部服务', value: 'all' },
    ...Array.from(new Set(endpoints.map((e) => getServiceOption(e.service)))).map((s) => ({
      label: s,
      value: s,
    })),
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <ApiOutlined /> 接口服务管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="API 网关监控"
          description="实时监控所有微服务的 API 调用情况，包括 QPS、响应时间、错误率等关键指标。"
          type="info"
          showIcon
        />

        {/* 统计概览 */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic title="总 QPS" value={totalQps} suffix="请求/秒" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均响应时间"
                value={avgResponseTime.toFixed(0)}
                suffix="ms"
                valueStyle={{ color: avgResponseTime > 500 ? '#f5222d' : avgResponseTime > 200 ? '#faad14' : '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="异常接口"
                value={errorEndpoints}
                suffix="个"
                valueStyle={{ color: errorEndpoints > 0 ? '#f5222d' : '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="在线接口" value={filteredEndpoints.length} suffix="个" />
            </Card>
          </Col>
        </Row>

        {/* 筛选和列表 */}
        <Card
          size="small"
          title="API 端点列表"
          extra={
            <Space>
              <Select
                value={selectedService}
                onChange={setSelectedService}
                options={serviceOptions}
                style={{ width: 150 }}
              />
              <Select
                value={selectedStatus}
                onChange={setSelectedStatus}
                style={{ width: 100 }}
              >
                <Select.Option value="all">全部状态</Select.Option>
                <Select.Option value="online">正常</Select.Option>
                <Select.Option value="degraded">降级</Select.Option>
                <Select.Option value="offline">离线</Select.Option>
              </Select>
              <Button icon={<ReloadOutlined />} loading={loading} onClick={handleRefresh}>
                刷新
              </Button>
            </Space>
          }
        >
          <Table
            columns={columns}
            dataSource={filteredEndpoints.map((e) => ({ ...e, key: e.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1200 }}
          />
        </Card>
      </Space>

      {/* 详情弹窗 */}
      <Modal
        title="接口详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedEndpoint && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title="基本信息">
              <Row gutter={16}>
                <Col span={12}>
                  <Text strong>接口名称：</Text>
                  <Text>{selectedEndpoint.name}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>服务：</Text>
                  <Text>{selectedEndpoint.service}</Text>
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 8 }}>
                <Col span={12}>
                  <Text strong>方法：</Text>
                  {getMethodTag(selectedEndpoint.method)}
                </Col>
                <Col span={12}>
                  <Text strong>路径：</Text>
                  <Text code>{selectedEndpoint.path}</Text>
                </Col>
              </Row>
            </Card>

            <Card size="small" title="性能指标">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="QPS" value={selectedEndpoint.qps} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="平均响应"
                    value={selectedEndpoint.avgResponseTime}
                    suffix="ms"
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="错误率"
                    value={selectedEndpoint.errorRate}
                    suffix="%"
                    valueStyle={{
                      color: selectedEndpoint.errorRate > 1 ? '#f5222d' : '#52c41a',
                    }}
                  />
                </Col>
              </Row>
            </Card>

            <Card size="small" title="延迟分布">
              <Row gutter={16}>
                <Col span={12}>
                  <Text strong>P95 延迟：</Text>
                  <Progress
                    percent={Math.min(100, (selectedEndpoint.p95 / 5000) * 100)}
                    status={selectedEndpoint.p95 > 1000 ? 'exception' : 'normal'}
                  />
                  <Text style={{ marginLeft: 8 }}>{selectedEndpoint.p95} ms</Text>
                </Col>
                <Col span={12}>
                  <Text strong>P99 延迟：</Text>
                  <Progress
                    percent={Math.min(100, (selectedEndpoint.p99 / 5000) * 100)}
                    status={selectedEndpoint.p99 > 1000 ? 'exception' : 'normal'}
                  />
                  <Text style={{ marginLeft: 8 }}>{selectedEndpoint.p99} ms</Text>
                </Col>
              </Row>
            </Card>
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default ApiGateway;
