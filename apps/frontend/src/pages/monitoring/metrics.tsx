/**
 * Prometheus Metrics Viewer Page
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Table,
  Tag,
  Select,
  Row,
  Col,
  Statistic,
  Alert,
  Spin,
  Tabs,
  Descriptions,
} from 'antd';
import {
  SearchOutlined,
  CopyOutlined,
  ReloadOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { useMonitoringStore } from '@/stores/monitoring';
import { monitoringApi } from '@/services/api/monitoring';
import styles from './monitoring.module.scss';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { TabPane } = Tabs;

interface MetricData {
  name: string;
  type: string;
  help: string;
  value: number | string;
  labels?: Record<string, string>;
}

const parsePrometheusMetrics = (metricsText: string): MetricData[] => {
  const metrics: MetricData[] = [];
  const lines = metricsText.split('\n');
  let currentMetric: Partial<MetricData> | null = null;
  let currentType = 'unknown';
  let currentHelp = '';

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip comments and empty lines
    if (!trimmed || trimmed.startsWith('#')) {
      // Parse TYPE and HELP comments
      if (trimmed.startsWith('# TYPE ')) {
        const parts = trimmed.split(' ');
        if (parts.length >= 4) {
          currentType = parts[3];
        }
      } else if (trimmed.startsWith('# HELP ')) {
        const parts = trimmed.split(' ');
        if (parts.length >= 4) {
          currentHelp = parts.slice(3).join(' ');
        }
      }
      continue;
    }

    // Parse metric lines
    if (trimmed.includes('{')) {
      // Metric with labels
      const match = trimmed.match(/^([^{]+)\{([^}]+)\}\s+(.+)$/);
      if (match) {
        const [, name, labelsStr, value] = match;

        // Parse labels
        const labels: Record<string, string> = {};
        labelsStr.split(',').forEach((label) => {
          const [key, val] = label.split('=');
          if (key && val) {
            labels[key.trim()] = val.replace(/"/g, '').trim();
          }
        });

        currentMetric = {
          name: name.trim(),
          type: currentType,
          help: currentHelp,
          value: isNaN(parseFloat(value)) ? value : parseFloat(value),
          labels,
        };
        metrics.push(currentMetric as MetricData);
      }
    } else {
      // Metric without labels
      const parts = trimmed.split(/\s+/);
      if (parts.length >= 2) {
        currentMetric = {
          name: parts[0].trim(),
          type: currentType,
          help: currentHelp,
          value: isNaN(parseFloat(parts[1])) ? parts[1] : parseFloat(parts[1]),
        };
        metrics.push(currentMetric as MetricData);
      }
    }
  }

  return metrics;
};

const METRIC_CATEGORIES = {
  http: { label: 'HTTP', color: 'blue', icon: <CloudServerOutlined /> },
  db: { label: 'Database', color: 'green', icon: <DatabaseOutlined /> },
  system: { label: 'System', color: 'orange', icon: <ThunderboltOutlined /> },
  gpu: { label: 'GPU', color: 'purple', icon: <LineChartOutlined /> },
  business: { label: 'Business', color: 'cyan', icon: <LineChartOutlined /> },
  queue: { label: 'Queue', color: 'geekblue', icon: <LineChartOutlined /> },
};

const MetricsPage: React.FC = () => {
  const { metricsText, metricsLoading, fetchMetrics } = useMonitoringStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [copiedMetric, setCopiedMetric] = useState<string | null>(null);
  const [parsedMetrics, setParsedMetrics] = useState<MetricData[]>([]);

  useEffect(() => {
    loadMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (metricsText) {
      setParsedMetrics(parsePrometheusMetrics(metricsText));
    }
  }, [metricsText]);

  const loadMetrics = () => {
    fetchMetrics();
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMetric(text);
    setTimeout(() => setCopiedMetric(null), 2000);
  };

  const getMetricCategory = (metricName: string): string | undefined => {
    if (metricName.startsWith('http_')) return 'http';
    if (metricName.startsWith('db_')) return 'db';
    if (metricName.includes('cpu') || metricName.includes('memory')) return 'system';
    if (metricName.includes('gpu')) return 'gpu';
    if (metricName.includes('queue') || metricName.includes('celery')) return 'queue';
    if (metricName.includes('notebook') || metricName.includes('training') || metricName.includes('workflow')) {
      return 'business';
    }
    return undefined;
  };

  const filteredMetrics = parsedMetrics.filter((metric) => {
    const matchesSearch = !searchQuery ||
      metric.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      metric.help.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory = !selectedCategory || getMetricCategory(metric.name) === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  // Group metrics by name
  const groupedMetrics = filteredMetrics.reduce((acc, metric) => {
    if (!acc[metric.name]) {
      acc[metric.name] = [];
    }
    acc[metric.name].push(metric);
    return acc;
  }, {} as Record<string, MetricData[]>);

  const metricsList = Object.entries(groupedMetrics).map(([name, instances]) => ({
    name,
    type: instances[0].type,
    help: instances[0].help,
    instances,
    category: getMetricCategory(name),
  }));

  // Calculate summary statistics
  const summary = {
    totalMetrics: Object.keys(groupedMetrics).length,
    totalInstances: parsedMetrics.length,
    httpCount: parsedMetrics.filter((m) => getMetricCategory(m.name) === 'http').length,
    dbCount: parsedMetrics.filter((m) => getMetricCategory(m.name) === 'db').length,
  };

  const columns = [
    {
      title: 'Metric Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space direction="vertical" size={0}>
          <Text code copyable={{ text: name }}>
            {name}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          counter: 'green',
          gauge: 'blue',
          histogram: 'orange',
          summary: 'purple',
        };
        return <Tag color={colorMap[type.toLowerCase()] || 'default'}>{type.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Description',
      dataIndex: 'help',
      key: 'help',
      ellipsis: true,
      render: (help: string) => <Text type="secondary">{help || '-'}</Text>,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string | undefined) => {
        if (!category) return <Text type="secondary">-</Text>;
        const config = METRIC_CATEGORIES[category as keyof typeof METRIC_CATEGORIES];
        return (
          <Tag color={config?.color} icon={config?.icon}>
            {config?.label}
          </Tag>
        );
      },
    },
    {
      title: 'Instances',
      dataIndex: 'instances',
      key: 'instances',
      width: 100,
      render: (instances: MetricData[]) => (
        <Tag>{instances.length}</Tag>
      ),
    },
    {
      title: 'Current Value',
      key: 'value',
      width: 150,
      render: (_: any, record: { instances: MetricData[] }) => {
        const instance = record.instances[0];
        if (typeof instance.value === 'number') {
          return <Text code>{instance.value.toFixed(2)}</Text>;
        }
        return <Text type="secondary">N/A</Text>;
      },
    },
  ];

  return (
    <div className={styles.monitoringDashboard}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <Title level={2}>
            <LineChartOutlined className={styles.titleIcon} />
            Prometheus Metrics
          </Title>
          <Text type="secondary">Real-time system metrics exported for Prometheus</Text>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadMetrics}
          loading={metricsLoading}
        >
          Refresh
        </Button>
      </div>

      {/* Summary Statistics */}
      <Row gutter={16} className={styles.summaryRow}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Metrics"
              value={summary.totalMetrics}
              prefix={<LineChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Instances"
              value={summary.totalInstances}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="HTTP Metrics"
              value={summary.httpCount}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Database Metrics"
              value={summary.dbCount}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs defaultActiveKey="table">
          <TabPane tab="Metrics Table" key="table">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* Search and Filter */}
              <Row gutter={16}>
                <Col span={12}>
                  <Search
                    placeholder="Search metrics by name or description..."
                    allowClear
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    prefix={<SearchOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Select
                    placeholder="Filter by category"
                    allowClear
                    style={{ width: '100%' }}
                    value={selectedCategory}
                    onChange={setSelectedCategory}
                  >
                    {Object.entries(METRIC_CATEGORIES).map(([key, config]) => (
                      <Select.Option key={key} value={key}>
                        <Space>
                          {config.icon}
                          {config.label}
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Col>
              </Row>

              {/* Metrics Table */}
              <Table
                columns={columns}
                dataSource={metricsList}
                rowKey="name"
                loading={metricsLoading}
                pagination={{
                  pageSize: 20,
                  showSizeChanger: true,
                  showTotal: (total) => `Total ${total} metrics`,
                }}
                expandable={{
                  expandedRowRender: (record) => (
                    <div style={{ padding: '16px 0' }}>
                      <Text strong>Instances:</Text>
                      <Table
                        size="small"
                        columns={[
                          {
                            title: 'Labels',
                            dataIndex: 'labels',
                            key: 'labels',
                            render: (labels: Record<string, string>) => (
                              <Space size={4} wrap>
                                {Object.entries(labels).map(([key, value]) => (
                                  <Tag key={key}>{key}={value}</Tag>
                                ))}
                              </Space>
                            ),
                          },
                          {
                            title: 'Value',
                            dataIndex: 'value',
                            key: 'value',
                            render: (value: number | string) => (
                              <Text code>
                                {typeof value === 'number' ? value.toFixed(4) : value}
                              </Text>
                            ),
                          },
                        ]}
                        dataSource={record.instances}
                        rowKey={(r, i) => `${r.name}-${i}`}
                        pagination={false}
                      />
                    </div>
                  ),
                }}
              />
            </Space>
          </TabPane>

          <TabPane tab="Raw Output" key="raw">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="Prometheus Text Format"
                description="This endpoint exports metrics in Prometheus text format. Configure Prometheus to scrape this endpoint."
                type="info"
                showIcon
              />
              <Card>
                <pre
                  style={{
                    background: '#1e1e1e',
                    color: '#d4d4d4',
                    padding: 16,
                    borderRadius: 4,
                    overflow: 'auto',
                    maxHeight: 600,
                    fontSize: 12,
                  }}
                >
                  {metricsText || 'No metrics available'}
                </pre>
              </Card>
            </Space>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default MetricsPage;
