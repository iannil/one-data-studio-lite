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
  Empty,
  Spin,
  Descriptions,
  Progress,
  Alert,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { Line, DualAxes } from '@ant-design/charts';

const { Title, Text } = Typography;

export interface PredictionPoint {
  date: string;
  value: number;
  confidence?: number;
  type?: 'historical' | 'predicted';
}

export interface TimeSeriesPredictionResult {
  predictions: Array<{
    date: string;
    value: number;
    confidence: number;
  }>;
  trend: 'increasing' | 'decreasing' | 'stable';
  seasonality: 'daily' | 'weekly' | 'monthly' | 'none';
  analysis: string;
  confidence_overall: number;
}

export interface AnalysisPredictionProps {
  historicalData: Array<{ date: string; value: number }>;
  predictionResult?: TimeSeriesPredictionResult;
  loading?: boolean;
  title?: string;
  valueLabel?: string;
  height?: number;
}

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case 'increasing':
      return <ArrowUpOutlined style={{ color: '#52c41a' }} />;
    case 'decreasing':
      return <ArrowDownOutlined style={{ color: '#ff4d4f' }} />;
    default:
      return <MinusOutlined style={{ color: '#8c8c8c' }} />;
  }
};

const getTrendColor = (trend: string) => {
  switch (trend) {
    case 'increasing':
      return 'green';
    case 'decreasing':
      return 'red';
    default:
      return 'default';
  }
};

const getSeasonalityLabel = (seasonality: string) => {
  const labels: Record<string, string> = {
    daily: '日周期',
    weekly: '周周期',
    monthly: '月周期',
    none: '无明显周期',
  };
  return labels[seasonality] || seasonality;
};

export default function AnalysisPrediction({
  historicalData,
  predictionResult,
  loading = false,
  title = '时序预测分析',
  valueLabel = '数值',
  height = 400,
}: AnalysisPredictionProps) {
  const chartData = useMemo(() => {
    const combined: PredictionPoint[] = [];

    historicalData.forEach((item) => {
      combined.push({
        date: item.date,
        value: item.value,
        type: 'historical',
      });
    });

    if (predictionResult?.predictions) {
      predictionResult.predictions.forEach((item) => {
        combined.push({
          date: item.date,
          value: item.value,
          confidence: item.confidence,
          type: 'predicted',
        });
      });
    }

    return combined;
  }, [historicalData, predictionResult]);

  const confidenceBandData = useMemo(() => {
    if (!predictionResult?.predictions) return [];

    return predictionResult.predictions.map((item) => {
      const margin = item.value * (1 - item.confidence) * 0.5;
      return {
        date: item.date,
        upper: item.value + margin,
        lower: item.value - margin,
        value: item.value,
      };
    });
  }, [predictionResult]);

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            正在进行时序预测分析...
          </Text>
        </div>
      </Card>
    );
  }

  if (!historicalData || historicalData.length === 0) {
    return (
      <Card title={title}>
        <Empty description="暂无历史数据，无法进行预测分析" />
      </Card>
    );
  }

  const chartConfig = {
    data: chartData,
    xField: 'date',
    yField: 'value',
    seriesField: 'type',
    height,
    smooth: true,
    color: ['#1890ff', '#ff7a45'],
    point: {
      size: 4,
      shape: 'circle',
    },
    legend: {
      position: 'top' as const,
      itemName: {
        formatter: (text: string) => {
          return text === 'historical' ? '历史数据' : '预测数据';
        },
      },
    },
    tooltip: {
      formatter: (datum: PredictionPoint) => {
        return {
          name: datum.type === 'historical' ? '历史数据' : '预测数据',
          value: datum.value.toFixed(2),
        };
      },
    },
    xAxis: {
      label: {
        autoRotate: true,
        autoHide: true,
      },
    },
    yAxis: {
      title: {
        text: valueLabel,
      },
    },
    annotations: predictionResult
      ? [
          {
            type: 'regionFilter',
            start: [historicalData[historicalData.length - 1]?.date || 0, 'min'],
            end: ['max', 'max'],
            color: '#fff7e6',
          },
        ]
      : [],
  };

  return (
    <Card
      title={
        <Space>
          <LineChartOutlined />
          <span>{title}</span>
        </Space>
      }
    >
      <Row gutter={[16, 16]}>
        {predictionResult && (
          <>
            <Col span={24}>
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="整体置信度"
                    value={predictionResult.confidence_overall * 100}
                    precision={1}
                    suffix="%"
                    valueStyle={{
                      color:
                        predictionResult.confidence_overall >= 0.7
                          ? '#52c41a'
                          : predictionResult.confidence_overall >= 0.5
                          ? '#faad14'
                          : '#ff4d4f',
                    }}
                  />
                  <Progress
                    percent={predictionResult.confidence_overall * 100}
                    showInfo={false}
                    strokeColor={
                      predictionResult.confidence_overall >= 0.7
                        ? '#52c41a'
                        : predictionResult.confidence_overall >= 0.5
                        ? '#faad14'
                        : '#ff4d4f'
                    }
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="趋势方向"
                    value={
                      predictionResult.trend === 'increasing'
                        ? '上升'
                        : predictionResult.trend === 'decreasing'
                        ? '下降'
                        : '平稳'
                    }
                    prefix={getTrendIcon(predictionResult.trend)}
                    valueStyle={{
                      color:
                        predictionResult.trend === 'increasing'
                          ? '#52c41a'
                          : predictionResult.trend === 'decreasing'
                          ? '#ff4d4f'
                          : '#8c8c8c',
                    }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="周期性"
                    value={getSeasonalityLabel(predictionResult.seasonality)}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="预测周期数"
                    value={predictionResult.predictions?.length || 0}
                    suffix="个"
                  />
                </Col>
              </Row>
            </Col>

            {predictionResult.analysis && (
              <Col span={24}>
                <Alert
                  message="AI 分析洞察"
                  description={predictionResult.analysis}
                  type="info"
                  showIcon
                />
              </Col>
            )}
          </>
        )}

        <Col span={24}>
          <Line {...chartConfig} />
        </Col>

        {predictionResult?.predictions && predictionResult.predictions.length > 0 && (
          <Col span={24}>
            <Card title="预测详情" size="small">
              <Descriptions bordered size="small" column={4}>
                {predictionResult.predictions.slice(0, 8).map((pred, index) => (
                  <Descriptions.Item
                    key={index}
                    label={
                      <Space>
                        <Text type="secondary">{pred.date}</Text>
                      </Space>
                    }
                  >
                    <Space>
                      <Text strong>{pred.value.toFixed(2)}</Text>
                      <Tag color={pred.confidence >= 0.7 ? 'green' : pred.confidence >= 0.5 ? 'orange' : 'red'}>
                        {(pred.confidence * 100).toFixed(0)}%
                      </Tag>
                    </Space>
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          </Col>
        )}
      </Row>
    </Card>
  );
}
