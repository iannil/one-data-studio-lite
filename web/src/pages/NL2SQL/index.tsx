import React, { useEffect, useState } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tree,
  Spin,
  message,
  Typography,
  Space,
  Divider,
  Alert,
  Row,
  Col,
} from 'antd';
import {
  SearchOutlined,
  TableOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { query, getTables } from '../../api/nl2sql';
import { TableInfo, NL2SQLQueryResponse } from '../../types';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

const NL2SQL: React.FC = () => {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [loadingTables, setLoadingTables] = useState(true);
  const [question, setQuestion] = useState('');
  const [querying, setQuerying] = useState(false);
  const [result, setResult] = useState<NL2SQLQueryResponse | null>(null);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const data = await getTables();
        setTables(data);
      } catch (error) {
        message.error('获取表列表失败');
      } finally {
        setLoadingTables(false);
      }
    };
    fetchTables();
  }, []);

  const handleQuery = async () => {
    if (!question.trim()) {
      message.warning('请输入查询问题');
      return;
    }
    setQuerying(true);
    setResult(null);
    try {
      const data = await query({ question, max_rows: 100 });
      setResult(data);
      if (!data.success) {
        message.error('查询失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '查询失败');
    } finally {
      setQuerying(false);
    }
  };

  // 构建表树形数据
  const treeData = tables.map((table) => ({
    title: (
      <span>
        <TableOutlined style={{ marginRight: 4 }} />
        {table.table_name}
        {table.comment && <Text type="secondary"> ({table.comment})</Text>}
      </span>
    ),
    key: `${table.database}.${table.table_name}`,
    children: table.columns.map((col) => ({
      title: (
        <span>
          {col.name}
          <Text type="secondary"> ({col.data_type})</Text>
          {col.comment && <Text type="secondary"> - {col.comment}</Text>}
        </span>
      ),
      key: `${table.database}.${table.table_name}.${col.name}`,
      isLeaf: true,
    })),
  }));

  // 结果表格列
  const columns = result?.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
  })) || [];

  // 结果数据
  const dataSource = result?.rows.map((row, index) => {
    const record: Record<string, any> = { key: index };
    result.columns.forEach((col, colIndex) => {
      record[col] = row[colIndex];
    });
    return record;
  }) || [];

  return (
    <Row gutter={16} style={{ height: '100%' }}>
      {/* 左侧：表列表 */}
      <Col xs={24} md={6}>
        <Card
          title={
            <span>
              <DatabaseOutlined /> 数据表
            </span>
          }
          size="small"
          style={{ height: 'calc(100vh - 180px)', overflow: 'auto' }}
        >
          {loadingTables ? (
            <Spin />
          ) : (
            <Tree
              treeData={treeData}
              defaultExpandAll={false}
              showLine
            />
          )}
        </Card>
      </Col>

      {/* 右侧：查询区域 */}
      <Col xs={24} md={18}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 查询输入 */}
          <Card size="small">
            <Title level={5}>自然语言查询</Title>
            <TextArea
              placeholder="请用自然语言描述您想查询的数据，例如：查询销售额最高的前10个产品"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onPressEnter={(e) => {
                if (e.ctrlKey) handleQuery();
              }}
            />
            <div style={{ marginTop: 12, textAlign: 'right' }}>
              <Text type="secondary" style={{ marginRight: 16 }}>
                Ctrl + Enter 快速查询
              </Text>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                loading={querying}
                onClick={handleQuery}
              >
                查询
              </Button>
            </div>
          </Card>

          {/* 生成的 SQL */}
          {result && (
            <Card size="small" title="生成的 SQL">
              <pre style={{
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                overflow: 'auto',
                margin: 0,
              }}>
                {result.generated_sql}
              </pre>
              {result.explanation && (
                <>
                  <Divider style={{ margin: '12px 0' }} />
                  <Paragraph type="secondary">
                    <strong>解释：</strong>{result.explanation}
                  </Paragraph>
                </>
              )}
            </Card>
          )}

          {/* 查询结果 */}
          {result && (
            <Card
              size="small"
              title={`查询结果 (${result.row_count} 行, 耗时 ${result.execution_time_ms?.toFixed(0) || '-'} ms)`}
            >
              {result.success ? (
                <Table
                  columns={columns}
                  dataSource={dataSource}
                  scroll={{ x: 'max-content' }}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条`,
                  }}
                  size="small"
                />
              ) : (
                <Alert type="error" message="查询执行失败" />
              )}
            </Card>
          )}
        </Space>
      </Col>
    </Row>
  );
};

export default NL2SQL;
