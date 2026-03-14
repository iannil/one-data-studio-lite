'use client';

import { useState, useMemo } from 'react';
import {
  Card,
  Space,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Table,
  Alert,
  Empty,
  Spin,
  Select,
  Slider,
  Progress,
  Tooltip,
  Button,
} from 'antd';
import {
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DotChartOutlined,
} from '@ant-design/icons';
import { Scatter } from '@ant-design/charts';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { Option } = Select;

export interface AnomalyDataPoint {
  id?: string | number;
  date?: string;
  value: number;
  feature1?: number;
  feature2?: number;
  label?: string;
}

export interface AnomalyResult {
  anomalies: Array<{
    index: number;
    score: number;
    features: string[];
    date?: string;
    value?: number;
    reason?: string;
  }>;
  anomaly_count: number;
  total_records: number;
  anomaly_percentage: number;
  threshold: number;
  method: string;
  confidence: number;
}

export interface AnomalyDetectionProps {
  data: AnomalyDataPoint[];
  anomalyResult?: AnomalyResult;
  loading?: boolean;
  title?: string;
  onDetect?: (threshold: number, method: string) => void;
  height?: number;
}

const getScoreColor = (score: number): string => {
  if (score >= 0.8) return '#f5222d';
  if (score >= 0.6) return '#fa8c16';
  if (score >= 0.4) return '#faad14';
  return '#52c41a';
};

const getScoreLevel = (score: number): { text: string; color: string; icon: React.ReactNode } => {
  if (score >= 0.8) {
    return { text: '严重', color: 'red', icon: <CloseCircleOutlined /> };
  }
  if (score >= 0.6) {
    return { text: '高度异常', color: 'orange', icon: <WarningOutlined /> };
  }
  if (score >= 0.4) {
    return { text: '中度异常', color: 'gold', icon: <WarningOutlined /> };
  }
  return { text: '正常', color: 'green', icon: <CheckCircleOutlined /> };
};

