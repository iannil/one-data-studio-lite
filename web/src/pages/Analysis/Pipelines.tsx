import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Popconfirm } from 'antd';
import { RobotOutlined, ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { getPipelines, runPipeline } from '../../api/cubestudio';

const { Title } = Typography;

const Pipelines: React.FC = () => {
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPipelines = async () => {
    setLoading(true);
    try {
      const data = await getPipelines();
      setPipelines(data?.result || data?.pipelines || data || []);
    } catch {
      message.error('获取 Pipeline 列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  const handleRun = async (id: number) => {
    try {
      await runPipeline(id);
      message.success('Pipeline 已启动');
      fetchPipelines();
    } catch {
      message.error('启动 Pipeline 失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'describe', key: 'describe', ellipsis: true, render: (t: string) => t || '-' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = { running: 'processing', success: 'success', failed: 'error', pending: 'warning' };
        return <Tag color={colors[status] || 'default'}>{status || '-'}</Tag>;
      },
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      render: (user: any) => (typeof user === 'string' ? user : user?.username) || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'changed_on',
      key: 'changed_on',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Popconfirm title="确认运行此 Pipeline？" onConfirm={() => handleRun(record.id)}>
          <Button type="link" size="small" icon={<PlayCircleOutlined />}>
            运行
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <RobotOutlined /> AI Pipeline
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ReloadOutlined />} onClick={fetchPipelines}>刷新</Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={Array.isArray(pipelines) ? pipelines.map((p, i) => ({ ...p, key: p.id || i })) : []}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default Pipelines;
