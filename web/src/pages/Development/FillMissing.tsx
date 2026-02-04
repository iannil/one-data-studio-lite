import React, { useState } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Select,
  message,
  Typography,
  Space,
  Statistic,
  Row,
  Col,
  Spin,
  Alert,
} from 'antd';
import { FieldNumberOutlined, SearchOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { analyzeQualityV1 } from '../../api/cleaning';

const { Title, Text } = Typography;

type FillStrategy = 'mean' | 'median' | 'mode' | 'fixed' | 'forward' | 'remove';

interface FieldNullInfo {
  column: string;
  nullCount: number;
  nullPercentage: number;
  dataType: string;
  strategy?: FillStrategy;
  fixedValue?: string;
}

const strategyOptions: { label: string; value: FillStrategy; dataTypes: string[] }[] = [
  { label: '均值填充', value: 'mean', dataTypes: ['number', 'integer', 'float'] },
  { label: '中位数填充', value: 'median', dataTypes: ['number', 'integer', 'float'] },
  { label: '众数填充', value: 'mode', dataTypes: ['string', 'number', 'integer', 'float', 'date'] },
  { label: '固定值', value: 'fixed', dataTypes: ['string', 'number', 'integer', 'float', 'date', 'boolean'] },
  { label: '前值填充', value: 'forward', dataTypes: ['string', 'number', 'integer', 'float', 'date'] },
  { label: '删除行', value: 'remove', dataTypes: ['string', 'number', 'integer', 'float', 'date', 'boolean'] },
];

const FillMissing: React.FC = () => {
  const [tableName, setTableName] = useState('');
  const [database, setDatabase] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [fieldInfos, setFieldInfos] = useState<FieldNullInfo[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

  const handleAnalyze = async () => {
    if (!tableName.trim()) {
      message.warning('请输入表名');
      return;
    }
    setAnalyzing(true);
    setFieldInfos([]);
    setHasAnalyzed(false);
    try {
      const resp = await analyzeQualityV1({
        table_name: tableName,
        database: database || undefined,
        sample_size: 1000,
      });

      if (resp.success && resp.data) {
        const { issues, total_rows } = resp.data;

        // Extract null-related issues
        const nullIssues = issues.filter((issue) =>
          issue.issue_type.toLowerCase().includes('null') ||
          issue.issue_type.toLowerCase().includes('missing') ||
          issue.issue_type.toLowerCase().includes('empty')
        );

        const fields: FieldNullInfo[] = nullIssues.map((issue) => ({
          column: issue.column,
          nullCount: issue.count,
          nullPercentage: issue.percentage,
          dataType: 'unknown',
          strategy: undefined,
          fixedValue: undefined,
        }));

        setFieldInfos(fields);
        setTotalRows(total_rows || 0);
        setHasAnalyzed(true);

        if (fields.length === 0) {
          message.info('未发现缺失值，数据完整');
        } else {
          message.success(`分析完成，发现 ${fields.length} 个字段存在缺失值`);
        }
      } else {
        message.error(resp.message || '分析失败');
      }
    } catch {
      message.error('分析失败，请检查网络连接');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleStrategyChange = (column: string, strategy: FillStrategy) => {
    setFieldInfos((prev) =>
      prev.map((f) => (f.column === column ? { ...f, strategy } : f))
    );
  };

  const handleFixedValueChange = (column: string, value: string) => {
    setFieldInfos((prev) =>
      prev.map((f) => (f.column === column ? { ...f, fixedValue: value } : f))
    );
  };

  const getAvailableStrategies = (dataType: string) => {
    return strategyOptions.filter((opt) =>
      opt.dataTypes.includes(dataType) || opt.dataTypes.includes('unknown')
    );
  };

  const handleApplyStrategy = () => {
    const configuredFields = fieldInfos.filter((f) => f.strategy);
    if (configuredFields.length === 0) {
      message.warning('请至少配置一个字段的填充策略');
      return;
    }

    // Generate rules from configured strategies
    const rules = configuredFields.map((f) => ({
      field: f.column,
      strategy: f.strategy,
      value: f.strategy === 'fixed' ? f.fixedValue : undefined,
    }));

    message.success(`已生成 ${rules.length} 条填充规则，可导出为 SeaTunnel 配置`);
  };

  const columns = [
    {
      title: '字段名',
      dataIndex: 'column',
      key: 'column',
      width: 200,
    },
    {
      title: '数据类型',
      dataIndex: 'dataType',
      key: 'dataType',
      width: 100,
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '缺失数量',
      dataIndex: 'nullCount',
      key: 'nullCount',
      width: 100,
      render: (count: number) => <Text strong>{count.toLocaleString()}</Text>,
    },
    {
      title: '缺失比例',
      dataIndex: 'nullPercentage',
      key: 'nullPercentage',
      width: 100,
      render: (percentage: number) => {
        const color = percentage > 0.5 ? 'red' : percentage > 0.2 ? 'orange' : 'green';
        return <Tag color={color}>{(percentage * 100).toFixed(1)}%</Tag>;
      },
    },
    {
      title: '填充策略',
      key: 'strategy',
      width: 200,
      render: (_: unknown, record: FieldNullInfo) => {
        const options = getAvailableStrategies(record.dataType);
        return (
          <Select
            placeholder="选择策略"
            value={record.strategy}
            onChange={(v) => handleStrategyChange(record.column, v)}
            options={options}
            style={{ width: '100%' }}
            allowClear
          />
        );
      },
    },
    {
      title: '固定值',
      key: 'fixedValue',
      width: 150,
      render: (_: unknown, record: FieldNullInfo) => {
        if (record.strategy === 'fixed') {
          return (
            <Input
              placeholder="输入固定值"
              value={record.fixedValue}
              onChange={(e) => handleFixedValueChange(record.column, e.target.value)}
              size="small"
            />
          );
        }
        return <Text type="secondary">-</Text>;
      },
    },
  ];

  const totalNullCount = fieldInfos.reduce((sum, f) => sum + f.nullCount, 0);
  const avgNullPercentage = fieldInfos.length > 0
    ? fieldInfos.reduce((sum, f) => sum + f.nullPercentage, 0) / fieldInfos.length
    : 0;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <FieldNumberOutlined /> 缺失值填充
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 表选择区 */}
        <Card size="small" title="1. 选择表并分析">
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
            <Button type="primary" loading={analyzing} onClick={handleAnalyze}>
              分析缺失值
            </Button>
          </Space>
        </Card>

        {analyzing && (
          <Card size="small">
            <Spin tip="正在分析数据质量..." />
          </Card>
        )}

        {hasAnalyzed && fieldInfos.length === 0 && (
          <Alert
            message="数据完整"
            description="表中未发现缺失值，无需进行填充操作。"
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
          />
        )}

        {hasAnalyzed && fieldInfos.length > 0 && (
          <>
            {/* 统计概览 */}
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic title="总行数" value={totalRows} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="含缺失值字段"
                    value={fieldInfos.length}
                    valueStyle={{ color: fieldInfos.length > 0 ? '#fa8c16' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="总缺失单元格"
                    value={totalNullCount}
                    valueStyle={{ color: totalNullCount > 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平均缺失率"
                    value={`${(avgNullPercentage * 100).toFixed(1)}%`}
                    valueStyle={{
                      color: avgNullPercentage > 0.3 ? '#cf1322' : avgNullPercentage > 0.1 ? '#fa8c16' : '#3f8600',
                    }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 策略配置 */}
            <Card
              size="small"
              title="2. 配置填充策略"
              extra={
                <Button type="primary" onClick={handleApplyStrategy}>
                  应用策略
                </Button>
              }
            >
              <Alert
                message="配置说明"
                description="为每个含缺失值的字段选择合适的填充策略。选择'固定值'时需在右侧输入具体值。"
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
              />
              <Table
                columns={columns}
                dataSource={fieldInfos.map((f, i) => ({ ...f, key: i }))}
                pagination={false}
                size="small"
              />
            </Card>

            {/* 预览结果 */}
            <Card size="small" title="3. 预览与导出">
              <Alert
                message="预览模式"
                description="配置完成后点击'应用策略'生成清洗规则，可导出为 SeaTunnel Transform 配置文件。"
                type="info"
                showIcon
              />
            </Card>
          </>
        )}
      </Space>
    </div>
  );
};

export default FillMissing;
