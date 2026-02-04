import React, { useState } from 'react';
import { Card, Input, Button, message, Typography, Space, Spin, Table, Tag, Statistic, Row, Col } from 'antd';
import { CheckCircleOutlined, SearchOutlined } from '@ant-design/icons';
import { analyzeQualityV1 } from '../../api/cleaning';

const { Title } = Typography;

const QualityCheck: React.FC = () => {
  const [tableName, setTableName] = useState('');
  const [database, setDatabase] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QualityReport | null>(null);

  interface QualityReport {
    total_columns?: number;
    total_rows?: number;
    issues?: QualityIssue[];
    quality_issues?: QualityIssue[];
    quality_score?: number;
  }

  interface QualityIssue {
    column?: string;
    issue_type?: string;
    description?: string;
    severity?: string;
    affected_ratio?: number;
  }

  const handleAnalyze = async () => {
    if (!tableName.trim()) {
      message.warning('请输入表名');
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const resp = await analyzeQualityV1({
        table_name: tableName,
        database: database || undefined,
        sample_size: 1000,
      });
      if (resp.success && resp.data) {
        setResult(resp.data);
        message.success('质量分析完成');
      } else {
        message.error(resp.message || '分析失败');
      }
    } catch {
      message.error('质量分析失败');
    } finally {
      setLoading(false);
    }
  };

  const issueColumns = [
    { title: '字段名', dataIndex: 'column', key: 'column' },
    {
      title: '问题类型',
      dataIndex: 'issue_type',
      key: 'issue_type',
      render: (text: string) => <Tag color="orange">{text}</Tag>,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (text: string) => {
        const colors: Record<string, string> = { high: 'red', medium: 'orange', low: 'green' };
        return <Tag color={colors[text] || 'default'}>{text}</Tag>;
      },
    },
    {
      title: '影响比例',
      dataIndex: 'affected_ratio',
      key: 'affected_ratio',
      render: (v: number) => v != null ? `${(v * 100).toFixed(1)}%` : '-',
    },
  ];

  const issues = result?.issues || result?.quality_issues || [];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <CheckCircleOutlined /> 数据质量检测
      </Title>
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <Card size="small">
          <Space>
            <Input
              placeholder="数据库名（可选）"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              style={{ width: 200 }}
            />
            <Input
              placeholder="表名，如 user_info"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              onPressEnter={handleAnalyze}
              style={{ width: 300 }}
              prefix={<SearchOutlined />}
            />
            <Button type="primary" loading={loading} onClick={handleAnalyze}>
              开始检测
            </Button>
          </Space>
        </Card>

        {loading && <Spin />}

        {result && (
          <>
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic title="总列数" value={result.total_columns || '-'} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="总行数" value={result.total_rows || '-'} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="问题数"
                    value={issues.length}
                    valueStyle={{ color: issues.length > 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="质量评分"
                    value={result.quality_score != null ? `${(result.quality_score * 100).toFixed(0)}` : '-'}
                    suffix="/100"
                  />
                </Card>
              </Col>
            </Row>

            <Card title="质量问题" size="small">
              <Table
                columns={issueColumns}
                dataSource={issues.map((issue: QualityIssue, i: number) => ({ ...issue, key: i }))}
                pagination={false}
                size="small"
                locale={{ emptyText: '未发现质量问题' }}
              />
            </Card>
          </>
        )}
      </Space>
    </div>
  );
};

export default QualityCheck;
