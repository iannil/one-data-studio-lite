import React, { useState } from 'react';
import {
  Card,
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
  Row,
  Col,
  Table,
} from 'antd';
import {
  FileTextOutlined,
  PlusOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type ContentType = 'article' | 'help' | 'news';
type ContentStatus = 'draft' | 'published' | 'archived';

interface ContentItem {
  id: string;
  title: string;
  summary: string;
  content: string;
  type: ContentType;
  status: ContentStatus;
  category: string;
  tags: string[];
  author: string;
  viewCount: number;
  publishTime?: string;
  createdAt: string;
}

const DEMO_CONTENTS: ContentItem[] = [
  {
    id: '1',
    title: 'NL2SQL 使用指南',
    summary: '如何使用自然语言查询数据，快速获取业务洞察',
    content: 'NL2SQL 功能介绍\n\nNL2SQL（Natural Language to SQL）是一种允许用户使用自然语言查询数据库的技术...',
    type: 'help',
    status: 'published',
    category: '使用指南',
    tags: ['NL2SQL', '教程'],
    author: 'data_team',
    viewCount: 342,
    publishTime: '2026-01-25 10:00:00',
    createdAt: '2026-01-20 10:00:00',
  },
  {
    id: '2',
    title: '数据质量检查最佳实践',
    summary: '配置和使用数据质量检查功能的完整指南',
    content: '数据质量是数据管理的重要环节...',
    type: 'article',
    status: 'published',
    category: '最佳实践',
    tags: ['数据质量', '指南'],
    author: 'quality_team',
    viewCount: 156,
    publishTime: '2026-01-22 14:00:00',
    createdAt: '2026-01-18 09:00:00',
  },
  {
    id: '3',
    title: 'v2.1 版本新功能介绍',
    summary: '系统升级到 v2.1 版本，新增数据融合和多项优化',
    content: '我们很高兴宣布...',
    type: 'news',
    status: 'published',
    category: '产品动态',
    tags: ['版本更新', '新功能'],
    author: 'product_team',
    viewCount: 567,
    publishTime: '2026-01-20 09:00:00',
    createdAt: '2026-01-19 16:00:00',
  },
];

const CONTENT_TYPE_OPTIONS = [
  { label: '文章', value: 'article' },
  { label: '帮助文档', value: 'help' },
  { label: '新闻动态', value: 'news' },
];

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' },
];

const CATEGORY_OPTIONS = [
  { label: '使用指南', value: '使用指南' },
  { label: '最佳实践', value: '最佳实践' },
  { label: '产品动态', value: '产品动态' },
  { label: '技术文档', value: '技术文档' },
  { label: '常见问题', value: '常见问题' },
];

