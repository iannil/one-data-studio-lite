import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Typography, Space, Spin, Modal, Form, Input, Select } from 'antd';
import { SwapOutlined, PlusOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { getMappings, updateMapping, triggerSync } from '../../api/metadata-sync';

const { Title } = Typography;

const MetadataSync: React.FC = () => {
  const [mappings, setMappings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchMappings = async () => {
    setLoading(true);
    try {
      const data = await getMappings();
      setMappings(data?.mappings || data || []);
    } catch {
      message.error('获取映射规则失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await triggerSync();
      message.success('同步已触发');
    } catch {
      message.error('触发同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleSaveMapping = async (values: any) => {
    try {
      await updateMapping(values);
      message.success('映射规则已保存');
      setModalVisible(false);
      form.resetFields();
      fetchMappings();
    } catch {
      message.error('保存映射规则失败');
    }
  };

  const columns = [
    { title: '映射名称', dataIndex: 'name', key: 'name' },
    { title: '源平台', dataIndex: 'source_platform', key: 'source_platform', render: (t: string) => <Tag color="blue">{t || '-'}</Tag> },
    { title: '目标平台', dataIndex: 'target_platform', key: 'target_platform', render: (t: string) => <Tag color="green">{t || '-'}</Tag> },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = { active: 'success', inactive: 'default', error: 'error' };
        return <Tag color={colors[status] || 'default'}>{status || '-'}</Tag>;
      },
    },
    { title: '上次同步', dataIndex: 'last_sync', key: 'last_sync', render: (t: string) => t ? new Date(t).toLocaleString() : '-' },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true, render: (t: string) => t || '-' },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SwapOutlined /> 元数据同步
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            添加映射
          </Button>
          <Button icon={<SyncOutlined />} loading={syncing} onClick={handleSync}>
            手动同步
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchMappings}>刷新</Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={(Array.isArray(mappings) ? mappings : []).map((m, i) => ({ ...m, key: m.id || i }))}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>

      <Modal
        title="添加映射规则"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleSaveMapping}>
          <Form.Item name="name" label="映射名称" rules={[{ required: true, message: '请输入映射名称' }]}>
            <Input placeholder="如：MySQL 到 DataHub" />
          </Form.Item>
          <Form.Item name="source_platform" label="源平台" rules={[{ required: true }]}>
            <Select placeholder="选择源平台">
              <Select.Option value="mysql">MySQL</Select.Option>
              <Select.Option value="postgresql">PostgreSQL</Select.Option>
              <Select.Option value="hive">Hive</Select.Option>
              <Select.Option value="kafka">Kafka</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="target_platform" label="目标平台" rules={[{ required: true }]}>
            <Select placeholder="选择目标平台">
              <Select.Option value="datahub">DataHub</Select.Option>
              <Select.Option value="superset">Superset</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="映射规则描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MetadataSync;
