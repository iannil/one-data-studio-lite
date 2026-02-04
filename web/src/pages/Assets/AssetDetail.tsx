import React, { useEffect, useState } from 'react';
import { Card, Tabs, Table, Tag, Typography, Spin, Descriptions, Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { getAssetDetailV1, getDatasetSchemaV1 } from '../../api/data-api';
import { getLineage } from '../../api/datahub';

const { Title, Text } = Typography;

interface AssetDetail {
  id?: string;
  name: string;
  type?: string;
  platform?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

interface SchemaField {
  name?: string;
  fieldPath?: string;
  type?: string;
  nativeDataType?: string;
  description?: string;
  nullable?: boolean;
}

interface SchemaData {
  fields?: SchemaField[];
  columns?: SchemaField[];
}

interface LineageRelationship {
  entity?: { urn?: string } | string;
  type?: string;
  urn?: string;
}

interface LineageData {
  relationships?: LineageRelationship[];
}

const AssetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [schema, setSchema] = useState<SchemaData | null>(null);
  const [lineage, setLineage] = useState<LineageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const [assetResp, schemaResp] = await Promise.all([
          getAssetDetailV1(id).catch(() => null),
          getDatasetSchemaV1(id).catch(() => null),
        ]);
        setAsset(assetResp?.data ?? null);
        setSchema(schemaResp?.data ?? null);
        // 尝试获取血缘（需要 URN 格式）
        if (id.startsWith('urn:')) {
          const lineageData = await getLineage(id, 'OUTGOING').catch(() => null);
          setLineage(lineageData);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  const schemaColumns = [
    { title: '字段名', dataIndex: 'name', key: 'name', render: (_t: string, r: SchemaField) => r.name || r.fieldPath || '-' },
    { title: '类型', dataIndex: 'type', key: 'type', render: (_t: string, r: SchemaField) => <Tag>{r.type || r.nativeDataType || '-'}</Tag> },
    { title: '描述', dataIndex: 'description', key: 'description', render: (t: string) => t || '-' },
  ];

  const lineageColumns = [
    { title: 'URN', dataIndex: 'urn', key: 'urn', ellipsis: true, render: (t: string) => <Text copyable style={{ fontSize: 12 }}>{t}</Text> },
    { title: '类型', dataIndex: 'type', key: 'type', render: (_t: string, r: LineageRelationship) => <Tag>{r.type || '-'}</Tag> },
  ];

  if (loading) {
    return <Spin size="large" style={{ display: 'block', textAlign: 'center', padding: 100 }} />;
  }

  const tabItems = [
    {
      key: 'info',
      label: '基本信息',
      children: asset ? (
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="名称">{asset.name || '-'}</Descriptions.Item>
          <Descriptions.Item label="类型">{asset.type || '-'}</Descriptions.Item>
          <Descriptions.Item label="平台">{asset.platform || '-'}</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{asset.description || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{asset.created_at ? new Date(asset.created_at).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{asset.updated_at ? new Date(asset.updated_at).toLocaleString() : '-'}</Descriptions.Item>
        </Descriptions>
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>无法获取资产详情</div>
      ),
    },
    {
      key: 'schema',
      label: 'Schema',
      children: schema ? (
        <Table
          columns={schemaColumns}
          dataSource={(schema.fields || schema.columns || []).map((f: SchemaField, i: number) => ({ ...f, key: i }))}
          pagination={false}
          size="small"
        />
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>无 Schema 信息</div>
      ),
    },
    {
      key: 'lineage',
      label: '血缘',
      children: lineage?.relationships?.length ? (
        <Table
          columns={lineageColumns}
          dataSource={lineage?.relationships?.map((r: LineageRelationship, i: number) => ({
            urn: typeof r.entity === 'string' ? r.entity : r.entity?.urn || r.urn || '-',
            type: r.type || '-',
            key: i,
          })) || []}
          pagination={false}
          size="small"
        />
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>无血缘关系</div>
      ),
    },
  ];

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Title level={4} style={{ marginBottom: 16 }}>
        资产详情: {asset?.name || id}
      </Title>
      <Card size="small">
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
};

export default AssetDetail;
