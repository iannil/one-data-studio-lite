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
} from 'antd';
import {
  TableOutlined,
  KeyOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { metadataApi, sourcesApi } from '@/services/api';
import type { MetadataTable, MetadataColumn, DataSource } from '@/types';

const { Title, Text } = Typography;

export default function MetadataPage() {
  const [tables, setTables] = useState<MetadataTable[]>([]);
  const [sources, setSources] = useState<DataSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | undefined>();
  const [selectedTable, setSelectedTable] = useState<MetadataTable | null>(null);
  const [loading, setLoading] = useState(false);

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
    try {
      const response = await metadataApi.getTable(table.id);
      setSelectedTable(response.data);
    } catch (error) {
      message.error('获取表详情失败');
    }
  };

  const getSourceName = (sourceId: string) => {
    const source = sources.find(s => s.id === sourceId);
    return source?.name || sourceId;
  };

  const tableColumns: ColumnsType<MetadataTable> = [
    {
      title: '表名',
      dataIndex: 'table_name',
      key: 'table_name',
      render: (name, record) => (
        <Space>
          <TableOutlined />
          <a onClick={() => handleTableClick(record)}>{name}</a>
        </Space>
      ),
    },
    {
      title: 'Schema',
      dataIndex: 'schema_name',
      key: 'schema_name',
      render: (schema) => schema || 'public',
    },
    {
      title: '数据源',
      dataIndex: 'source_id',
      key: 'source_id',
      render: (sourceId) => (
        <Tag icon={<DatabaseOutlined />} color="blue">
          {getSourceName(sourceId)}
        </Tag>
      ),
    },
    {
      title: '行数',
      dataIndex: 'row_count',
      key: 'row_count',
      render: (count) => count?.toLocaleString() || '-',
    },
    {
      title: '列数',
      dataIndex: 'columns',
      key: 'column_count',
      render: (columns) => columns?.length || 0,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) =>
        tags?.map(tag => <Tag key={tag}>{tag}</Tag>) || '-',
    },
  ];

  const columnColumns: ColumnsType<MetadataColumn> = [
    {
      title: '序号',
      dataIndex: 'ordinal_position',
      key: 'ordinal_position',
      width: 60,
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
      title: '数据类型',
      dataIndex: 'data_type',
      key: 'data_type',
      render: (type) => <Tag color="purple">{type}</Tag>,
    },
    {
      title: '可空',
      dataIndex: 'nullable',
      key: 'nullable',
      width: 80,
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
      width: 80,
      render: (isPK) => isPK ? <Tag color="gold">PK</Tag> : '-',
    },
    {
      title: '默认值',
      dataIndex: 'default_value',
      key: 'default_value',
      render: (value) => value || '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc) => desc || '-',
    },
  ];

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card
          title={<Title level={4}>元数据浏览</Title>}
          extra={
            <Select
              allowClear
              placeholder="筛选数据源"
              style={{ width: 200 }}
              value={selectedSourceId}
              onChange={handleSourceChange}
              options={sources.map(s => ({ value: s.id, label: s.name }))}
            />
          }
        >
          <Spin spinning={loading}>
            {tables.length > 0 ? (
              <Table
                columns={tableColumns}
                dataSource={tables}
                rowKey="id"
                pagination={{ pageSize: 10 }}
                onRow={(record) => ({
                  onClick: () => handleTableClick(record),
                  style: { cursor: 'pointer' },
                })}
              />
            ) : (
              <Empty description="暂无元数据，请先扫描数据源" />
            )}
          </Spin>
        </Card>

        {selectedTable && (
          <Card
            title={
              <Space>
                <TableOutlined />
                <span>表详情: {selectedTable.table_name}</span>
              </Space>
            }
          >
            <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="表名">
                {selectedTable.table_name}
              </Descriptions.Item>
              <Descriptions.Item label="Schema">
                {selectedTable.schema_name || 'public'}
              </Descriptions.Item>
              <Descriptions.Item label="数据源">
                {getSourceName(selectedTable.source_id)}
              </Descriptions.Item>
              <Descriptions.Item label="行数">
                {selectedTable.row_count?.toLocaleString() || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedTable.description || selectedTable.ai_description || '-'}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>列信息</Title>
            <Table
              columns={columnColumns}
              dataSource={selectedTable.columns}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        )}
      </Space>
    </AuthGuard>
  );
}
