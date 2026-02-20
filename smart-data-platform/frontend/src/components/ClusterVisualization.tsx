'use client';

import { useMemo } from 'react';
import {
  Card,
  Space,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Empty,
  Spin,
  List,
  Descriptions,
  Progress,
  Badge,
  Alert,
} from 'antd';
import {
  DotChartOutlined,
  ClusterOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { Scatter, Pie, Column } from '@ant-design/charts';

const { Title, Text, Paragraph } = Typography;

const CLUSTER_COLORS = [
  '#1890ff',
  '#52c41a',
  '#faad14',
  '#eb2f96',
  '#722ed1',
  '#13c2c2',
  '#fa541c',
  '#2f54eb',
];

export interface ClusterInfo {
  cluster_id: number;
  name?: string;
  description?: string;
  size: number;
  percentage: number;
  feature_means?: Record<string, number>;
  key_characteristics?: string[];
}

export interface ClusteringResult {
  clusters: ClusterInfo[];
  n_clusters: number;
  features_used: string[];
  total_samples: number;
  summary?: string;
  recommendations?: string[];
  data_with_clusters?: Array<Record<string, unknown>>;
}

export interface ClusterVisualizationProps {
  result?: ClusteringResult;
  loading?: boolean;
  title?: string;
  height?: number;
  xFeature?: string;
  yFeature?: string;
}

export default function ClusterVisualization({
  result,
  loading = false,
  title = '聚类分析结果',
  height = 350,
  xFeature,
  yFeature,
}: ClusterVisualizationProps) {
  const scatterData = useMemo(() => {
    if (!result?.data_with_clusters) return [];

    const xField = xFeature || result.features_used?.[0];
    const yField = yFeature || result.features_used?.[1] || result.features_used?.[0];

    return result.data_with_clusters.map((item) => ({
      x: Number(item[xField]) || 0,
      y: Number(item[yField]) || 0,
      cluster: `群组 ${item.cluster}`,
      clusterId: item.cluster,
    }));
  }, [result, xFeature, yFeature]);

  const pieData = useMemo(() => {
    if (!result?.clusters) return [];

    return result.clusters.map((cluster) => ({
      type: cluster.name || `群组 ${cluster.cluster_id}`,
      value: cluster.size,
      percentage: cluster.percentage,
    }));
  }, [result]);

  const barData = useMemo(() => {
    if (!result?.clusters) return [];

    const data: Array<{ cluster: string; feature: string; value: number }> = [];

    result.clusters.forEach((cluster) => {
      if (cluster.feature_means) {
        Object.entries(cluster.feature_means).forEach(([feature, value]) => {
          data.push({
            cluster: cluster.name || `群组 ${cluster.cluster_id}`,
            feature,
            value,
          });
        });
      }
    });

    return data;
  }, [result]);

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            正在进行聚类分析...
          </Text>
        </div>
      </Card>
    );
  }

  if (!result || !result.clusters || result.clusters.length === 0) {
    return (
      <Card title={title}>
        <Empty description="暂无聚类分析结果" />
      </Card>
    );
  }

  const scatterConfig = {
    data: scatterData,
    xField: 'x',
    yField: 'y',
    colorField: 'cluster',
    size: 5,
    shape: 'circle',
    height,
    color: CLUSTER_COLORS.slice(0, result.n_clusters),
    legend: {
      position: 'right' as const,
    },
    xAxis: {
      title: {
        text: xFeature || result.features_used?.[0] || 'X',
      },
      grid: {
        line: {
          style: {
            stroke: '#eee',
          },
        },
      },
    },
    yAxis: {
      title: {
        text: yFeature || result.features_used?.[1] || 'Y',
      },
      grid: {
        line: {
          style: {
            stroke: '#eee',
          },
        },
      },
    },
    tooltip: {
      fields: ['cluster', 'x', 'y'],
    },
  };

  const pieConfig = {
    data: pieData,
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    innerRadius: 0.5,
    height: 200,
    color: CLUSTER_COLORS.slice(0, result.n_clusters),
    label: {
      type: 'spider' as const,
      content: '{name}: {percentage}%',
    },
    legend: {
      position: 'bottom' as const,
    },
    statistic: {
      title: {
        content: '总样本数',
      },
      content: {
        content: result.total_samples.toLocaleString(),
      },
    },
  };

  const barConfig = {
    data: barData,
    isGroup: true,
    xField: 'feature',
    yField: 'value',
    seriesField: 'cluster',
    height: 250,
    color: CLUSTER_COLORS.slice(0, result.n_clusters),
    legend: {
      position: 'top' as const,
    },
    label: {
      position: 'middle' as const,
      style: {
        fill: '#fff',
        fontSize: 10,
      },
    },
  };

  return (
    <Card
      title={
        <Space>
          <ClusterOutlined />
          <span>{title}</span>
          <Badge count={`${result.n_clusters} 个群组`} style={{ backgroundColor: '#1890ff' }} />
        </Space>
      }
    >
      <Row gutter={[16, 16]}>
        {/* Summary Statistics */}
        <Col span={24}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="群组数量" value={result.n_clusters} suffix="个" />
            </Col>
            <Col span={6}>
              <Statistic title="总样本数" value={result.total_samples} />
            </Col>
            <Col span={6}>
              <Statistic title="使用特征数" value={result.features_used?.length || 0} suffix="个" />
            </Col>
            <Col span={6}>
              <Statistic
                title="最大群组占比"
                value={Math.max(...result.clusters.map((c) => c.percentage))}
                suffix="%"
                precision={1}
              />
            </Col>
          </Row>
        </Col>

        {/* AI Summary */}
        {result.summary && (
          <Col span={24}>
            <Alert
              message="AI 聚类洞察"
              description={result.summary}
              type="info"
              showIcon
              icon={<BulbOutlined />}
            />
          </Col>
        )}

        {/* Scatter Plot and Pie Chart */}
        <Col span={16}>
          <Card title="聚类分布散点图" size="small">
            {scatterData.length > 0 ? (
              <Scatter {...scatterConfig} />
            ) : (
              <Empty description="无法生成散点图，缺少必要的特征数据" />
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="群组占比" size="small">
            <Pie {...pieConfig} />
          </Card>
        </Col>

        {/* Feature Comparison */}
        {barData.length > 0 && (
          <Col span={24}>
            <Card title="各群组特征均值对比" size="small">
              <Column {...barConfig} />
            </Card>
          </Col>
        )}

        {/* Cluster Details */}
        <Col span={24}>
          <Card title="群组详情" size="small">
            <List
              grid={{ gutter: 16, column: result.n_clusters <= 4 ? result.n_clusters : 4 }}
              dataSource={result.clusters}
              renderItem={(cluster, index) => (
                <List.Item>
                  <Card
                    size="small"
                    title={
                      <Space>
                        <div
                          style={{
                            width: 12,
                            height: 12,
                            borderRadius: '50%',
                            backgroundColor: CLUSTER_COLORS[index % CLUSTER_COLORS.length],
                          }}
                        />
                        <Text strong>{cluster.name || `群组 ${cluster.cluster_id}`}</Text>
                      </Space>
                    }
                    extra={
                      <Tag color={CLUSTER_COLORS[index % CLUSTER_COLORS.length]}>
                        {cluster.percentage.toFixed(1)}%
                      </Tag>
                    }
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Statistic
                        title="样本数量"
                        value={cluster.size}
                        valueStyle={{ fontSize: 20 }}
                      />
                      <Progress
                        percent={cluster.percentage}
                        strokeColor={CLUSTER_COLORS[index % CLUSTER_COLORS.length]}
                        showInfo={false}
                        size="small"
                      />
                      {cluster.description && (
                        <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                          {cluster.description}
                        </Paragraph>
                      )}
                      {cluster.key_characteristics && cluster.key_characteristics.length > 0 && (
                        <div>
                          <Text type="secondary">关键特征：</Text>
                          <div style={{ marginTop: 4 }}>
                            {cluster.key_characteristics.slice(0, 3).map((char, i) => (
                              <Tag key={i} style={{ marginBottom: 4 }}>
                                {char}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* Recommendations */}
        {result.recommendations && result.recommendations.length > 0 && (
          <Col span={24}>
            <Card title="AI 建议" size="small">
              <List
                dataSource={result.recommendations}
                renderItem={(item, index) => (
                  <List.Item>
                    <Space>
                      <Badge count={index + 1} style={{ backgroundColor: '#1890ff' }} />
                      <Text>{item}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        )}
      </Row>
    </Card>
  );
}
