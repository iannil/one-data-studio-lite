import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Modal, Input } from 'antd';
import { SyncOutlined, ReloadOutlined, PlusOutlined, StopOutlined } from '@ant-design/icons';
import { getJobs, cancelJob } from '../../api/seatunnel';

const { Title, Text } = Typography;
const { TextArea } = Input;

const statusColors: Record<string, string> = {
  RUNNING: 'processing',
  FINISHED: 'success',
  FAILED: 'error',
  CANCELED: 'default',
  CREATED: 'warning',
};

const SyncJobs: React.FC = () => {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitModalVisible, setSubmitModalVisible] = useState(false);
  const [configText, setConfigText] = useState('');

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await getJobs();
      setJobs(Array.isArray(data) ? data : data?.jobs || []);
    } catch {
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleCancel = async (jobId: string) => {
    try {
      await cancelJob(jobId);
      message.success('任务已取消');
      fetchJobs();
    } catch {
      message.error('取消任务失败');
    }
  };

  const columns = [
    {
      title: '任务 ID',
      dataIndex: 'jobId',
      key: 'jobId',
      ellipsis: true,
      render: (text: string) => <Text copyable style={{ fontSize: 12 }}>{text || '-'}</Text>,
    },
    {
      title: '任务名称',
      dataIndex: 'jobName',
      key: 'jobName',
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'jobStatus',
      key: 'jobStatus',
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>{status || '-'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      render: (text: string) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '完成时间',
      dataIndex: 'finishTime',
      key: 'finishTime',
      render: (text: string) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Space>
          {record.jobStatus === 'RUNNING' && (
            <Button
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleCancel(record.jobId)}
            >
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SyncOutlined /> 数据同步任务
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setSubmitModalVisible(true)}>
            提交任务
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchJobs}>刷新</Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={jobs.map((j, i) => ({ ...j, key: j.jobId || i }))}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>

      <Modal
        title="提交 SeaTunnel 任务"
        open={submitModalVisible}
        onCancel={() => setSubmitModalVisible(false)}
        onOk={async () => {
          try {
            const config = JSON.parse(configText);
            const { submitJob: submit } = await import('../../api/seatunnel');
            await submit(config);
            message.success('任务已提交');
            setSubmitModalVisible(false);
            setConfigText('');
            fetchJobs();
          } catch {
            message.error('提交失败，请检查 JSON 格式');
          }
        }}
        width={700}
      >
        <TextArea
          rows={15}
          value={configText}
          onChange={(e) => setConfigText(e.target.value)}
          placeholder='请输入 SeaTunnel 任务配置 JSON...'
          style={{ fontFamily: 'monospace' }}
        />
      </Modal>
    </div>
  );
};

export default SyncJobs;
