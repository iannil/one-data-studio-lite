'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Tag,
  Space,
  Typography,
  Select,
  Descriptions,
  Empty,
  Spin,
  message,
  Row,
  Col,
  Input,
  Tooltip,
  Badge,
} from 'antd';
import {
  TableOutlined,
  KeyOutlined,
  DatabaseOutlined,
  SearchOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { metadataApi, sourcesApi } from '@/services/api';
import type { MetadataTable, MetadataColumn, DataSource } from '@/types';

const { Title, Text } = Typography;
const { Search } = Input;

export default function MetadataPage() {
  const [tables, setTables] = useState<MetadataTable[]>([]);
  const [sources, setSources] = useState<DataSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | undefined>();
  const [selectedTable, setSelectedTable] = useState<MetadataTable | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');

  const fetchSources = async () => {
    try {
      const response = await sourcesApi.list();
      setSources(response.data);
    } catch (error) {
      message.error('获取数据源列表失败');
    }
  };

  const fetchTables = async (sourceId?: string) => {
    setLoading(true);
    try {
      const response = await metadataApi.listTables(sourceId);
      setTables(response.data);
      setSelectedTable(null);
    } catch (error) {
      message.error('获取元数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
    fetchTables();
  }, []);

  const handleSourceChange = (value: string | undefined) => {
    setSelectedSourceId(value);
    fetchTables(value);
  };

  const handleTableClick = async (table: MetadataTable) => {
    setDetailLoading(true);
    try {
      const response = await metadataApi.getTable(table.id);
      setSelectedTable(response.data);
    } catch (error) {
      message.error('获取表详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const getSourceName = (sourceId: string) => {
    const source = sources.find(s => s.id === sourceId);
    return source?.name || sourceId;
  };

  const filteredTables = tables.filter(table => {
    if (!searchKeyword.trim()) return true;
    const keyword = searchKeyword.toLowerCase();
    return (
      table.table_name.toLowerCase().includes(keyword) ||
      table.schema_name?.toLowerCase().includes(keyword) ||
      table.description?.toLowerCase().includes(keyword)
    );
  });

  const tableColumns: ColumnsType<MetadataTable> = [
    {
      title: '表名',
      dataIndex: 'table_name',
      key: 'table_name',
      render: (name, record) => (
        <Space>
          <TableOutlined />
          <Tooltip title={record.description || record.ai_description}>
            <a onClick={() => handleTableClick(record)}>{name}</a>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Schema',
      dataIndex: 'schema_name',
      key: 'schema_name',
      width: 100,
      render: (schema) => <Text type="secondary">{schema || 'public'}</Text>,
    },
    {
      title: '数据源',
      dataIndex: 'source_id',
      key: 'source_id',
      width: 140,
      render: (sourceId) => (
        <Tag icon={<DatabaseOutlined />} color="blue">
          {getSourceName(sourceId)}
        </Tag>
      ),
    },
    {
      title: '列数',
      dataIndex: 'columns',
      key: 'column_count',
      width: 70,
      render: (columns) => (
        <Badge count={columns?.length || 0} showZero color="#8c8c8c" />
      ),
    },
  ];

  const columnColumns: ColumnsType<MetadataColumn> = [
    {
      title: '#',
      dataIndex: 'ordinal_position',
      key: 'ordinal_position',
      width: 45,
      render: (pos) => <Text type="secondary">{pos}</Text>,
    },
    {
      title: '列名',
      dataIndex: 'column_name',
      key: 'column_name',
      render: (name, record) => (
        <Space>
          {record.is_primary_key && <KeyOutlined style={{ color: '#faad14' }} />}
          <Text strong={record.is_primary_key}>{name}</Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 120,
      render: (type) => <Tag color="purple">{type}</Tag>,
    },
    {
      title: '可空',
      dataIndex: 'nullable',
      key: 'nullable',
      width: 60,
      render: (nullable) => (
        <Tag color={nullable ? 'default' : 'red'}>
          {nullable ? 'YES' : 'NO'}
        </Tag>
      ),
    },
    {
      title: '主键',
      dataIndex: 'is_primary_key',
      key: 'is_primary_key',
      width: 60,
      render: (isPK) => isPK ? <Tag color="gold">PK</Tag> : '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc, record) => (
        <Tooltip title={desc || record.ai_inferred_meaning}>
          <Text type="secondary">{desc || record.ai_inferred_meaning || '-'}</Text>
        </Tooltip>
      ),
    },
  ];

  return (
    <AuthGuard>
      <Row gutter={16} style={{ height: 'calc(100vh - 120px)' }}>
        {/* 左侧: 表列表 */}
        <Col span={selectedTable ? 10 : 24} style={{ height: '100%' }}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>元数据浏览</span>
                <Badge count={filteredTables.length} showZero color="#1890ff" />
              </Space>
            }
            extra={
              <Select
                allowClear
                placeholder="筛选数据源"
                style={{ width: 160 }}
                value={selectedSourceId}
                onChange={handleSourceChange}
                options={sources.map(s => ({ value: s.id, label: s.name }))}
              />
            }
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
          >
            <Search
              placeholder="搜索表名..."
              prefix={<SearchOutlined />}
              allowClear
              value={searchKeyword}
              onChange={e => setSearchKeyword(e.target.value)}
              style={{ marginBottom: 12 }}
            />

            <Spin spinning={loading} style={{ flex: 1 }}>
              {filteredTables.length > 0 ? (
                <div style={{ flex: 1, overflow: 'auto' }}>
                  <Table
                    columns={tableColumns}
                    dataSource={filteredTables}
                    rowKey="id"
                    size="small"
                    pagination={{ pageSize: 15, size: 'small', showSizeChanger: false }}
                    onRow={(record) => ({
                      onClick: () => handleTableClick(record),
                      style: {
                        cursor: 'pointer',
                        background: selectedTable?.id === record.id ? '#e6f7ff' : undefined,
                      },
                    })}
                  />
                </div>
              ) : (
                <Empty description="暂无元数据，请先扫描数据源" />
              )}
            </Spin>
          </Card>
        </Col>

        {/* 右侧: 表详情 */}
        {selectedTable && (
          <Col span={14} style={{ height: '100%' }}>
            <Card
              title={
                <Space>
                  <TableOutlined />
                  <span>{selectedTable.table_name}</span>
                  <Tag color="blue">{selectedTable.schema_name || 'public'}</Tag>
                </Space>
              }
              extra={
                <Text type="secondary">
                  {getSourceName(selectedTable.source_id)}
                </Text>
              }
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
              bodyStyle={{ flex: 1, overflow: 'auto' }}
            >
              <Spin spinning={detailLoading}>
                <Descriptions
                  bordered
                  size="small"
                  column={2}
                  style={{ marginBottom: 16 }}
                >
                  <Descriptions.Item label="表名">
                    {selectedTable.table_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="Schema">
                    {selectedTable.schema_name || 'public'}
                  </Descriptions.Item>
                  <Descriptions.Item label="数据源">
                    <Tag icon={<DatabaseOutlined />} color="blue">
                      {getSourceName(selectedTable.source_id)}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="行数">
                    {selectedTable.row_count?.toLocaleString() || '-'}
                  </Descriptions.Item>
                  {(selectedTable.description || selectedTable.ai_description) && (
                    <Descriptions.Item label="描述" span={2}>
                      {selectedTable.description || selectedTable.ai_description}
                    </Descriptions.Item>
                  )}
                </Descriptions>

                <div style={{ marginBottom: 12 }}>
                  <Space>
                    <Title level={5} style={{ margin: 0 }}>列信息</Title>
                    <Badge
                      count={selectedTable.columns?.length || 0}
                      showZero
                      color="#722ed1"
                    />
                  </Space>
                </div>

                <Table
                  columns={columnColumns}
                  dataSource={selectedTable.columns}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  scroll={{ y: 'calc(100vh - 400px)' }}
                />
              </Spin>
            </Card>
          </Col>
        )}

        {/* 右侧: 空状态提示 */}
        {!selectedTable && (
          <Col span={0}>
            {/* Hidden when no table selected - left side expands to full width */}
          </Col>
        )}
      </Row>
    </AuthGuard>
  );
}
