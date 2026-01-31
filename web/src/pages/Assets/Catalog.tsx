import React, { useEffect, useState } from 'react';
import { Card, Table, Input, Select, Tag, message, Typography, Space, Button, Spin } from 'antd';
import { BookOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { searchAssetsV1 } from '../../api/data-api';

const { Title } = Typography;

const Catalog: React.FC = () => {
  const navigate = useNavigate();
  const [assets, setAssets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const resp = await searchAssetsV1({
        keyword: keyword || undefined,
        type: typeFilter,
      });
      setAssets(resp?.data || []);
    } catch {
      message.error('搜索数据资产失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  const columns = [
    {
      title: '资产名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <a onClick={() => navigate(`/assets/detail/${record.id || record.urn || ''}`)}>{text || '-'}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (text: string) => <Tag color="blue">{text || '-'}</Tag>,
    },
    {
      title: '所属平台',
      dataIndex: 'platform',
      key: 'platform',
      render: (text: string) => text || '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => tags?.map((t) => <Tag key={t}>{t}</Tag>) || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <BookOutlined /> 资产目录
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索数据资产..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={fetchAssets}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="资产类型"
            allowClear
            style={{ width: 150 }}
            value={typeFilter}
            onChange={setTypeFilter}
          >
            <Select.Option value="table">表</Select.Option>
            <Select.Option value="view">视图</Select.Option>
            <Select.Option value="api">API</Select.Option>
            <Select.Option value="file">文件</Select.Option>
          </Select>
          <Button type="primary" onClick={fetchAssets}>搜索</Button>
          <Button icon={<ReloadOutlined />} onClick={() => { setKeyword(''); setTypeFilter(undefined); fetchAssets(); }}>
            重置
          </Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={(Array.isArray(assets) ? assets : []).map((a, i) => ({ ...a, key: a.id || a.urn || i }))}
            pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default Catalog;
