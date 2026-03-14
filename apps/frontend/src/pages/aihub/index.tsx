/**
 * AIHub Model Marketplace
 *
 * Browse, search, and deploy 400+ open-source AI models.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Input,
  Select,
  Button,
  Tag,
  Space,
  Tooltip,
  Badge,
  Statistic,
  message,
  Tabs,
  Modal,
  Descriptions,
  Progress,
  Divider,
} from 'antd';
import {
  SearchOutlined,
  RocketOutlined,
  CodeOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  FilterOutlined,
  DatabaseOutlined,
  ApiOutlined,
  StarOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import {
  useAIHubStore,
  useAIHubModels,
  useAIHubLoading,
} from '@/stores/aihub';
import type { AIHubModel, ModelCategory, ModelFramework } from '@/stores/aihub';

const { Search } = Input;
const { Option } = Select;

const AIHubPage: React.FC = () => {
  const router = useRouter();
  const [form] = Form.useForm();

  const {
    models,
    categories,
    frameworks,
    stats,
    fetchModels,
    fetchCategories,
    fetchFrameworks,
    fetchStats,
    clearError,
  } = useAIHubStore();

  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [selectedFramework, setSelectedFramework] = useState<string | undefined>();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'market' | 'deployments' | 'finetune'>('market');
  const [previewModel, setPreviewModel] = useState<AIHubModel | null>(null);

  useEffect(() => {
    fetchCategories();
    fetchFrameworks();
    fetchStats();
    fetchModels();
  }, [fetchCategories, fetchFrameworks, fetchStats, fetchModels]);

  const handleSearch = () => {
    fetchModels({
      category: selectedCategory,
      framework: selectedFramework,
      search: searchTerm,
    });
  };

  const handleDeploy = (model: AIHubModel) => {
    router.push(`/aihub/deploy/${model.id}`);
  };

  const handleFinetune = (model: AIHubModel) => {
    router.push(`/aihub/finetune/${model.id}`);
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      llm: 'purple',
      embedding: 'blue',
      image_classification: 'green',
      object_detection: 'orange',
      segmentation: 'cyan',
      ocr: 'magenta',
      vision_language: 'gold',
      asr: 'lime',
      tts: 'pink',
    };
    return colors[category] || 'default';
  };

  const modelCards = models.map((model) => ({
    ...model,
    key: model.id,
  }));

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>
            <DatabaseOutlined /> AIHub Model Market
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            400+ open-source AI models ready for deployment
          </p>
        </Col>
      </Row>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Models"
              value={stats.total || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Categories"
              value={Object.keys(stats.categories || {}).length}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Deployments"
              value={0}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Finetuning Jobs"
              value={0}
              prefix={<CodeOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={(key) => setActiveTab(key as any)}>
          <Tabs.TabPane tab="Model Market" key="market">
            {/* Filters */}
            <Row gutter={16} style={{ marginBottom: '24px' }} align="middle">
              <Col span={8}>
                <Search
                  placeholder="Search models by name, description, or tags..."
                  allowClear
                  enterButton={<SearchOutlined />}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onSearch={handleSearch}
                />
              </Col>
              <Col span={5}>
                <Select
                  placeholder="Category"
                  allowClear
                  style={{ width: '100%' }}
                  value={selectedCategory}
                  onChange={setSelectedCategory}
                >
                  {categories.map((cat) => (
                    <Option key={cat.value} value={cat.value}>
                      {cat.label}
                    </Option>
                  ))}
                </Select>
              </Col>
              <Col span={5}>
                <Select
                  placeholder="Framework"
                  allowClear
                  style={{ width: '100%' }}
                  value={selectedFramework}
                  onChange={setSelectedFramework}
                >
                  {frameworks.map((fw) => (
                    <Option key={fw} value={fw}>
                      {fw.charAt(0).toUpperCase() + fw.slice(1)}
                    </Option>
                  ))}
                </Select>
              </Col>
              <Col span={6}>
                <Button type="primary" icon={<FilterOutlined />} onClick={handleSearch}>
                  Apply Filters
                </Button>
              </Col>
            </Row>

            {/* Model Grid */}
            <Row gutter={[16, 16]}>
              {modelCards.map((model) => (
                <Col key={model.id} xs={24} sm={12} md={8} lg={6}>
                  <Card
                    hoverable
                    size="small"
                    actions={[
                      <Tooltip title="View Details">
                        <Button
                          type="text"
                          icon={<EyeOutlined />}
                          onClick={() => setPreviewModel(model)}
                        />
                      </Tooltip>,
                      <Tooltip title="Deploy">
                        <Button
                          type="text"
                          icon={<RocketOutlined />}
                          onClick={() => handleDeploy(model)}
                        />
                      </Tooltip>,
                      <Tooltip title="Finetune">
                        <Button
                          type="text"
                          icon={<CodeOutlined />}
                          onClick={() => handleFinetune(model)}
                        />
                      </Tooltip>,
                    ]}
                  >
                    <Space direction="vertical" style={{ width: '100%' }} size="small">
                      <div>
                        <Tag color={getCategoryColor(model.category)} style={{ marginBottom: '4px' }}>
                          {model.category.replace('_', ' ')}
                        </Tag>
                      </div>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>
                        {model.name}
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        {model.description?.substring(0, 60)}
                        {model.description && model.description.length > 60 ? '...' : ''}
                      </div>
                      <div>
                        {model.tags?.slice(0, 3).map((tag) => (
                          <Tag key={tag} style={{ fontSize: '11px' }}>
                            {tag}
                          </Tag>
                        ))}
                      </div>
                      <Divider style={{ margin: '8px 0' }} />
                      <Row gutter={8}>
                        <Col span={12}>
                          <Space size="small">
                            <ThunderboltOutlined style={{ color: '#1890ff' }} />
                            <span style={{ fontSize: '11px' }}>
                              {model.parameter_size || '-'}
                            </span>
                          </Space>
                        </Col>
                        <Col span={12}>
                          <span style={{ fontSize: '11px', color: '#666' }}>
                            {model.provider || '-'}
                          </span>
                        </Col>
                      </Row>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Tabs.TabPane>

          <Tabs.TabPane tab="My Deployments" key="deployments">
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
              <RocketOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <p>Deploy a model to get started</p>
              <Button type="primary" onClick={() => setActiveTab('market')}>
                Browse Models
              </Button>
            </div>
          </Tabs.TabPane>

          <Tabs.TabPane tab="Fine-tuning Jobs" key="finetune">
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
              <CodeOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <p>No fine-tuning jobs yet</p>
              <Button type="primary" onClick={() => setActiveTab('market')}>
                Browse Models
              </Button>
            </div>
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* Model Preview Modal */}
      <Modal
        title={previewModel?.name}
        open={!!previewModel}
        onCancel={() => setPreviewModel(null)}
        footer={[
          <Button key="close" onClick={() => setPreviewModel(null)}>
            Close
          </Button>,
          <Button
            key="finetune"
            onClick={() => {
              if (previewModel) {
                handleFinetune(previewModel);
                setPreviewModel(null);
              }
            }}
          >
            Finetune
          </Button>,
          <Button
            key="deploy"
            type="primary"
            icon={<RocketOutlined />}
            onClick={() => {
              if (previewModel) {
                handleDeploy(previewModel);
                setPreviewModel(null);
              }
            }}
          >
            Deploy Now
          </Button>,
        ]}
        width={700}
      >
        {previewModel && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="ID" span={2}>
              <code>{previewModel.id}</code>
            </Descriptions.Item>
            <Descriptions.Item label="Category" span={2}>
              <Tag color={getCategoryColor(previewModel.category)}>
                {previewModel.category.replace('_', ' ')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Framework">
              <Tag>{previewModel.framework}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="License">
              <Tag>{previewModel.license}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Description" span={2}>
              {previewModel.description}
            </Descriptions.Item>
            <Descriptions.Item label="Provider">
              {previewModel.provider}
            </Descriptions.Item>
            <Descriptions.Item label="Parameters">
              {previewModel.parameter_size}
            </Descriptions.Item>
            <Descriptions.Item label="GPU Memory">
              {previewModel.gpu_memory_mb
                ? `${(previewModel.gpu_memory_mb / 1024).toFixed(1)} GB`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="CPU Cores">
              {previewModel.cpu_cores || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Tasks" span={2}>
              <Space wrap>
                {previewModel.tasks?.map((task) => (
                  <Tag key={task}>{task}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Languages" span={2}>
              <Space wrap>
                {previewModel.languages?.map((lang) => (
                  <Tag key={lang}>{lang.toUpperCase()}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Capabilities" span={2}>
              <Space wrap>
                {previewModel.capabilities?.cuda_supported && (
                  <Tag color="green">CUDA</Tag>
                )}
                {previewModel.capabilities?.quantization_available && (
                  <Tag color="blue">Quantization</Tag>
                )}
                {previewModel.capabilities?.streaming && (
                  <Tag color="purple">Streaming</Tag>
                )}
                {previewModel.capabilities?.function_calling && (
                  <Tag color="orange">Function Calling</Tag>
                )}
                {previewModel.capabilities?.vision && <Tag color="cyan">Vision</Tag>}
                {previewModel.capabilities?.code && <Tag color="magenta">Code</Tag>}
              </Space>
            </Descriptions.Item>
            {previewModel.paper_url && (
              <Descriptions.Item label="Paper" span={2}>
                <a href={previewModel.paper_url} target="_blank" rel="noopener noreferrer">
                  <ApiOutlined /> Research Paper
                </a>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default AIHubPage;
