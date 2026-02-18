'use client';

import { useState } from 'react';
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
} from 'antd';
import {
  SearchOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  TableOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import AuthGuard from '@/components/AuthGuard';
import ChartRenderer, { type ChartType, type VisualizationSuggestion } from '@/components/ChartRenderer';
import { analysisApi } from '@/services/api';

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

export default function AnalysisPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

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

  const getVizIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      bar: <BarChartOutlined />,
      line: <LineChartOutlined />,
      pie: <PieChartOutlined />,
      table: <TableOutlined />,
    };
    return icons[type] || <TableOutlined />;
  };

  return (
    <AuthGuard>
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
            {/* Security Warning - Show when SQL is blocked */}
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
                    <Text type="secondary">
                      提示：本系统仅支持 SELECT、WITH (CTE) 和 EXPLAIN 查询语句，不允许执行修改数据的操作。
                    </Text>
                  </Space>
                }
                type="error"
                showIcon
                icon={<WarningOutlined />}
                style={{ marginBottom: 16 }}
              />
            )}

            {/* Generated SQL */}
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

            {/* Query Results - Only show when there's no security error and data exists */}
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

            {/* Security blocked message when no data */}
            {result.security_error && (
              <Card>
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <SafetyCertificateOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />
                  <Paragraph style={{ marginTop: 16 }}>
                    <Text type="secondary">
                      查询因安全原因被阻止，请修改查询语句后重试。
                    </Text>
                  </Paragraph>
                </div>
              </Card>
            )}
          </>
        )}
      </Space>
    </AuthGuard>
  );
}
