import React, { useEffect, useState } from 'react';
import { Card, Table, Tree, Input, message, Typography, Row, Col, Spin, Descriptions, Tag } from 'antd';
import { NodeIndexOutlined, SearchOutlined } from '@ant-design/icons';
import { searchEntities, getEntityAspect } from '../../api/metadata';

const { Title, Text } = Typography;

const MetadataBrowser: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [selectedUrn, setSelectedUrn] = useState<string | null>(null);
  const [schema, setSchema] = useState<any>(null);
  const [loadingSchema, setLoadingSchema] = useState(false);

  const fetchDatasets = async (query?: string) => {
    setLoading(true);
    try {
      const data = await searchEntities({ entity: 'dataset', query: query || '*', count: 50 });
      setDatasets(data?.entities || data?.results || []);
    } catch {
      message.error('获取数据集列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleSelectDataset = async (urn: string) => {
    setSelectedUrn(urn);
    setLoadingSchema(true);
    try {
      const data = await getEntityAspect(urn, 'schemaMetadata');
      setSchema(data);
    } catch {
      setSchema(null);
    } finally {
      setLoadingSchema(false);
    }
  };

  // 构建树形数据：按 platform 分组
  const treeData = (() => {
    const groups: Record<string, any[]> = {};
    datasets.forEach((ds) => {
      const platform = ds.platform || 'unknown';
      if (!groups[platform]) groups[platform] = [];
      groups[platform].push(ds);
    });
    return Object.entries(groups).map(([platform, items]) => ({
      title: platform,
      key: platform,
      children: items.map((ds) => ({
        title: ds.name || ds.urn?.split(',').pop()?.replace(')', '') || ds.urn,
        key: ds.urn || ds.name,
        isLeaf: true,
      })),
    }));
  })();

  const schemaColumns = [
    { title: '字段名', dataIndex: 'fieldPath', key: 'fieldPath' },
    { title: '类型', dataIndex: 'nativeDataType', key: 'nativeDataType', render: (t: string) => <Tag>{t || '-'}</Tag> },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true, render: (t: string) => t || '-' },
    { title: '可为空', dataIndex: 'nullable', key: 'nullable', render: (v: boolean) => v ? '是' : '否' },
  ];

  const schemaFields = schema?.fields || schema?.schemaMetadata?.fields || [];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <NodeIndexOutlined /> 元数据管理
      </Title>
      <Row gutter={16}>
        <Col xs={24} md={8}>
          <Card
            title="数据集"
            size="small"
            style={{ height: 'calc(100vh - 200px)', overflow: 'auto' }}
            extra={
              <Input
                placeholder="搜索"
                size="small"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onPressEnter={() => fetchDatasets(searchText || undefined)}
                prefix={<SearchOutlined />}
                style={{ width: 150 }}
              />
            }
          >
            {loading ? (
              <Spin />
            ) : (
              <Tree
                treeData={treeData}
                showLine
                onSelect={(keys) => {
                  const key = keys[0] as string;
                  if (key && key.startsWith('urn:')) {
                    handleSelectDataset(key);
                  }
                }}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} md={16}>
          {selectedUrn ? (
            <Card title="Schema 信息" size="small">
              <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="URN">
                  <Text copyable style={{ fontSize: 12 }}>{selectedUrn}</Text>
                </Descriptions.Item>
              </Descriptions>
              {loadingSchema ? (
                <Spin />
              ) : (
                <Table
                  columns={schemaColumns}
                  dataSource={schemaFields.map((f: any, i: number) => ({ ...f, key: i }))}
                  pagination={false}
                  size="small"
                />
              )}
            </Card>
          ) : (
            <Card size="small">
              <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                请从左侧选择一个数据集查看 Schema
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default MetadataBrowser;
