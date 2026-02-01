import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Form,
  Input,
  Select,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Radio,
  DatePicker,
  Row,
  Col,
} from 'antd';
import {
  NotificationOutlined,
  PlusOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type AnnouncementStatus = 'draft' | 'published' | 'scheduled';
type Priority = 'low' | 'medium' | 'high';

interface Announcement {
  id: string;
  title: string;
  content: string;
  status: AnnouncementStatus;
  priority: Priority;
  targetType: 'all' | 'tenant' | 'role' | 'user';
  targetValues?: string[];
  publishTime?: string;
  scheduledTime?: string;
  viewCount: number;
  createdBy: string;
  createdAt: string;
}

const DEMO_ANNOUNCEMENTS: Announcement[] = [
  {
    id: '1',
    title: '系统升级通知 v2.1.0',
    content: '系统将于 2026年2月2日进行版本升级，新增数据融合功能，优化性能体验。',
    status: 'published',
    priority: 'high',
    targetType: 'all',
    publishTime: '2026-01-25 10:00:00',
    viewCount: 1256,
    createdBy: 'admin',
    createdAt: '2026-01-20 10:00:00',
  },
  {
    id: '2',
    title: '数据源维护通知',
    content: 'MySQL 主数据库将于 2月3日凌晨进行例行维护，预计耗时2小时。',
    status: 'published',
    priority: 'medium',
    targetType: 'all',
    publishTime: '2026-01-28 15:00:00',
    viewCount: 523,
    createdBy: 'admin',
    createdAt: '2026-01-26 14:00:00',
  },
  {
    id: '3',
    title: '新功能培训通知',
    content: '我们将于下周举办 NL2SQL 功能培训，欢迎各位同事参加。',
    status: 'scheduled',
    priority: 'low',
    targetType: 'all',
    scheduledTime: '2026-02-05 14:00:00',
    viewCount: 0,
    createdBy: 'hr',
    createdAt: '2026-01-30 09:00:00',
  },
];

const Announcements: React.FC = () => {
  const [announcements, setAnnouncements] = useState<Announcement[]>(DEMO_ANNOUNCEMENTS);
  const [modalVisible, setModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null);
  const [viewingAnnouncement, setViewingAnnouncement] = useState<Announcement | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingAnnouncement(null);
    form.resetFields();
    form.setFieldsValue({
      status: 'draft',
      priority: 'medium',
      targetType: 'all',
    });
    setModalVisible(true);
  };

  const handleEdit = (announcement: Announcement) => {
    setEditingAnnouncement(announcement);
    form.setFieldsValue(announcement);
    setModalVisible(true);
  };

  const handleView = (announcement: Announcement) => {
    setViewingAnnouncement(announcement);
    setViewModalVisible(true);
    // Update view count
    setAnnouncements((prev) =>
      prev.map((a) =>
        a.id === announcement.id
          ? { ...a, viewCount: (a.viewCount || 0) + 1 }
          : a
      )
    );
  };

  const handleDelete = (id: string) => {
    setAnnouncements(announcements.filter((a) => a.id !== id));
    message.success('删除成功');
  };

  const handlePublish = (id: string) => {
    setAnnouncements((prev) =>
      prev.map((a) =>
        a.id === id
          ? { ...a, status: 'published' as const, publishTime: new Date().toLocaleString('zh-CN') }
          : a
      )
    );
    message.success('发布成功');
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingAnnouncement) {
        setAnnouncements((prev) =>
          prev.map((a) =>
            a.id === editingAnnouncement.id ? { ...a, ...values } : a
          )
        );
        message.success('更新成功');
      } else {
        const newAnnouncement: Announcement = {
          id: Date.now().toString(),
          title: values.title,
          content: values.content,
          status: values.status,
          priority: values.priority,
          targetType: values.targetType,
          targetValues: values.targetValues,
          scheduledTime: values.scheduledTime,
          viewCount: 0,
          createdBy: 'admin',
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setAnnouncements([newAnnouncement, ...announcements]);
        message.success('创建成功');
      }
      setModalVisible(false);
    });
  };

  const getStatusTag = (status: AnnouncementStatus) => {
    const config = {
      draft: { color: 'default', text: '草稿' },
      published: { color: 'success', text: '已发布' },
      scheduled: { color: 'blue', text: '定时发布' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const getPriorityTag = (priority: Priority) => {
    const config = {
      low: { color: 'default', text: '低' },
      medium: { color: 'orange', text: '中' },
      high: { color: 'red', text: '高' },
    };
    const { color, text } = config[priority];
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 200 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: AnnouncementStatus) => getStatusTag(status),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: Priority) => getPriorityTag(priority),
    },
    {
      title: '目标人群',
      dataIndex: 'targetType',
      key: 'targetType',
      width: 100,
      render: (type: string, record: Announcement) => (
        <span>
          <Tag>{type === 'all' ? '全部' : type}</Tag>
          {record.targetValues && record.targetValues.length > 0 && (
            <Tag>+{record.targetValues.length}</Tag>
          )}
        </span>
      ),
    },
    { title: '浏览量', dataIndex: 'viewCount', key: 'viewCount', width: 80 },
    {
      title: '发布时间',
      dataIndex: 'publishTime',
      key: 'publishTime',
      width: 160,
      render: (t?: string) => t || '-',
    },
    {
      title: '创建者',
      dataIndex: 'createdBy',
      key: 'createdBy',
      width: 100,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, record: Announcement) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          {record.status === 'draft' && (
            <Button
              type="link"
              size="small"
              onClick={() => handlePublish(record.id)}
            >
              发布
            </Button>
          )}
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <NotificationOutlined /> 通知公告管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="公告发布说明"
          description="支持向全部用户、特定租户、角色或个人发布公告。草稿状态可编辑，发布后不可修改。"
          type="info"
          showIcon
        />

        <Card
          size="small"
          title="公告列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建公告
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={announcements.map((a) => ({ ...a, key: a.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1100 }}
          />
        </Card>
      </Space>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingAnnouncement ? '编辑公告' : '新建公告'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="title"
            label="公告标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="请输入公告标题" />
          </Form.Item>

          <Form.Item
            name="content"
            label="公告内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea rows={6} placeholder="请输入公告详细内容..." />
          </Form.Item>

          <Form.Item name="priority" label="优先级" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value="low">低</Radio>
              <Radio value="medium">中</Radio>
              <Radio value="high">高</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="targetType" label="目标人群" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value="all">全部用户</Radio>
              <Radio value="tenant">指定租户</Radio>
              <Radio value="role">指定角色</Radio>
              <Radio value="user">指定用户</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => currentValues?.targetType !== 'all'}>
            <Form.Item name="targetValues" label="目标值" style={{ display: form.getFieldValue('targetType') === 'all' ? 'none' : undefined }}>
              <Select
                mode="tags"
                placeholder={form.getFieldValue('targetType') === 'tenant' ? '选择租户' : form.getFieldValue('targetType') === 'role' ? '选择角色' : '输入用户ID'}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Form.Item>

          <Form.Item label="发布方式">
            <Radio.Group>
              <Radio value="draft">保存为草稿</Radio>
              <Radio value="published">立即发布</Radio>
              <Radio value="scheduled">定时发布</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => currentValues?.status === 'scheduled'}
          >
            <Form.Item name="scheduledTime" label="发布时间" style={{ display: form.getFieldValue('status') === 'scheduled' ? undefined : 'none' }}>
              <DatePicker showTime style={{ width: '100%' }} />
            </Form.Item>
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看弹窗 */}
      <Modal
        title="公告详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {viewingAnnouncement && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title="基本信息">
              <Row gutter={16}>
                <Col span={12}>
                  <Text strong>标题：</Text>
                  <Text>{viewingAnnouncement.title}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>优先级：</Text>
                  {getPriorityTag(viewingAnnouncement.priority)}
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 8 }}>
                <Col span={12}>
                  <Text strong>发布时间：</Text>
                  <Text>{viewingAnnouncement.publishTime || '未发布'}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>浏览量：</Text>
                  <Text>{viewingAnnouncement.viewCount}</Text>
                </Col>
              </Row>
            </Card>

            <Card size="small" title="公告内容">
              <div
                style={{
                  maxHeight: 300,
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.8,
                }}
              >
                {viewingAnnouncement.content}
              </div>
            </Card>
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default Announcements;
