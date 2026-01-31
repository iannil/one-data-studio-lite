import React, { useEffect, useState } from 'react';
import { Card, Table, Input, Tag, message, Typography, Space, Button, Spin } from 'antd';
import { DatabaseOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { searchEntities } from '../../api/datahub';

const { Title } = Typography;

const DataSources: React.FC = () => {
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');

  const fetchDataSources = async (query?: string) => {
    setLoading(true);
    try {
      const data = await searchEntities({ entity: 'dataPlatform', query: query || '*' });
      setDataSources(data?.entities || data?.results || []);
    } catch {
      message.error('获取数据源列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDataSources();
  }, []);

  const handleSearch = () => {
    fetchDataSources(searchText || undefined);
  };

  const columns = [
    {
      title: '数据源名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => text || record.urn?.split(':').pop() || '-',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (text: string, record: any) => {
        const t = text || record.platform || '-';
        return <Tag color="blue">{t}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const s = status || 'active';
        return <Tag color={s === 'active' ? 'green' : 'default'}>{s === 'active' ? '正常' : s}</Tag>;
      },
    },
    {
      title: 'URN',
      dataIndex: 'urn',
      key: 'urn',
      ellipsis: true,
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <DatabaseOutlined /> 数据源管理
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索数据源..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Button type="primary" onClick={handleSearch}>搜索</Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchDataSources()}>刷新</Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={dataSources.map((d, i) => ({ ...d, key: d.urn || i }))}
            pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default DataSources;