export default function AnomalyDetection({
  data,
  anomalyResult,
  loading = false,
  title = '异常检测分析',
  onDetect,
  height = 400,
}: AnomalyDetectionProps) {
  const [threshold, setThreshold] = useState(3);
  const [method, setMethod] = useState('zscore');

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    const anomalies = new Set(
      anomalyResult?.anomalies.map((a) => a.index) || []
    );

    return data.map((point, index) => ({
      x: point.date || index,
      y: point.value,
      isAnomaly: anomalies.has(index),
      score: anomalyResult?.anomalies.find((a) => a.index === index)?.score || 0,
      label: point.label || `点 ${index}`,
    }));
  }, [data, anomalyResult]);

  const anomalyColumns: ColumnsType<AnomalyResult['anomalies'][0]> = [
    {
      title: '索引',
      dataIndex: 'index',
      key: 'index',
      width: 80,
    },
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      render: (date) => date || '-',
    },
    {
      title: '异常值',
      dataIndex: 'value',
      key: 'value',
      render: (value) => value?.toFixed(2) || '-',
    },
    {
      title: '异常分数',
      dataIndex: 'score',
      key: 'score',
      width: 150,
      render: (score) => (
        <Space>
          <Progress
            percent={Math.min(score * 100, 100)}
            size="small"
            strokeColor={getScoreColor(score)}
            format={() => (score * 100).toFixed(1) + '%'}
            style={{ width: 80 }}
          />
          <Tag color={getScoreLevel(score).color}>
            {getScoreLevel(score).text}
          </Tag>
        </Space>
      ),
    },
    {
      title: '涉及特征',
      dataIndex: 'features',
      key: 'features',
      render: (features: string[]) => (
        <Space size="small" wrap>
          {features?.map((f) => <Tag key={f}>{f}</Tag>) || '-'}
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            正在进行异常检测分析...
          </Text>
        </div>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card title={title}>
        <Empty description="暂无数据，无法进行异常检测" />
      </Card>
    );
  }

  const chartConfig = {
    data: chartData,
    xField: 'x',
    yField: 'y',
    colorField: 'isAnomaly',
    color: ['#52c41a', '#f5222d'],
    size: 5,
    shape: 'circle',
    pointStyle: ({ isAnomaly }: { isAnomaly: boolean }) => (isAnomaly ? 'diamond' : 'circle'),
    xAxis: {
      title: '时间 / 索引',
      label: {
        autoRotate: true,
        autoHide: true,
      },
    },
    yAxis: {
      title: '数值',
    },
    tooltip: {
      fields: ['x', 'y', 'label'],
      formatter: (datum: typeof chartData[0]) => {
        return {
          name: datum.label,
          value: `值: ${datum.y.toFixed(2)}${datum.isAnomaly ? ' (异常)' : ''}`,
        };
      },
    },
    legend: {
      position: 'top' as const,
      itemName: {
        formatter: (text: string) => (text === 'true' ? '异常点' : '正常点'),
      },
    },
  };

  return (
    <Card
      title={
        <Space>
          <DotChartOutlined />
          <span>{title}</span>
        </Space>
      }
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Controls */}
        <Row gutter={16} align="middle">
          <Col span={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">检测方法</Text>
              <Select
                value={method}
                onChange={setMethod}
                style={{ width: '100%' }}
              >
                <Option value="zscore">Z-Score</Option>
                <Option value="iqr">IQR (四分位距)</Option>
                <Option value="isolation_forest">Isolation Forest</Option>
                <Option value="lof">LOF (局部异常因子)</Option>
              </Select>
            </Space>
          </Col>
          <Col span={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">
                阈值: {threshold}
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  ({method === 'zscore' || method === 'lof' ? '标准差' : '倍数'})
                </Text>
              </Text>
              <Slider
                min={1}
                max={5}
                step={0.5}
                value={threshold}
                onChange={setThreshold}
              />
            </Space>
          </Col>
          <Col span={12}>
            <Space style={{ float: 'right' }}>
              <Button onClick={() => onDetect?.(threshold, method)}>
                重新检测
              </Button>
            </Space>
          </Col>
        </Row>

        {/* Statistics */}
        {anomalyResult && (
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="检测到的异常"
                value={anomalyResult.anomaly_count}
                valueStyle={{ color: anomalyResult.anomaly_count > 0 ? '#f5222d' : '#52c41a' }}
                prefix={<WarningOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="异常比例"
                value={anomalyResult.anomaly_percentage}
                precision={2}
                suffix="%"
                valueStyle={{
                  color: anomalyResult.anomaly_percentage > 10 ? '#f5222d' : '#52c41a',
                }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="检测方法"
                value={method.toUpperCase()}
                valueStyle={{ fontSize: 16, color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="置信度"
                value={anomalyResult.confidence * 100}
                precision={1}
                suffix="%"
              />
            </Col>
          </Row>
        )}

        {/* Alert if no anomalies found */}
        {anomalyResult && anomalyResult.anomaly_count === 0 && (
          <Alert
            message="未检测到异常"
            description="在当前数据中未发现异常点，数据质量良好。"
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
          />
        )}

        {/* Alert if many anomalies found */}
        {anomalyResult && anomalyResult.anomaly_percentage > 20 && (
          <Alert
            message="检测到大量异常"
            description={`发现 ${anomalyResult.anomaly_count} 个异常点 (${anomalyResult.anomaly_percentage.toFixed(1)}%)，请检查数据源质量或调整检测阈值。`}
            type="warning"
            showIcon
          />
        )}

        {/* Chart */}
        <Scatter {...chartConfig} height={height} />

        {/* Anomalies Table */}
        {anomalyResult && anomalyResult.anomaly_count > 0 && (
          <Card title="异常点详情" size="small">
            <Table
              columns={anomalyColumns}
              dataSource={anomalyResult.anomalies}
              rowKey="index"
              pagination={{ pageSize: 10 }}
              size="small"
              scroll={{ y: 300 }}
            />
          </Card>
        )}

        {/* Recommendations */}
        {anomalyResult && anomalyResult.anomaly_count > 0 && (
          <Card title="处理建议" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>
                • <strong>立即处理</strong>: 优先检查严重异常（分数 &gt; 80%）的数据点
              </Text>
              <Text>
                • <strong>数据清洗</strong>: 考虑使用中位数或移动平均值替换异常值
              </Text>
              <Text>
                • <strong>根本原因</strong>: 分析异常发生的时间模式，识别潜在的数据采集问题
              </Text>
              <Text>
                • <strong>持续监控</strong>: 对检测到的异常模式设置告警规则
              </Text>
            </Space>
          </Card>
        )}
      </Space>
    </Card>
  );
}
