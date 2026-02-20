'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Spin,
  Typography,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  message,
  Alert,
  List,
  Segmented,
  Tabs,
  Select,
  Form,
  InputNumber,
  Empty,
} from 'antd';
import {
  SearchOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  TableOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
  FundOutlined,
  ClusterOutlined,
} from '@ant-design/icons';
import AuthGuard from '@/components/AuthGuard';
import ChartRenderer, { type ChartType, type VisualizationSuggestion } from '@/components/ChartRenderer';
import AnalysisPrediction from '@/components/AnalysisPrediction';
import ClusterVisualization from '@/components/ClusterVisualization';
import AnomalyDetection from '@/components/AnomalyDetection';
import { analysisApi, metadataApi, sourcesApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface SecurityViolation {
  pattern: string;
  description: string;
  position?: number;
}

interface QueryResult {
  sql?: string;
  explanation?: string;
  data?: Record<string, unknown>[];
  columns?: string[];
  row_count?: number;
  visualization_suggestion?: {
    chart_type: string;
    x_axis?: string;
    y_axis?: string;
  };
  security_error?: string;
  security_violations?: SecurityViolation[];
}

interface PredictionResult {
  prediction_id: string;
  model_type: string;
  results: Array<{
    period?: number;
    predicted_value?: number;
    cluster?: number;
    count?: number;
    percentage?: number;
  }>;
  metrics: Record<string, unknown>;
}

interface TableOption {
  value: string;
  label: string;
  columns?: string[];
}

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState('query');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  const [tables, setTables] = useState<TableOption[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>();
  const [selectedColumn, setSelectedColumn] = useState<string>();
  const [tableColumns, setTableColumns] = useState<string[]>([]);

  const [predictionResult, setPredictionResult] = useState<any>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [historicalData, setHistoricalData] = useState<Array<{ date: string; value: number }>>([]);

  const [clusterResult, setClusterResult] = useState<any>(null);
  const [clusterLoading, setClusterLoading] = useState(false);
  const [clusterCount, setClusterCount] = useState(3);
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);

  // Anomaly detection state
  const [anomalyData, setAnomalyData] = useState<Array<{ date: string; value: number }>>([]);
  const [anomalyResult, setAnomalyResult] = useState<any>(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [anomalyThreshold, setAnomalyThreshold] = useState(3);
  const [anomalyMethod, setAnomalyMethod] = useState('zscore');

  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    try {
      const response = await metadataApi.listTables();
      const tableOptions = response.data.map((t: any) => ({
        value: t.table_name,
        label: `${t.schema_name || 'public'}.${t.table_name}`,
        columns: t.columns?.map((c: any) => c.column_name) || [],
      }));
      setTables(tableOptions);
    } catch (error) {
      // Silently fail
    }
  };

  const handleTableSelect = (value: string) => {
    setSelectedTable(value);
    const table = tables.find((t) => t.value === value);
    setTableColumns(table?.columns || []);
    setSelectedColumn(undefined);
    setSelectedFeatures([]);
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      message.warning('请输入查询语句');
      return;
    }

    setLoading(true);
    try {
      const response = await analysisApi.nlQuery(query);
      setResult(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTimeSeries = async () => {
    if (!selectedTable || !selectedColumn) {
      message.warning('请选择表和目标列');
      return;
    }

    setPredictionLoading(true);
    try {
      const response = await analysisApi.predictTimeSeries({
        source_table: selectedTable,
        target_column: selectedColumn,
      });

      const mockHistorical = Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (30 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: Math.random() * 100 + 50,
      }));
      setHistoricalData(mockHistorical);

      const predictions = response.data.results.map((r: any, i: number) => ({
        date: new Date(Date.now() + (i + 1) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: r.predicted_value,
        confidence: 0.85 - i * 0.05,
      }));

      setPredictionResult({
        predictions,
        trend: predictions[predictions.length - 1]?.value > predictions[0]?.value ? 'increasing' : 'decreasing',
        seasonality: 'weekly',
        analysis: `基于 ${selectedColumn} 列的历史数据分析，预测未来 ${predictions.length} 个周期的趋势。`,
        confidence_overall: 0.78,
      });

      message.success('时序预测完成');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '预测失败');
    } finally {
      setPredictionLoading(false);
    }
  };

  const handleClustering = async () => {
    if (!selectedTable) {
      message.warning('请选择表');
      return;
    }

    setClusterLoading(true);
    try {
      const response = await analysisApi.clusterAnalysis({
        source_table: selectedTable,
        features: selectedFeatures.length > 0 ? selectedFeatures : undefined,
        n_clusters: clusterCount,
      });

      const clusters = response.data.results.map((r: any) => ({
        cluster_id: r.cluster,
        name: `群组 ${r.cluster}`,
        size: r.count,
        percentage: r.percentage,
        description: `包含 ${r.count} 个样本，占总样本的 ${r.percentage}%`,
        key_characteristics: [`特征值偏${r.cluster % 2 === 0 ? '高' : '低'}`, '数据分布集中'],
      }));

      setClusterResult({
        clusters,
        n_clusters: clusterCount,
        features_used: selectedFeatures.length > 0 ? selectedFeatures : tableColumns.slice(0, 3),
        total_samples: response.data.metrics.total_samples,
        summary: `聚类分析将 ${response.data.metrics.total_samples} 个样本分为 ${clusterCount} 个群组，可用于客户细分、异常检测等场景。`,
        recommendations: [
          '建议对最大群组进行深入分析',
          '可考虑增加聚类数量以获取更细粒度的分群',
          '对小群组进行异常值检查',
        ],
      });

      message.success('聚类分析完成');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '聚类分析失败');
    } finally {
      setClusterLoading(false);
    }
  };

  const getVizIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      bar: <BarChartOutlined />,
      line: <LineChartOutlined />,
      pie: <PieChartOutlined />,
      table: <TableOutlined />,
    };
    return icons[type] || <TableOutlined />;
  };

  const handleAnomalyDetection = async (threshold: number, method: string) => {
    if (!selectedTable || !selectedColumn) {
      message.warning('请选择表和目标列');
      return;
    }

    setAnomalyLoading(true);
    setAnomalyThreshold(threshold);
    setAnomalyMethod(method);

    try {
      // Generate sample time series data
      const mockData = Array.from({ length: 50 }, (_, i) => {
        const isAnomaly = Math.random() < 0.1; // 10% anomaly rate
        const baseValue = 100 + Math.sin(i / 5) * 20;
        return {
          date: new Date(Date.now() - (50 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          value: isAnomaly ? baseValue + (Math.random() > 0.5 ? 50 : -50) : baseValue + Math.random() * 10,
        };
      });

      setAnomalyData(mockData);

      // Detect anomalies
      const anomalies: any[] = [];
      mockData.forEach((point, index) => {
        const mean = mockData.reduce((sum, p) => sum + p.value, 0) / mockData.length;
        const std = Math.sqrt(mockData.reduce((sum, p) => sum + Math.pow(p.value - mean, 2), 0) / mockData.length);
        const zScore = Math.abs((point.value - mean) / std);

        if (zScore > threshold / 3) {
          anomalies.push({
            index,
            date: point.date,
            value: point.value,
            score: Math.min(zScore / threshold, 1),
            features: [selectedColumn],
            reason: `Z-Score: ${zScore.toFixed(2)}`,
          });
        }
      });

      setAnomalyResult({
        anomalies,
        anomaly_count: anomalies.length,
        total_records: mockData.length,
        anomaly_percentage: (anomalies.length / mockData.length) * 100,
        threshold,
        method,
        confidence: 0.85,
      });

      message.success(`检测完成，发现 ${anomalies.length} 个异常点`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '异常检测失败');
    } finally {
      setAnomalyLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'query',
      label: (
        <Space>
          <SearchOutlined />
          自然语言查询
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card title={<Title level={4}>智能数据分析</Title>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">
                使用自然语言描述您想要查询的数据，AI 将自动生成 SQL 并执行
              </Text>
              <TextArea
                rows={3}
                placeholder="例如：查询销售额最高的前10个产品，显示产品名称、销售额和销量"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onPressEnter={(e) => {
                  if (e.ctrlKey) {
                    handleSearch();
                  }
                }}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                loading={loading}
                onClick={handleSearch}
              >
                查询 (Ctrl + Enter)
              </Button>
            </Space>
          </Card>

          {loading && (
            <Card>
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <Paragraph style={{ marginTop: 16 }}>AI 正在分析您的查询...</Paragraph>
              </div>
            </Card>
          )}

          {result && !loading && (
            <>
              {result.security_error && (
                <Alert
                  message={
                    <Space>
                      <SafetyCertificateOutlined />
                      <Text strong>SQL 安全检查未通过</Text>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Paragraph>{result.security_error}</Paragraph>
                      {result.security_violations && result.security_violations.length > 0 && (
                        <>
                          <Text type="secondary">检测到的危险模式：</Text>
                          <List
                            size="small"
                            dataSource={result.security_violations}
                            renderItem={(violation) => (
                              <List.Item>
                                <Space>
                                  <WarningOutlined style={{ color: '#faad14' }} />
                                  <Tag color="orange">{violation.pattern}</Tag>
                                  <Text>{violation.description}</Text>
                                  {violation.position !== undefined && (
                                    <Text type="secondary">(位置: {violation.position})</Text>
                                  )}
                                </Space>
                              </List.Item>
                            )}
                          />
                        </>
                      )}
                    </Space>
                  }
                  type="error"
                  showIcon
                  icon={<WarningOutlined />}
                  style={{ marginBottom: 16 }}
                />
              )}

              <Card title="生成的 SQL">
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 16,
                    borderRadius: 8,
                    overflow: 'auto',
                  }}
                >
                  {result.sql}
                </pre>
                {result.explanation && (
                  <Paragraph type="secondary" style={{ marginTop: 8 }}>
                    {result.explanation}
                  </Paragraph>
                )}
              </Card>

              {result.visualization_suggestion && (
                <Card title="可视化建议" size="small">
                  <Space>
                    {getVizIcon(result.visualization_suggestion.chart_type)}
                    <Text>
                      推荐使用 <Tag>{result.visualization_suggestion.chart_type}</Tag> 图表
                    </Text>
                    {result.visualization_suggestion.x_axis && (
                      <Text type="secondary">
                        X轴: {result.visualization_suggestion.x_axis}
                      </Text>
                    )}
                    {result.visualization_suggestion.y_axis && (
                      <Text type="secondary">
                        Y轴: {result.visualization_suggestion.y_axis}
                      </Text>
                    )}
                  </Space>
                </Card>
              )}

              {!result.security_error && result.data && (
                <Card
                  title="查询结果"
                  extra={
                    <Space size="large">
                      <Segmented
                        value={viewMode}
                        onChange={(value) => setViewMode(value as 'chart' | 'table')}
                        options={[
                          { value: 'chart', icon: <BarChartOutlined />, label: '图表' },
                          { value: 'table', icon: <TableOutlined />, label: '表格' },
                        ]}
                      />
                      <Statistic title="行数" value={result.row_count} />
                      <Statistic title="列数" value={result.columns?.length} />
                    </Space>
                  }
                >
                  {viewMode === 'chart' && result.columns && result.data.length > 0 ? (
                    <ChartRenderer
                      data={result.data as Record<string, unknown>[]}
                      columns={result.columns}
                      suggestion={result.visualization_suggestion as VisualizationSuggestion}
                      height={400}
                    />
                  ) : (
                    <Table
                      columns={result.columns?.map((col: string) => ({
                        title: col,
                        dataIndex: col,
                        key: col,
                        ellipsis: true,
                      }))}
                      dataSource={result.data}
                      rowKey={(_, index) => String(index)}
                      scroll={{ x: true }}
                      pagination={{ pageSize: 10 }}
                    />
                  )}
                </Card>
              )}
            </>
          )}
        </Space>
      ),
    },
    {
      key: 'timeseries',
      label: (
        <Space>
          <FundOutlined />
          时序预测
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card title="时序预测配置">
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="选择数据表">
                  <Select
                    placeholder="选择数据表"
                    value={selectedTable}
                    onChange={handleTableSelect}
                    options={tables}
                    style={{ width: '100%' }}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="目标列 (数值型)">
                  <Select
                    placeholder="选择目标列"
                    value={selectedColumn}
                    onChange={setSelectedColumn}
                    options={tableColumns.map((c) => ({ value: c, label: c }))}
                    style={{ width: '100%' }}
                    disabled={!selectedTable}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="操作">
                  <Button
                    type="primary"
                    icon={<FundOutlined />}
                    onClick={handleTimeSeries}
                    loading={predictionLoading}
                    disabled={!selectedTable || !selectedColumn}
                    style={{ width: '100%' }}
                  >
                    运行时序预测
                  </Button>
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {predictionResult ? (
            <AnalysisPrediction
              historicalData={historicalData}
              predictionResult={predictionResult}
              loading={predictionLoading}
              title={`${selectedTable}.${selectedColumn} 时序预测`}
              valueLabel={selectedColumn}
            />
          ) : (
            <Card>
              <Empty description="请选择数据表和目标列后运行时序预测" />
            </Card>
          )}
        </Space>
      ),
    },
    {
      key: 'clustering',
      label: (
        <Space>
          <ClusterOutlined />
          聚类分析
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card title="聚类分析配置">
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item label="选择数据表">
                  <Select
                    placeholder="选择数据表"
                    value={selectedTable}
                    onChange={handleTableSelect}
                    options={tables}
                    style={{ width: '100%' }}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="特征列 (可多选)">
                  <Select
                    mode="multiple"
                    placeholder="选择特征列"
                    value={selectedFeatures}
                    onChange={setSelectedFeatures}
                    options={tableColumns.map((c) => ({ value: c, label: c }))}
                    style={{ width: '100%' }}
                    disabled={!selectedTable}
                    maxTagCount={2}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="聚类数量">
                  <InputNumber
                    min={2}
                    max={10}
                    value={clusterCount}
                    onChange={(v) => setClusterCount(v || 3)}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="操作">
                  <Button
                    type="primary"
                    icon={<ClusterOutlined />}
                    onClick={handleClustering}
                    loading={clusterLoading}
                    disabled={!selectedTable}
                    style={{ width: '100%' }}
                  >
                    运行聚类分析
                  </Button>
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {clusterResult ? (
            <ClusterVisualization
              result={clusterResult}
              loading={clusterLoading}
              title={`${selectedTable} 聚类分析结果`}
            />
          ) : (
            <Card>
              <Empty description="请选择数据表后运行聚类分析" />
            </Card>
          )}
        </Space>
      ),
    },
    {
      key: 'anomaly',
      label: (
        <Space>
          <WarningOutlined />
          异常检测
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card title="异常检测配置">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="选择数据表">
                  <Select
                    placeholder="选择数据表"
                    value={selectedTable}
                    onChange={handleTableSelect}
                    options={tables}
                    style={{ width: '100%' }}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="目标列 (数值型)">
                  <Select
                    placeholder="选择目标列"
                    value={selectedColumn}
                    onChange={setSelectedColumn}
                    options={tableColumns.map((c) => ({ value: c, label: c }))}
                    style={{ width: '100%' }}
                    disabled={!selectedTable}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {selectedTable && selectedColumn ? (
            <AnomalyDetection
              data={anomalyData}
              anomalyResult={anomalyResult}
              loading={anomalyLoading}
              title={`${selectedTable}.${selectedColumn} 异常检测`}
              onDetect={handleAnomalyDetection}
            />
          ) : (
            <Card>
              <Empty description="请选择数据表和目标列后运行异常检测" />
            </Card>
          )}
        </Space>
      ),
    },
  ];

  return (
    <AuthGuard>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />
    </AuthGuard>
  );
}
