'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Alert,
  List,
  Select,
  Empty,
  Spin,
  message,
  Tabs,
  Descriptions,
  Tooltip,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  FundOutlined,
  SafetyCertificateOutlined,
  ClockCircleOutlined,
  LineChartOutlined,
  FileTextOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { qualityApi, sourcesApi, metadataApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;

interface QualityScore {
  overall_score: number;
  completeness_score: number;
  uniqueness_score: number;
  validity_score: number;
  consistency_score: number;
  timeliness_score: number;
  row_count: number;
  column_count: number;
  assessment: string;
}

interface QualityIssue {
  type: string;
  column?: string;
  null_percentage?: number;
  duplicate_count?: number;
  duplicate_percentage?: number;
  unique_values?: number;
  cardinality?: number;
  outlier_count?: number;
  outlier_percentage?: number;
  message: string;
}

interface QualityIssuesResponse {
  issues: {
    critical: QualityIssue[];
    warning: QualityIssue[];
    info: QualityIssue[];
  };
  total_issues: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
}

interface QualityTrend {
  date: string;
  score: number;
}

interface QualityReport {
  table_name: string;
  generated_at: string;
  summary: QualityScore & {
    total_issues: number;
    critical_issues: number;
    warning_issues: number;
  };
  issues: {
    critical: QualityIssue[];
    warning: QualityIssue[];
    info: QualityIssue[];
  };
  trend: {
    trend: QualityTrend[];
    average_score: number;
    trend_direction: string;
  };
  recommendations: Array<{
    priority: string;
    category: string;
    action: string;
    description: string;
  }>;
}

interface SourceOption {
  value: string;
  label: string;
}

interface TableOption {
  value: string;
  label: string;
  columns?: string[];
}

const getAssessmentColor = (assessment: string): string => {
  const colors: Record<string, string> = {
    Excellent: '#52c41a',
    Good: '#1890ff',
    Fair: '#faad14',
    Poor: '#ff7a45',
    Critical: '#f5222d',
  };
  return colors[assessment] || '#d9d9d9';
};

const getAssessmentIcon = (assessment: string) => {
  const icons: Record<string, React.ReactNode> = {
    Excellent: <CheckCircleOutlined />,
    Good: <CheckCircleOutlined />,
    Fair: <WarningOutlined />,
    Poor: <WarningOutlined />,
    Critical: <CloseCircleOutlined />,
  };
  return icons[assessment] || <InfoCircleOutlined />;
};

const getScoreColor = (score: number): string => {
  if (score >= 90) return '#52c41a';
  if (score >= 75) return '#1890ff';
  if (score >= 60) return '#faad14';
  if (score >= 40) return '#ff7a45';
  return '#f5222d';
};

const getPriorityTag = (priority: string) => {
  const colors: Record<string, string> = {
    high: 'red',
    medium: 'orange',
    low: 'blue',
  };
  const labels: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低',
  };
  return <Tag color={colors[priority]}>{labels[priority] || priority}</Tag>;
};