const Content: React.FC = () => {
  const [contents, setContents] = useState<ContentItem[]>(DEMO_CONTENTS);
  const [modalVisible, setModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [editingContent, setEditingContent] = useState<ContentItem | null>(null);
  const [viewingContent, setViewingContent] = useState<ContentItem | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingContent(null);
    form.resetFields();
    form.setFieldsValue({
      type: 'article',
      status: 'draft',
      category: '使用指南',
    });
    setModalVisible(true);
  };

  const handleEdit = (content: ContentItem) => {
    setEditingContent(content);
    form.setFieldsValue(content);
    setModalVisible(true);
  };

  const handleView = (content: ContentItem) => {
    setViewingContent(content);
    setViewModalVisible(true);
    // Update view count
    setContents((prev) =>
      prev.map((c) =>
        c.id === content.id
          ? { ...c, viewCount: (c.viewCount || 0) + 1 }
          : c
      )
    );
  };

  const handleDelete = (id: string) => {
    setContents(contents.filter((c) => c.id !== id));
    message.success('删除成功');
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingContent) {
        setContents((prev) =>
          prev.map((c) =>
            c.id === editingContent.id ? { ...c, ...values } : c
          )
        );
        message.success('更新成功');
      } else {
        const newContent: ContentItem = {
          id: Date.now().toString(),
          title: values.title,
          summary: values.summary,
          content: values.content,
          type: values.type,
          status: values.status,
          category: values.category,
          tags: values.tags || [],
          author: 'admin',
          viewCount: 0,
          publishTime: values.status === 'published' ? new Date().toLocaleString('zh-CN') : undefined,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setContents([newContent, ...contents]);
        message.success('创建成功');
      }
      setModalVisible(false);
    });
  };

  const getTypeTag = (type: ContentType) => {
    const config: Record<ContentType, { color: string; text: string }> = {
      article: { color: 'blue', text: '文章' },
      help: { color: 'green', text: '帮助' },
      news: { color: 'orange', text: '新闻' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const getStatusTag = (status: ContentStatus) => {
    const config: Record<ContentStatus, { color: string; text: string }> = {
      draft: { color: 'default', text: '草稿' },
      published: { color: 'success', text: '已发布' },
      archived: { color: 'default', text: '已归档' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 200 },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (type: ContentType) => getTypeTag(type),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => <Tag>{category}</Tag>,
    },
    { title: '标签', dataIndex: 'tags', key: 'tags', render: (tags: string[]) => tags.slice(0, 2).map((t) => <Tag key={t}>{t}</Tag>) },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ContentStatus) => getStatusTag(status),
    },
    { title: '浏览量', dataIndex: 'viewCount', key: 'viewCount', width: 80 },
    { title: '作者', dataIndex: 'author', key: 'author', width: 100 },
    {
      title: '发布时间',
      dataIndex: 'publishTime',
      key: 'publishTime',
      width: 160,
      render: (t?: string) => t || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: ContentItem) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
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
        <FileTextOutlined /> 内容发布管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="内容管理说明"
          description="支持发布文章、帮助文档、新闻动态等内容，支持分类、标签管理和全文搜索。"
          type="info"
          showIcon
        />

        <Card
          size="small"
          title="内容列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建内容
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={contents.map((c) => ({ ...c, key: c.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1000 }}
          />
        </Card>
      </Space>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingContent ? '编辑内容' : '新建内容'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={800}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="title"
            label="内容标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="请输入内容标题" />
          </Form.Item>

          <Form.Item
            name="summary"
            label="摘要"
            rules={[{ required: true, message: '请输入摘要' }]}
          >
            <Input.TextArea rows={2} placeholder="简短描述，用于列表展示" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="type" label="内容类型" rules={[{ required: true }]}>
                <Select options={CONTENT_TYPE_OPTIONS} placeholder="选择类型" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="category" label="分类" rules={[{ required: true }]}>
                <Select options={CATEGORY_OPTIONS} placeholder="选择分类" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="status" label="状态" rules={[{ required: true }]}>
                <Select options={STATUS_OPTIONS} placeholder="选择状态" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="tags"
                label="标签"
                rules={[{ type: 'array' }]}
              >
                <Select
                  mode="tags"
                  placeholder="输入标签，回车添加"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="content"
            label="正文内容"
            rules={[{ required: true, message: '请输入正文内容' }]}
          >
            <TextArea rows={10} placeholder="支持 Markdown 格式..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看弹窗 */}
      <Modal
        title="内容详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {viewingContent && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title="基本信息">
              <Row gutter={16}>
                <Col span={8}>
                  <Text strong>标题：</Text>
                  <Text>{viewingContent.title}</Text>
                </Col>
                <Col span={8}>
                  <Text strong>类型：</Text>
                  {getTypeTag(viewingContent.type)}
                </Col>
                <Col span={8}>
                  <Text strong>浏览量：</Text>
                  <Text>{viewingContent.viewCount}</Text>
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 8 }}>
                <Col span={8}>
                  <Text strong>分类：</Text>
                  <Tag>{viewingContent.category}</Tag>
                </Col>
                <Col span={8}>
                  <Text strong>作者：</Text>
                  <Text>{viewingContent.author}</Text>
                </Col>
                <Col span={8}>
                  <Text strong>发布时间：</Text>
                  <Text>{viewingContent.publishTime || '未发布'}</Text>
                </Col>
              </Row>
            </Card>

            <Card size="small" title="摘要">
              <Text>{viewingContent.summary}</Text>
            </Card>

            <Card size="small" title="正文">
              <div
                style={{
                  maxHeight: 400,
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.8,
                  padding: 16,
                  backgroundColor: '#fafafa',
                  borderRadius: 4,
                }}
              >
                {viewingContent.content}
              </div>
            </Card>
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default Content;
