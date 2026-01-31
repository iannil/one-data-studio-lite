import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Input } from 'antd';
import { LineChartOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { getCharts } from '../../api/superset';

const { Title, Text } = Typography;

const Charts: React.FC = () => {
  const [charts, setCharts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');

  const fetchCharts = async () => {
    setLoading(true);
    try {
      const data = await getCharts();
      setCharts(data?.result || data?.charts || []);
    } catch {
      message.error('获取图表列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCharts();
  }, []);

  const filteredCharts = searchText
    ? charts.filter((c) =>
        (c.slice_name || c.chart_name || '').toLowerCase().includes(searchText.toLowerCase())
      )
    : charts;

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    {
      title: '图表名称',
      dataIndex: 'slice_name',
      key: 'slice_name',
      render: (text: string, record: any) => text || record.chart_name || '-',
    },
    {
      title: '图表类型',
      dataIndex: 'viz_type',
      key: 'viz_type',
      render: (text: string) => <Tag color="blue">{text || '-'}</Tag>,
    },
    {
      title: '数据源',
      dataIndex: 'datasource_name_text',
      key: 'datasource',
      render: (text: string) => text || '-',
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
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <LineChartOutlined /> 图表管理
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索图表..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchCharts}>刷新</Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredCharts.map((c, i) => ({ ...c, key: c.id || i }))}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default Charts;
