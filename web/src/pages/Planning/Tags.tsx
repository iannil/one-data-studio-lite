import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Input, Modal, Form, message, Typography, Space, Tag, Spin } from 'antd';
import { TagsOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { searchTags, createTag } from '../../api/metadata';

const { Title } = Typography;

const Tags: React.FC = () => {
  const [tags, setTags] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchTags = async (query?: string) => {
    setLoading(true);
    try {
      const data = await searchTags(query);
      setTags(data?.entities || data?.results || []);
    } catch {
      message.error('获取标签列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTags();
  }, []);

  const handleCreate = async (values: { name: string; description?: string }) => {
    try {
      await createTag(values.name, values.description);
      message.success('标签创建成功');
      setModalVisible(false);
      form.resetFields();
      fetchTags();
    } catch {
      message.error('创建标签失败');
    }
  };

  const columns = [
    {
      title: '标签名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <Tag color="blue">{text || record.urn?.split(':').pop() || '-'}</Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
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
        <TagsOutlined /> 数据标签管理
      </Title>
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索标签..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={() => fetchTags(searchText || undefined)}
            style={{ width: 250 }}
            prefix={<SearchOutlined />}
          />
          <Button type="primary" onClick={() => fetchTags(searchText || undefined)}>搜索</Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchTags()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            创建标签
          </Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={tags.map((t, i) => ({ ...t, key: t.urn || i }))}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>

      <Modal
        title="创建标签"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="标签名称" rules={[{ required: true, message: '请输入标签名称' }]}>
            <Input placeholder="如：PII、财务数据" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="标签描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Tags;
