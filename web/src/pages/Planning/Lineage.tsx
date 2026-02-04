import React, { useState } from 'react';
import { Card, Input, Button, message, Typography, Flex, Space, Spin, Tag, Table } from 'antd';
import { BranchesOutlined, SearchOutlined } from '@ant-design/icons';
import { getLineage } from '../../api/metadata';

const { Title, Text } = Typography;

interface LineageNode {
  urn: string;
  type: string;
  direction: string;
}

interface LineageRelationship {
  entity?: { urn?: string } | string;
  type?: string;
  urn?: string;
}

const Lineage: React.FC = () => {
  const [urn, setUrn] = useState('');
  const [loading, setLoading] = useState(false);
  const [upstreamNodes, setUpstreamNodes] = useState<LineageNode[]>([]);
  const [downstreamNodes, setDownstreamNodes] = useState<LineageNode[]>([]);

  const fetchLineage = async () => {
    if (!urn.trim()) {
      message.warning('请输入数据集 URN');
      return;
    }
    setLoading(true);
    try {
      const [incoming, outgoing] = await Promise.all([
        getLineage(urn, 'INCOMING').catch(() => ({ relationships: [] })),
        getLineage(urn, 'OUTGOING').catch(() => ({ relationships: [] })),
      ]);
      setUpstreamNodes(
        (incoming.relationships || []).map((r: LineageRelationship) => ({
          urn: typeof r.entity === 'string' ? r.entity : (r.entity?.urn || r.urn || '-'),
          type: r.type || '-',
          direction: '上游',
        }))
      );
      setDownstreamNodes(
        (outgoing.relationships || []).map((r: LineageRelationship) => ({
          urn: typeof r.entity === 'string' ? r.entity : (r.entity?.urn || r.urn || '-'),
          type: r.type || '-',
          direction: '下游',
        }))
      );
    } catch {
      message.error('获取血缘关系失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'URN',
      dataIndex: 'urn',
      key: 'urn',
      ellipsis: true,
      render: (text: string) => <Text copyable style={{ fontSize: 12 }}>{text}</Text>,
    },
    {
      title: '关系类型',
      dataIndex: 'type',
      key: 'type',
      width: 150,
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 100,
      render: (text: string) => (
        <Tag color={text === '上游' ? 'blue' : 'green'}>{text}</Tag>
      ),
    },
  ];

  const allNodes = [...upstreamNodes, ...downstreamNodes];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <BranchesOutlined /> 数据血缘
      </Title>
      <Flex vertical style={{ width: '100%' }} gap="middle">
        <Card size="small">
          <Space>
            <Input
              placeholder="请输入数据集 URN，如 urn:li:dataset:(urn:li:dataPlatform:mysql,db.table,PROD)"
              value={urn}
              onChange={(e) => setUrn(e.target.value)}
              onPressEnter={fetchLineage}
              style={{ width: 600 }}
              prefix={<SearchOutlined />}
            />
            <Button type="primary" onClick={fetchLineage} loading={loading}>
              查询血缘
            </Button>
          </Space>
        </Card>

        {loading ? (
          <Spin />
        ) : allNodes.length > 0 ? (
          <>
            <Card title={`上游依赖 (${upstreamNodes.length})`} size="small">
              <Table
                columns={columns}
                dataSource={upstreamNodes.map((n, i) => ({ ...n, key: `up-${i}` }))}
                pagination={false}
                size="small"
                locale={{ emptyText: '无上游依赖' }}
              />
            </Card>
            <Card title={`下游影响 (${downstreamNodes.length})`} size="small">
              <Table
                columns={columns}
                dataSource={downstreamNodes.map((n, i) => ({ ...n, key: `down-${i}` }))}
                pagination={false}
                size="small"
                locale={{ emptyText: '无下游影响' }}
              />
            </Card>
          </>
        ) : urn ? (
          <Card size="small">
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              未找到血缘关系，请确认 URN 格式正确
            </div>
          </Card>
        ) : null}
      </Flex>
    </div>
  );
};

export default Lineage;