export default function QualityPage() {
  const [activeTab, setActiveTab] = useState('assessment');

  // Data sources and tables
  const [sources, setSources] = useState<SourceOption[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>();
  const [tables, setTables] = useState<TableOption[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>();

  // Quality data
  const [qualityScore, setQualityScore] = useState<QualityScore | null>(null);
  const [qualityIssues, setQualityIssues] = useState<QualityIssuesResponse | null>(null);
  const [qualityTrend, setQualityTrend] = useState<{
    trend: QualityTrend[];
    average_score: number;
    trend_direction: string;
  } | null>(null);
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);

  // Loading states
  const [loading, setLoading] = useState(false);
  const [scoreLoading, setScoreLoading] = useState(false);
  const [issuesLoading, setIssuesLoading] = useState(false);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    try {
      const response = await sourcesApi.list(0, 100);
      const sourceOptions = response.data.items.map((s: any) => ({
        value: s.id,
        label: s.name,
      }));
      setSources(sourceOptions);
    } catch (error) {
      // Silently fail
    }
  };

  const handleSourceChange = async (sourceId: string) => {
    setSelectedSource(sourceId);
    setSelectedTable(undefined);
    setTables([]);
    setQualityScore(null);
    setQualityIssues(null);
    setQualityTrend(null);
    setQualityReport(null);

    try {
      const response = await sourcesApi.getTables(sourceId);
      const tableOptions = response.data.map((t: any) => ({
        value: t.table_name,
        label: t.table_name,
      }));
      setTables(tableOptions);
    } catch (error) {
      message.error('加载表失败');
    }
  };

  const runAssessment = async () => {
    if (!selectedSource || !selectedTable) {
      message.warning('请选择数据源和表');
      return;
    }

    setScoreLoading(true);
    setIssuesLoading(true);
    setLoading(true);

    try {
      // Run all quality checks in parallel
      const [scoreResponse, issuesResponse, trendResponse, reportResponse] = await Promise.allSettled([
        qualityApi.runAssessment(selectedSource, selectedTable),
        qualityApi.getIssues({ source_id: selectedSource, table_name: selectedTable }),
        qualityApi.getTrend(`${selectedSource}:${selectedTable}`, 30).catch(() => null),
        qualityApi.getReport(`${selectedSource}:${selectedTable}`).catch(() => null),
      ]);

      if (scoreResponse.status === 'fulfilled') {
        setQualityScore(scoreResponse.value.data);
      }
      if (issuesResponse.status === 'fulfilled') {
        setQualityIssues(issuesResponse.value.data);
      }
      if (trendResponse.status === 'fulfilled' && trendResponse.value) {
        setQualityTrend(trendResponse.value.data);
      }
      if (reportResponse.status === 'fulfilled' && reportResponse.value) {
        setQualityReport(reportResponse.value.data);
      }

      message.success('质量评估完成');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '质量评估失败');
    } finally {
      setScoreLoading(false);
      setIssuesLoading(false);
      setLoading(false);
    }
  };

  const issueColumns: ColumnsType<QualityIssue> = [
    {
      title: '严重程度',
      dataIndex: 'type',
      key: 'severity',
      width: 100,
      render: (type) => {
        const isCritical = type.includes('high') || type.includes('critical');
        return (
          <Tag icon={isCritical ? <CloseCircleOutlined /> : <WarningOutlined />} color={isCritical ? 'red' : 'orange'}>
            {isCritical ? '严重' : '警告'}
          </Tag>
        );
      },
    },
    {
      title: '问题类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        const labels: Record<string, string> = {
          high_null_percentage: '高空值率',
          moderate_null_percentage: '高空值率',
          high_duplicate_percentage: '高重复率',
          duplicate_rows: '重复行',
          low_cardinality: '低基数',
          outliers_detected: '异常值',
        };
        return labels[type] || type;
      },
    },
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
    },
    {
      title: '详情',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '数值',
      key: 'value',
      width: 120,
      render: (_, record) => {
        if (record.null_percentage) return `${record.null_percentage}%`;
        if (record.duplicate_percentage) return `${record.duplicate_percentage}%`;
        if (record.outlier_percentage) return `${record.outlier_percentage}%`;
        if (record.duplicate_count) return record.duplicate_count;
        if (record.unique_values) return record.unique_values;
        return '-';
      },
    },
  ];

  const recommendationColumns: ColumnsType<QualityReport['recommendations'][0]> = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority) => getPriorityTag(priority),
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
    },
    {
      title: '行动',
      dataIndex: 'action',
      key: 'action',
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  const scoreGauge = (score: number, label: string) => (
    <div style={{ textAlign: 'center' }}>
      <Progress
        type="circle"
        percent={Math.round(score)}
        strokeColor={getScoreColor(score)}
        size={100}
        format={(percent) => (
          <span style={{ color: getScoreColor(score), fontWeight: 'bold' }}>
            {percent}
          </span>
        )}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
    </div>
  );

  const tabItems = [
    {
      key: 'assessment',
      label: (
        <Space>
          <SafetyCertificateOutlined />
          质量评估
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Selection */}
          <Card>
            <Row gutter={16} align="middle">
              <Col span={10}>
                <Select
                  placeholder="选择数据源"
                  value={selectedSource}
                  onChange={handleSourceChange}
                  options={sources}
                  style={{ width: '100%' }}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Col>
              <Col span={10}>
                <Select
                  placeholder="选择数据表"
                  value={selectedTable}
                  onChange={setSelectedTable}
                  options={tables}
                  style={{ width: '100%' }}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  disabled={!selectedSource}
                />
              </Col>
              <Col span={4}>
                <Button
                  type="primary"
                  icon={<FundOutlined />}
                  onClick={runAssessment}
                  loading={loading}
                  disabled={!selectedSource || !selectedTable}
                  block
                >
                  运行评估
                </Button>
              </Col>
            </Row>
          </Card>

          {scoreLoading ? (
            <Card>
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <Paragraph style={{ marginTop: 16 }}>正在分析数据质量...</Paragraph>
              </div>
            </Card>
          ) : qualityScore ? (
            <>
              {/* Overall Score */}
              <Card
                title={
                  <Space>
                    {getAssessmentIcon(qualityScore.assessment)}
                    <Title level={4} style={{ margin: 0 }}>
                      数据质量评分: {qualityScore.assessment}
                    </Title>
                  </Space>
                }
              >
                <Row gutter={24} style={{ marginBottom: 24 }}>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <Progress
                      type="circle"
                      percent={Math.round(qualityScore.overall_score)}
                      strokeColor={getAssessmentColor(qualityScore.assessment)}
                      size={180}
                      format={(percent) => (
                        <div>
                          <div style={{ fontSize: 36, fontWeight: 'bold', color: getAssessmentColor(qualityScore.assessment) }}>
                            {percent}
                          </div>
                          <div style={{ fontSize: 14, color: '#8c8c8c' }}>综合评分</div>
                        </div>
                      )}
                    />
                  </Col>
                  <Col span={16}>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Row gutter={[16, 16]}>
                          <Col span={12}>{scoreGauge(qualityScore.completeness_score, '完整性')}</Col>
                          <Col span={12}>{scoreGauge(qualityScore.uniqueness_score, '唯一性')}</Col>
                          <Col span={12}>{scoreGauge(qualityScore.validity_score, '有效性')}</Col>
                          <Col span={12}>{scoreGauge(qualityScore.consistency_score, '一致性')}</Col>
                          <Col span={12}>{scoreGauge(qualityScore.timeliness_score, '及时性')}</Col>
                        </Row>
                      </Col>
                      <Col span={12}>
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="数据行数">{qualityScore.row_count.toLocaleString()}</Descriptions.Item>
                          <Descriptions.Item label="数据列数">{qualityScore.column_count}</Descriptions.Item>
                          <Descriptions.Item label="评估时间">{new Date().toLocaleString()}</Descriptions.Item>
                        </Descriptions>
                      </Col>
                    </Row>
                  </Col>
                </Row>

                {/* Dimension Explanations */}
                <Alert
                  message="质量维度说明"
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text><strong>完整性</strong>: 数据缺失情况 (30%)</Text>
                      <Text><strong>唯一性</strong>: 重复数据检测 (20%)</Text>
                      <Text><strong>有效性</strong>: 数据类型合规性 (20%)</Text>
                      <Text><strong>一致性</strong>: 格式规范检查 (15%)</Text>
                      <Text><strong>及时性</strong>: 数据新鲜度 (15%)</Text>
                    </Space>
                  }
                  type="info"
                  showIcon
                />
              </Card>

              {/* Issues */}
              {qualityIssues && (
                <Card
                  title={
                    <Space>
                      <WarningOutlined />
                      质量问题 ({qualityIssues.total_issues})
                    </Space>
                  }
                >
                  {qualityIssues.total_issues === 0 ? (
                    <Empty description="未发现明显的质量问题" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <>
                      {qualityIssues.critical_count > 0 && (
                        <Alert
                          message={`${qualityIssues.critical_count} 个严重问题`}
                          type="error"
                          showIcon
                          style={{ marginBottom: 16 }}
                        />
                      )}
                      <Table
                        columns={issueColumns}
                        dataSource={[
                          ...qualityIssues.issues.critical.map((i) => ({ ...i, severity: 'critical' })),
                          ...qualityIssues.issues.warning.map((i) => ({ ...i, severity: 'warning' })),
                          ...qualityIssues.issues.info.map((i) => ({ ...i, severity: 'info' })),
                        ]}
                        rowKey={(record, index) => `${record.type}-${index}`}
                        pagination={false}
                        size="small"
                      />
                    </>
                  )}
                </Card>
              )}
            </>
          ) : (
            <Card>
              <Empty description="请选择数据源和表后运行质量评估" />
            </Card>
          )}
        </Space>
      ),
    },
    {
      key: 'trend',
      label: (
        <Space>
          <LineChartOutlined />
          质量趋势
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {!selectedSource || !selectedTable ? (
            <Card>
              <Empty description="请先运行质量评估以查看趋势数据" />
            </Card>
          ) : !qualityTrend ? (
            <Card>
              <Empty description="暂无趋势数据" />
            </Card>
          ) : (
            <Card title="质量变化趋势">
              <Row gutter={16}>
                {qualityTrend.trend.map((point) => (
                  <Col key={point.date} span={4}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                        {new Date(point.date).toLocaleDateString()}
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: getScoreColor(point.score) }}>
                        {Math.round(point.score)}
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Text>平均评分: <strong style={{ color: getScoreColor(qualityTrend.average_score) }}>
                  {Math.round(qualityTrend.average_score)}
                </strong></Text>
                <Tag
                  color={qualityTrend.trend_direction === 'up' ? 'green' : qualityTrend.trend_direction === 'down' ? 'red' : 'default'}
                  style={{ marginLeft: 8 }}
                >
                  趋势: {qualityTrend.trend_direction === 'up' ? '上升' : qualityTrend.trend_direction === 'down' ? '下降' : '稳定'}
                </Tag>
              </div>
            </Card>
          )}
        </Space>
      ),
    },
    {
      key: 'report',
      label: (
        <Space>
          <FileTextOutlined />
          质量报告
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {!qualityReport ? (
            <Card>
              <Empty description="请先运行质量评估以生成报告" />
            </Card>
          ) : (
            <>
              {/* Summary */}
              <Card title="质量报告摘要">
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="表名">{qualityReport.table_name}</Descriptions.Item>
                  <Descriptions.Item label="生成时间">{new Date(qualityReport.generated_at).toLocaleString()}</Descriptions.Item>
                  <Descriptions.Item label="综合评分">{qualityReport.summary.overall_score}</Descriptions.Item>
                  <Descriptions.Item label="评估等级">{qualityReport.summary.assessment}</Descriptions.Item>
                  <Descriptions.Item label="总问题数">{qualityReport.summary.total_issues}</Descriptions.Item>
                  <Descriptions.Item label="严重问题">{qualityReport.summary.critical_issues}</Descriptions.Item>
                  <Descriptions.Item label="警告问题">{qualityReport.summary.warning_issues}</Descriptions.Item>
                </Descriptions>
              </Card>

              {/* Recommendations */}
              <Card title="改进建议">
                <Table
                  columns={recommendationColumns}
                  dataSource={qualityReport.recommendations}
                  rowKey={(record, index) => `${record.category}-${index}`}
                  pagination={false}
                  size="small"
                />
              </Card>

              {/* Export Button */}
              <Card>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(qualityReport, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `quality-report-${selectedTable}-${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                  }}
                >
                  导出质量报告 (JSON)
                </Button>
              </Card>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <AuthGuard>
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            <Title level={4} style={{ margin: 0 }}>数据质量管理</Title>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              if (selectedSource && selectedTable) {
                runAssessment();
              }
            }}
            loading={loading}
            disabled={!selectedSource || !selectedTable}
          >
            重新评估
          </Button>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>
    </AuthGuard>
  );
}
