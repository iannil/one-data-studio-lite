import React, { useState } from 'react';
import { Card, Input, Button, Table, Tabs, message, Typography, Space, Spin, Tag } from 'antd';
import { ApiOutlined, SearchOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { getDatasetSchemaV1, queryDatasetV1, subscribeDatasetV1 } from '../../api/data-api';

const { Title, Text } = Typography;
const { TextArea } = Input;

const DataApiManage: React.FC = () => {
  const [datasetId, setDatasetId] = useState('');
  const [schema, setSchema] = useState<any>(null);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [sql, setSql] = useState('');
  const [queryResult, setQueryResult] = useState<any>(null);
  const [querying, setQuerying] = useState(false);

  const fetchSchema = async () => {
    if (!datasetId.trim()) {
      message.warning('请输入数据集 ID');
      return;
    }
    setLoadingSchema(true);
    try {
      const resp = await getDatasetSchemaV1(datasetId);
      setSchema(resp?.data);
    } catch {
      message.error('获取 Schema 失败');
    } finally {
      setLoadingSchema(false);
    }
  };

  const handleQuery = async () => {
    if (!datasetId.trim()) {
      message.warning('请先输入数据集 ID');
      return;
    }
    setQuerying(true);
    try {
      const resp = await queryDatasetV1(datasetId, { sql: sql || undefined, limit: 100 });
      setQueryResult(resp?.data);
    } catch {
      message.error('查询失败');
    } finally {
      setQuerying(false);
    }
  };

  const handleSubscribe = async () => {
    if (!datasetId.trim()) {
      message.warning('请先输入数据集 ID');
      return;
    }
    try {
      await subscribeDatasetV1(datasetId);
      message.success('订阅成功');
    } catch {
      message.error('订阅失败');
    }
  };

  const schemaColumns = [
    { title: '字段名', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'type', key: 'type', render: (t: string) => <Tag>{t || '-'}</Tag> },
    { title: '描述', dataIndex: 'description', key: 'description', render: (t: string) => t || '-' },
    { title: '可为空', dataIndex: 'nullable', key: 'nullable', render: (v: boolean) => v ? '是' : '否' },
  ];

  const resultColumns = queryResult?.columns?.map((col: string) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
  })) || [];

  const resultData = queryResult?.rows?.map((row: any, i: number) => {
    if (Array.isArray(row)) {
      const record: Record<string, any> = { key: i };
      queryResult.columns.forEach((col: string, idx: number) => {
        record[col] = row[idx];
      });
      return record;
    }
    return { ...row, key: i };
  }) || [];

  const tabItems = [
    {
      key: 'schema',
      label: 'Schema',
      children: (
        <>
          {loadingSchema ? (
            <Spin />
          ) : schema ? (
            <Table
              columns={schemaColumns}
              dataSource={(schema.fields || schema.columns || []).map((f: any, i: number) => ({ ...f, key: i }))}
              pagination={false}
              size="small"
            />
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>请先获取数据集 Schema</div>
          )}
        </>
      ),
    },
    {
      key: 'query',
      label: '查询测试',
      children: (
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
          <TextArea
            placeholder="输入 SQL 查询语句..."
            rows={4}
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            style={{ fontFamily: 'monospace' }}
          />
          <Button type="primary" icon={<PlayCircleOutlined />} loading={querying} onClick={handleQuery}>
            执行查询
          </Button>
          {queryResult && (
            <Table
              columns={resultColumns}
              dataSource={resultData}
              scroll={{ x: 'max-content' }}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <ApiOutlined /> 数据 API 管理
      </Title>
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <Card size="small">
          <Space>
            <Input
              placeholder="数据集 ID"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              style={{ width: 300 }}
              prefix={<SearchOutlined />}
            />
            <Button type="primary" onClick={fetchSchema}>获取 Schema</Button>
            <Button onClick={handleSubscribe}>订阅</Button>
          </Space>
        </Card>
        <Card size="small">
          <Tabs items={tabItems} />
        </Card>
      </Space>
    </div>
  );
};

export default DataApiManage;
