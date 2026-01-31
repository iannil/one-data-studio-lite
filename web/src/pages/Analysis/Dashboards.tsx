import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Input } from 'antd';
import { DashboardOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { getDashboards } from '../../api/superset';

const { Title, Text } = Typography;

const Dashboards: React.FC = () => {
  const [dashboards, setDashboards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');

  const fetchDashboards = async () => {
    setLoading(true);
    try {
      const data = await getDashboards();
      setDashboards(data?.result || data?.dashboards || []);
    } catch {
      message.error('获取仪表板列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboards();
  }, []);

  const filteredDashboards = searchText
    ? dashboards.filter((d) =>
        (d.dashboard_title || d.title || '').toLowerCase().includes(searchText.toLowerCase())
      )
    : dashboards;

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '仪表板名称',
      dataIndex: 'dashboard_title',
      key: 'dashboard_title',
      render: (text: string, record: any) => text || record.title || '-',
    },
    {
      title: '状态',
      dataIndex: 'published',
      key: 'published',
      render: (published: boolean) => (
        <Tag color={published ? 'green' : 'default'}>{published ? '已发布' : '草稿'}</Tag>
      ),
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      render: (user: any) => user?.username || user?.first_name || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'changed_on_delta_humanized',
      key: 'changed_on',
      render: (text: string, record: any) => text || record.changed_on || '-',
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      render: (url: string) => url ? <Text copyable style={{ fontSize: 12 }}>{url}</Text> : '-',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <DashboardOutlined /> BI 仪表板
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索仪表板..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchDashboards}>刷新</Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredDashboards.map((d, i) => ({ ...d, key: d.id || i }))}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default Dashboards;
