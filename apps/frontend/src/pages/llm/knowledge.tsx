/**
 * Knowledge Base Page
 *
 * Private knowledge base with RAG (Retrieval-Augmented Generation) support.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Input,
  Table,
  Space,
  message,
  Modal,
  Form,
  Tag,
  List,
  Alert,
  Statistic,
  Tabs,
  Select,
  Slider,
  Divider,
  Tooltip,
  Upload,
  Progress,
  Avatar,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SearchOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  QuestionCircleOutlined,
  BookOutlined,
  SettingOutlined,
  DownloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import {
  useLLMStore,
  useKnowledgeBases,
  useSearchResults,
  useLLMLoading,
} from '@/stores/llm';

const { TextArea } = Input;
const { Option } = Select;
const { TabPane } = Tabs;

const KnowledgePage: React.FC = () => {
  const router = useRouter();
  const [form] = Form.useForm();
  const [docForm] = Form.useForm();

  const {
    knowledgeBases,
    currentKB,
    kbDocuments,
    searchResults,
    loading,
    fetchKnowledgeBases,
    createKnowledgeBase,
    deleteKnowledgeBase,
    addDocument,
    deleteDocument,
    searchKnowledgeBase,
    askQuestion,
    clearError,
  } = useLLMStore();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [addDocModalOpen, setAddDocModalOpen] = useState(false);
  const [selectedKB, setSelectedKB] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [asking, setAsking] = useState(false);
  const [ragAnswer, setRagAnswer] = useState<any>(null);

  useEffect(() => {
    fetchKnowledgeBases();
  }, [fetchKnowledgeBases]);

  const handleCreateKB = async () => {
    const values = form.getFieldsValue();
    try {
      await createKnowledgeBase({
        name: values.name,
        description: values.description,
        embedding_model: values.embedding_model,
        chunk_size: values.chunk_size,
        chunk_overlap: values.chunk_overlap,
        retrieval_top_k: values.retrieval_top_k,
      });
      message.success('Knowledge base created');
      setCreateModalOpen(false);
      form.resetFields();
    } catch (err) {
      message.error('Failed to create knowledge base');
    }
  };

  const handleSelectKB = (kb: any) => {
    setSelectedKB(kb);
  };

  const handleDeleteKB = async (kbId: string) => {
    try {
      await deleteKnowledgeBase(kbId);
      message.success('Knowledge base deleted');
    } catch (err) {
      message.error('Failed to delete knowledge base');
    }
  };

  const handleAddDocument = async () => {
    const values = docForm.getFieldsValue();
    if (!selectedKB) {
      message.warning('Please select a knowledge base first');
      return;
    }

    try {
      await addDocument(selectedKB.id, {
        title: values.title,
        content: values.content,
        source_uri: values.source_uri,
        chunk_strategy: values.chunk_strategy,
      });
      message.success('Document added');
      setAddDocModalOpen(false);
      docForm.resetFields();
    } catch (err) {
      message.error('Failed to add document');
    }
  };

  const handleSearch = async () => {
    if (!selectedKB || !searchQuery) {
      message.warning('Please select a knowledge base and enter a query');
      return;
    }

    setSearching(true);
    setRagAnswer(null);
    try {
      await searchKnowledgeBase(selectedKB.id, searchQuery, 5);
    } catch (err) {
      message.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleAsk = async () => {
    if (!selectedKB || !searchQuery) {
      message.warning('Please select a knowledge base and enter a question');
      return;
    }

    setAsking(true);
    setRagAnswer(null);
    try {
      const result = await askQuestion(selectedKB.id, searchQuery);
      setRagAnswer(result);
    } catch (err) {
      message.error('Failed to get answer');
    } finally {
      setAsking(false);
    }
  };

  const documentColumns = [
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      render: (title: string) => (
        <Space>
          <FileTextOutlined />
          {title}
        </Space>
      ),
    },
    {
      title: 'Chunks',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 100,
      render: (count: number) => <Tag>{count}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'indexed' ? 'green' : 'blue'}>{status}</Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, record: any) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => deleteDocument(selectedKB.id, record.id)}
        />
      ),
    },
  ];

  const totalDocs = knowledgeBases.reduce((sum, kb) => sum + (kb as any).document_count, 0);

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>
            <BookOutlined /> Knowledge Base
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            Private knowledge base with RAG-powered Q&A
          </p>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            New Knowledge Base
          </Button>
        </Col>
      </Row>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Knowledge Bases"
              value={knowledgeBases.length}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Documents"
              value={totalDocs}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Embeddings"
              value={totalDocs * 100}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Queries Today"
              value={0}
              prefix={<SearchOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={24}>
        {/* Left Column - KB List */}
        <Col span={8}>
          <Card
            title="My Knowledge Bases"
            extra={
              <Button size="small" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
                Add
              </Button>
            }
          >
            <List
              dataSource={knowledgeBases}
              renderItem={(kb: any) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    backgroundColor: selectedKB?.id === kb.id ? '#e6f7ff' : 'transparent',
                    borderRadius: '4px',
                    padding: '12px',
                  }}
                  onClick={() => handleSelectKB(kb)}
                >
                  <List.Item.Meta
                    avatar={<Avatar icon={<DatabaseOutlined />} style={{ backgroundColor: '#1890ff' }} />}
                    title={kb.name}
                    description={
                      <div>
                        <div>{kb.description || 'No description'}</div>
                        <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                          {kb.embedding_model} • {kb.chunk_size} chunks • {kb.document_count} docs
                        </div>
                      </div>
                    }
                  />
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteKB(kb.id);
                    }}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* Right Column - Search & Q&A */}
        <Col span={16}>
          {!selectedKB ? (
            <Card style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
              <DatabaseOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <p>Select or create a knowledge base to get started</p>
            </Card>
          ) : (
            <Tabs defaultActiveKey="search">
              <TabPane tab="Search & Q&A" key="search">
                {/* Search Input */}
                <Card style={{ marginBottom: '16px' }}>
                  <Row gutter={16}>
                    <Col flex="auto">
                      <Input.Search
                        placeholder="Ask a question or search the knowledge base..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        enterButton
                        size="large"
                        onSearch={handleAsk}
                        loading={asking}
                      />
                    </Col>
                    <Col>
                      <Button icon={<SearchOutlined />} onClick={handleSearch} loading={searching}>
                        Search
                      </Button>
                    </Col>
                  </Row>
                </Card>

                {/* RAG Answer */}
                {ragAnswer && (
                  <Card
                    style={{ marginBottom: '16px' }}
                    title="Answer"
                    extra={<Tag color="green">RAG</Tag>}
                  >
                    <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                      {ragAnswer.answer}
                    </div>
                    <Divider style={{ margin: '12px 0' }} />
                    <div>
                      <strong>Sources:</strong>
                      <List
                        size="small"
                        dataSource={ragAnswer.sources}
                        renderItem={(source: any) => (
                          <List.Item>
                            <div>Document: {source.document_id}</div>
                            <div style={{ fontSize: '12px', color: '#999' }}>
                              Score: {source.score.toFixed(3)}
                            </div>
                          </List.Item>
                        )}
                      />
                    </div>
                  </Card>
                )}

                {/* Search Results */}
                {!ragAnswer && searchResults.length > 0 && (
                  <Card title="Search Results" style={{ marginBottom: '16px' }}>
                    <List
                      dataSource={searchResults}
                      renderItem={(result: any) => (
                        <List.Item>
                          <Card size="small" style={{ width: '100%' }}>
                            <div style={{ marginBottom: '4px' }}>
                              <strong>Score:</strong>{' '}
                              <Tag color="green">{result.score.toFixed(3)}</Tag>
                            </div>
                            <div style={{ fontSize: '12px', color: '#666' }}>
                              {result.content.substring(0, 200)}...
                            </div>
                          </Card>
                        </List.Item>
                      )}
                    />
                  </Card>
                )}

                {!ragAnswer && searchResults.length === 0 && searchQuery && (
                  <Alert
                    type="info"
                    message="No results found"
                    description="Try rephrasing your question or search query"
                    showIcon
                  />
                )}
              </TabPane>

              <TabPane tab={`Documents (${selectedKB.document_count || 0})`} key="documents">
                <div style={{ marginBottom: '16px' }}>
                  <Button icon={<PlusOutlined />} onClick={() => setAddDocModalOpen(true)}>
                    Add Document
                  </Button>
                </div>
                <Table
                  columns={documentColumns}
                  dataSource={kbDocuments}
                  rowKey="id"
                  size="small"
                  pagination={false}
                />
              </TabPane>

              <TabPane tab="Settings" key="settings">
                <Card title="Knowledge Base Settings">
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="Name">{selectedKB.name}</Descriptions.Item>
                    <Descriptions.Item label="ID">{selectedKB.id}</Descriptions.Item>
                    <Descriptions.Item label="Embedding Model">{selectedKB.embedding_model}</Descriptions.Item>
                    <Descriptions.Item label="Chunk Size">{selectedKB.chunk_size}</Descriptions.Item>
                    <Descriptions.Item label="Chunk Overlap">{selectedKB.chunk_overlap}</Descriptions.Item>
                    <Descriptions.Item label="Retrieval Top-K">{selectedKB.retrieval_top_k}</Descriptions.Item>
                  </Descriptions>
                  <Divider />
                  <Button danger icon={<DeleteOutlined />}>
                    Delete Knowledge Base
                  </Button>
                </Card>
              </TabPane>
            </Tabs>
          )}
        </Col>
      </Row>

      {/* Create KB Modal */}
      <Modal
        title="Create Knowledge Base"
        open={createModalOpen}
        onOk={handleCreateKB}
        onCancel={() => {
          setCreateModalOpen(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Enter knowledge base name' }]}
          >
            <Input placeholder="My Knowledge Base" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Describe the purpose of this knowledge base..." />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="embedding_model"
                label="Embedding Model"
                initialValue="bge-large-zh"
              >
                <Select>
                  <Option value="bge-large-zh">BGE Large ZH</Option>
                  <Option value="bge-m3">BGE M3 (Multi-lingual)</Option>
                  <Option value="text-embedding-ada-002">OpenAI Ada-002</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="retrieval_top_k"
                label="Retrieval Top-K"
                initialValue={5}
              >
                <Slider min={1} max={20} marks={{ 1: '1', 5: '5', 10: '10', 20: '20' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Add Document Modal */}
      <Modal
        title="Add Document"
        open={addDocModalOpen}
        onOk={handleAddDocument}
        onCancel={() => {
          setAddDocModalOpen(false);
          docForm.resetFields();
        }}
      >
        <Form form={docForm} layout="vertical">
          <Form.Item
            name="title"
            label="Title"
            rules={[{ required: true, message: 'Enter document title' }]}
          >
            <Input placeholder="Document title" />
          </Form.Item>
          <Form.Item
            name="content"
            label="Content"
            rules={[{ required: true, message: 'Enter document content' }]}
          >
            <TextArea rows={8} placeholder="Paste document content here..." />
          </Form.Item>
          <Form.Item name="source_uri" label="Source URI (Optional)">
            <Input placeholder="https://example.com/doc.pdf" />
          </Form.Item>
          <Form.Item
            name="chunk_strategy"
            label="Chunking Strategy"
            initialValue="fixed_size"
          >
            <Select>
              <Option value="fixed_size">Fixed Size</Option>
              <Option value="paragraph">Paragraph</Option>
              <Option value="sentence">Sentence</Option>
              <Option value="recursive">Recursive</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KnowledgePage;
