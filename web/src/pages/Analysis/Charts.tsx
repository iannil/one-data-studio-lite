import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Input, Modal } from 'antd';
import { LineChartOutlined, ReloadOutlined, SearchOutlined, PlusOutlined, ExportOutlined } from '@ant-design/icons';
import { getChartsV1, type Chart } from '../../api/superset';
import { API_BASE_URL } from '../../api/client';

const { Title, Text } = Typography;

const Charts: React.FC = () => {
  const [charts, setCharts] = useState<Chart[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [createModalVisible, setCreateModalVisible] = useState(false);

  const fetchCharts = async () => {
    setLoading(true);
    try {
      const resp = await getChartsV1({ page: 1, page_size: 100 });
      setCharts(resp?.data?.result || []);
    } catch {
      message.error('获取图表列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCharts();
  }, []);

  // 获取 Superset URL 用于跳转
  const getSupersetUrl = () => {
    return API_BASE_URL.replace('/api', '').replace('/portal', '') || 'http://localhost:8088';
  };

  const handleOpenSupersetChart = () => {
    // 打开 Superset 原生图表创建页面
    const supersetUrl = getSupersetUrl();
    window.open(`${supersetUrl}/chart/edit`, '_blank');
    setCreateModalVisible(false);
  };

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
      render: (text: string, record: Chart) => text || record.chart_name || '-',
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
      render: (user?: Chart['created_by']) => user?.username || user?.first_name || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'changed_on_delta_humanized',
      key: 'changed_on',
      render: (text: string, record: Chart) => text || record.changed_on || '-',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <LineChartOutlined /> 图表管理
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
            创建图表
          </Button>
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

      <Modal
        title="创建图表"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={handleOpenSupersetChart}
        okText="在 Superset 中创建"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>点击"在 Superset 中创建"将打开 Apache Superset 的原生图表创建页面。</Text>
          <Text type="secondary">
            Superset 提供了强大的可视化编辑器，支持多种图表类型和配置选项。
          </Text>
          <Button
            icon={<ExportOutlined />}
            onClick={handleOpenSupersetChart}
            block
          >
            打开 Superset 图表编辑器
          </Button>
        </Space>
      </Modal>
    </div>
  );
};

export default Charts;
