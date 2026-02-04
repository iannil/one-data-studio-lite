import React, { useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Alert } from 'antd';
import { BranchesOutlined, ReloadOutlined } from '@ant-design/icons';
import { getProjects } from '../../api/dolphinscheduler';

const { Title } = Typography;

const EtlFlows: React.FC = () => {
  const [flows, setFlows] = useState<DolphinSchedulerProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  interface DolphinSchedulerProject {
    code?: number | string;
    id?: number | string;
    name?: string;
    description?: string;
    releaseState?: string;
    createTime?: string;
    updateTime?: string;
  }

  const fetchFlows = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProjects();
      // Hop 流程暂时从 DS 流程列表读取，后续对接 Hop REST API
      const list = data?.data?.totalList || data?.data || [];
      setFlows(Array.isArray(list) ? list : []);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError('认证失败，请重新登录');
      } else if (status === 503 || status === 502) {
        setError('DolphinScheduler 服务不可用，请确认服务已启动');
      } else {
        setError('获取 ETL 流程列表失败');
      }
      message.error('获取 ETL 流程列表失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchFlows();
  }, []);

  const columns = [
    {
      title: '流程名称',
      dataIndex: 'name',
      key: 'name',
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
      title: '状态',
      dataIndex: 'releaseState',
      key: 'releaseState',
      render: (state: string) => (
        <Tag color={state === 'ONLINE' ? 'green' : 'default'}>
          {state === 'ONLINE' ? '已上线' : '未上线'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updateTime',
      key: 'updateTime',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <BranchesOutlined /> ETL 流程管理
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ReloadOutlined />} onClick={fetchFlows}>刷新</Button>
        </Space>
        {error && (
          <Alert
            message={error}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={flows.map((f, i) => ({ ...f, key: f.code || f.id || i }))}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default EtlFlows;
