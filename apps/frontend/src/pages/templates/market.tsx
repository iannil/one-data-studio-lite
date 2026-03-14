/**
 * Template Market Page
 *
 * Browse, search, and use workflow templates from the marketplace.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Typography,
  Divider,
  Rate,
  Avatar,
  Badge,
  Tooltip,
  Modal,
  Descriptions,
  Steps,
  Alert,
  message,
  Spin,
  Empty,
  Pagination,
} from 'antd';
import {
  SearchOutlined,
  ThunderboltOutlined,
  StarOutlined,
  DownloadOutlined,
  EyeOutlined,
  FilterOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  TagsOutlined,
  FolderOutlined,
  HeartOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useTemplateStore,
  useTemplates,
  useFeaturedTemplates,
  useCategories,
  useTemplateLoading,
  useTemplateError,
  useFilteredTemplates,
} from '@/stores/template';
import type {
  WorkflowTemplate,
  TemplateCategory,
  TemplateComplexity,
} from '@/types/template';
import {
  TEMPLATE_CATEGORIES,
  COMPLEXITY_OPTIONS,
  SORT_OPTIONS,
  POPULAR_TAGS,
} from '@/types/template';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

const TemplateMarketPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    // Data
    templates,
    currentTemplate,
    featuredTemplates,
    categories,

    // Actions
    fetchTemplates,
    fetchTemplate,
    fetchFeaturedTemplates,
    fetchCategories,
    instantiateTemplate,
    addReview,
    fetchReviews,

    // Filters
    filters,
    setFilters,
    setSearchQuery,
    resetFilters,

    // UI
    selectTemplate,
    clearError,
  } = useTemplateStore();

  const filteredTemplates = useFilteredTemplates();
  const loading = useTemplateLoading();
  const error = useTemplateError();

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [useModalOpen, setUseModalOpen] = useState(false);
  const [useStep, setUseStep] = useState(0);
  const [variableValues, setVariableValues] = useState<Record<string, unknown>>({});

  useEffect(() => {
    fetchTemplates();
    fetchFeaturedTemplates(6);
    fetchCategories();
  }, []);

  useEffect(() => {
    // Re-fetch when filters change
    fetchTemplates();
  }, [filters]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleCategoryClick = (category: TemplateCategory) => {
    setFilters({ category });
    setCurrentPage(1);
  };

  const handleSearch = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  const handlePreview = async (templateId: string) => {
    await fetchTemplate(templateId);
    setPreviewModalOpen(true);
  };

  const handleUseTemplate = async (templateId: string) => {
    await fetchTemplate(templateId);
    setUseModalOpen(true);
    setUseStep(0);
    setVariableValues({});
  };

  const handleSubmitTemplate = async () => {
    if (!currentTemplate) return;

    try {
      const result = await instantiateTemplate({
        template_id: currentTemplate.id,
        variables: variableValues,
        dag_name: `${currentTemplate.name}_${Date.now()}`,
      });
      message.success('Workflow created from template successfully');
      setUseModalOpen(false);
      navigate(`/workflows/editor/${result.dag_id}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to create workflow from template');
    }
  };

  const getComplexityColor = (complexity?: string) => {
    const option = COMPLEXITY_OPTIONS.find((o) => o.value === complexity);
    return option?.color || 'default';
  };

  const getComplexityIcon = (complexity?: string) => {
    const option = COMPLEXITY_OPTIONS.find((o) => o.value === complexity);
    return option?.icon || '📊';
  };

  const paginatedTemplates = filteredTemplates.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Render featured section
  const renderFeaturedSection = () => {
    if (featuredTemplates.length === 0) return null;

    return (
      <div style={{ marginBottom: 32 }}>
        <Title level={4}>
          <StarOutlined /> Featured Templates
        </Title>
        <Row gutter={[16, 16]}>
          {featuredTemplates.map((template) => (
            <Col key={template.id} xs={24} sm={12} md={8} lg={4}>
              <Card
                hoverable
                onClick={() => handlePreview(template.id)}
                cover={
                  <div
                    style={{
                      height: 120,
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 48,
                    }}
                  >
                    {template.icon || '📦'}
                  </div>
                }
                bodyStyle={{ padding: 12 }}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text strong ellipsis>
                    {template.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {template.category}
                  </Text>
                  {template.stats && (
                    <Space size={4}>
                      <Rate disabled value={template.stats.avg_rating} style={{ fontSize: 12 }} />
                      <Text style={{ fontSize: 12 }}>({template.stats.rating_count})</Text>
                    </Space>
                  )}
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  };

  // Render categories
  const renderCategories = () => {
    return (
      <Card style={{ marginBottom: 24 }}>
        <Title level={5} style={{ marginBottom: 16 }}>
          <FolderOutlined /> Categories
        </Title>
        <Space wrap>
          <Tag
            icon={<FolderOutlined />}
            style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 14 }}
            onClick={() => {
              setFilters({ category: undefined });
              setCurrentPage(1);
            }}
          >
            All ({templates.length})
          </Tag>
          {categories.map((cat) => (
            <Tag
              key={cat.value}
              icon={<span>{cat.icon}</span>}
              color={filters.category === cat.value ? 'blue' : 'default'}
              style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 14 }}
              onClick={() => handleCategoryClick(cat.value)}
            >
              {cat.label} ({cat.count})
            </Tag>
          ))}
        </Space>
      </Card>
    );
  };

  // Render template card
  const renderTemplateCard = (template: any) => (
    <Col key={template.id} xs={24} sm={12} md={8} lg={6}>
      <Badge.Ribbon
        text={template.official ? 'Official' : template.verified ? 'Verified' : null}
        color={template.official ? 'blue' : 'green'}
      >
        <Card
          hoverable
          onClick={() => handlePreview(template.id)}
          cover={
            <div
              style={{
                height: 140,
                background: `linear-gradient(135deg, ${getCategoryColor(template.category)} 0%, ${getCategoryColor(template.category, true)} 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 48,
                position: 'relative',
              }}
            >
              {template.icon || '📦'}
              {template.featured && (
                <div style={{ position: 'absolute', top: 8, right: 8 }}>
                  <StarOutlined style={{ color: '#fadb14', fontSize: 20 }} />
                </div>
              )}
            </div>
          }
          bodyStyle={{ padding: 16 }}
          actions={[
            <Tooltip title="View Details">
              <EyeOutlined key="view" />
            </Tooltip>,
            <Tooltip title="Use Template">
              <RocketOutlined
                key="use"
                onClick={(e) => {
                  e.stopPropagation();
                  handleUseTemplate(template.id);
                }}
              />
            </Tooltip>,
          ]}
        >
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong ellipsis>
              {template.name}
            </Text>
            <Text type="secondary" ellipsis style={{ fontSize: 12 }}>
              {template.description}
            </Text>
            <div style={{ marginTop: 4 }}>
              {template.tags?.slice(0, 2).map((tag: string) => (
                <Tag key={tag} size="small" style={{ fontSize: 11 }}>
                  {tag}
                </Tag>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
              <Tag
                icon={<span>{getComplexityIcon(template.complexity)}</span>}
                color={getComplexityColor(template.complexity)}
                style={{ fontSize: 11 }}
              >
                {template.complexity || 'intermediate'}
              </Tag>
              {template.stats && (
                <Space size={4}>
                  <Rate disabled value={Math.round(template.stats.avg_rating)} style={{ fontSize: 12 }} />
                  <Text style={{ fontSize: 11 }}>({template.stats.rating_count})</Text>
                </Space>
              )}
            </div>
          </Space>
        </Card>
      </Badge.Ribbon>
    </Col>
  );

  const getCategoryColor = (category: string, secondary = false) => {
    const colors: Record<string, { primary: string; secondary: string }> = {
      etl: { primary: '#667eea', secondary: '#764ba2' },
      ml_training: { primary: '#f093fb', secondary: '#f5576c' },
      data_quality: { primary: '#4facfe', secondary: '#00f2fe' },
      monitoring: { primary: '#43e97b', secondary: '#38f9d7' },
      batch_inference: { primary: '#fa709a', secondary: '#fee140' },
      data_sync: { primary: '#30cfd0', secondary: '#330867' },
      reporting: { primary: '#a8edea', secondary: '#fed6e3' },
      notification: { primary: '#ff9a9e', secondary: '#fecfef' },
      backup: { primary: '#667eea', secondary: '#764ba2' },
      data_pipeline: { primary: '#f5af19', secondary: '#f12711' },
    };
    const c = colors[category] || colors.data_pipeline;
    return secondary ? c.secondary : c.primary;
  };

  // Render preview modal
  const renderPreviewModal = () => {
    if (!currentTemplate) return null;

    const stats = currentTemplate.stats || { avg_rating: 0, rating_count: 0, usage_count: 0 };

    return (
      <Modal
        title={
          <Space>
            <span style={{ fontSize: 24 }}>{currentTemplate.icon || '📦'}</span>
            <span>{currentTemplate.name}</span>
            {currentTemplate.verified && (
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            )}
          </Space>
        }
        open={previewModalOpen}
        onCancel={() => setPreviewModalOpen(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setPreviewModalOpen(false)}>
            Close
          </Button>,
          <Button
            key="use"
            type="primary"
            icon={<RocketOutlined />}
            onClick={() => {
              setPreviewModalOpen(false);
              setUseModalOpen(true);
            }}
          >
            Use This Template
          </Button>,
        ]}
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Category" span={2}>
            <Tag icon={<span>{currentTemplate.icon}</span>}>{currentTemplate.category}</Tag>
          </Descriptions.Item>

          <Descriptions.Item label="Author" span={2}>
            <Space>
              <Avatar size="small" icon={<UserOutlined />} />
              {currentTemplate.author || 'System'}
            </Space>
          </Descriptions.Item>

          <Descriptions.Item label="Complexity">
            <Tag color={getComplexityColor(currentTemplate.complexity)}>
              {getComplexityIcon(currentTemplate.complexity)} {currentTemplate.complexity}
            </Tag>
          </Descriptions.Item>

          <Descriptions.Item label="Tasks">
            {currentTemplate.tasks?.length || 0} tasks
          </Descriptions.Item>

          <Descriptions.Item label="Variables">
            {currentTemplate.variables?.length || 0} variables
          </Descriptions.Item>

          <Descriptions.Item label="Version">
            {currentTemplate.current_version || '1.0.0'}
          </Descriptions.Item>

          <Descriptions.Item label="Rating" span={2}>
            <Space>
              <Rate disabled value={Math.round(stats.avg_rating)} />
              <Text>{stats.avg_rating.toFixed(1)}</Text>
              <Text type="secondary">({stats.rating_count} reviews)</Text>
            </Space>
          </Descriptions.Item>

          <Descriptions.Item label="Usage" span={2}>
            <Text>{stats.usage_count || 0} times used</Text>
          </Descriptions.Item>

          <Descriptions.Item label="Description" span={2}>
            {currentTemplate.description}
          </Descriptions.Item>

          <Descriptions.Item label="Tags" span={2}>
            {currentTemplate.tags?.map((tag) => (
              <Tag key={tag} color="blue">
                {tag}
              </Tag>
            ))}
          </Descriptions.Item>
        </Descriptions>

        {currentTemplate.tasks && currentTemplate.tasks.length > 0 && (
          <>
            <Divider orientation="left">Workflow Tasks</Divider>
            <Steps
              direction="vertical"
              current={-1}
              items={currentTemplate.tasks.map((task, index) => ({
                title: task.name,
                description: task.description,
                icon: index + 1,
              }))}
            />
          </>
        )}
      </Modal>
    );
  };

  // Render use template modal
  const renderUseModal = () => {
    if (!currentTemplate) return null;

    const steps = [
      { title: 'Configure Variables', icon: <RocketOutlined /> },
      { title: 'Review', icon: <EyeOutlined /> },
      { title: 'Create Workflow', icon: <CheckCircleOutlined /> },
    ];

    return (
      <Modal
        title={`Use Template: ${currentTemplate.name}`}
        open={useModalOpen}
        onCancel={() => setUseModalOpen(false)}
        width={700}
        footer={[
          <Button key="cancel" onClick={() => setUseModalOpen(false)}>
            Cancel
          </Button>,
          useStep > 0 && (
            <Button key="prev" onClick={() => setUseStep((s) => s - 1)}>
              Previous
            </Button>
          ),
          useStep < steps.length - 1 ? (
            <Button
              key="next"
              type="primary"
              onClick={() => {
                if (useStep === 0) {
                  // Validate required variables
                  const required = currentTemplate.variables?.filter((v) => v.required) || [];
                  const missing = required.filter((v) => !variableValues[v.name]);
                  if (missing.length > 0) {
                    message.warning(`Please fill in: ${missing.map((v) => v.label).join(', ')}`);
                    return;
                  }
                }
                setUseStep((s) => s + 1);
              }}
            >
              Next
            </Button>
          ) : (
            <Button
              key="submit"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={handleSubmitTemplate}
            >
              Create Workflow
            </Button>
          ),
        ]}
      >
        <Steps current={useStep} items={steps} style={{ marginBottom: 24 }} />

        {useStep === 0 && (
          <div>
            <Alert
              message="Configure the template variables to create your workflow."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {currentTemplate.variables?.map((variable) => (
                <div key={variable.name}>
                  <Space style={{ marginBottom: 4 }}>
                    <Text strong>{variable.label}</Text>
                    {variable.required && <Text type="danger">*</Text>}
                    {variable.description && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        - {variable.description}
                      </Text>
                    )}
                  </Space>

                  {variable.type === 'select' ? (
                    <Select
                      placeholder={`Select ${variable.label}`}
                      style={{ width: '100%' }}
                      value={variableValues[variable.name]}
                      onChange={(value) =>
                        setVariableValues({ ...variableValues, [variable.name]: value })
                      }
                      options={variable.options?.map((opt) => ({ label: opt, value: opt }))}
                    />
                  ) : variable.type === 'boolean' ? (
                    <Select
                      placeholder={`Select ${variable.label}`}
                      style={{ width: '100%' }}
                      value={variableValues[variable.name]}
                      onChange={(value) =>
                        setVariableValues({ ...variableValues, [variable.name]: value })
                      }
                      options={[
                        { label: 'True', value: true },
                        { label: 'False', value: false },
                      ]}
                    />
                  ) : variable.type === 'number' ? (
                    <Input
                      type="number"
                      placeholder={variable.placeholder || `Enter ${variable.label}`}
                      value={variableValues[variable.name]}
                      onChange={(e) =>
                        setVariableValues({
                          ...variableValues,
                          [variable.name]: parseFloat(e.target.value),
                        })
                      }
                    />
                  ) : variable.type === 'multiline' ? (
                    <Input.TextArea
                      rows={3}
                      placeholder={variable.placeholder || `Enter ${variable.label}`}
                      value={variableValues[variable.name]}
                      onChange={(e) =>
                        setVariableValues({ ...variableValues, [variable.name]: e.target.value })
                      }
                    />
                  ) : (
                    <Input
                      placeholder={variable.placeholder || `Enter ${variable.label}`}
                      value={variableValues[variable.name]}
                      onChange={(e) =>
                        setVariableValues({ ...variableValues, [variable.name]: e.target.value })
                      }
                    />
                  )}
                </div>
              ))}
            </Space>
          </div>
        )}

        {useStep === 1 && (
          <div>
            <Alert
              message="Review your configuration before creating the workflow."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Template">{currentTemplate.name}</Descriptions.Item>
              <Descriptions.Item label="Tasks">
                {currentTemplate.tasks?.length || 0}
              </Descriptions.Item>
              <Descriptions.Item label="Variables">
                {currentTemplate.variables?.length || 0}
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">Variable Values</Divider>
            <Space direction="vertical" style={{ width: '100%' }}>
              {currentTemplate.variables?.map((variable) => (
                <Row key={variable.name}>
                  <Col span={8}>
                    <Text strong>{variable.label}:</Text>
                  </Col>
                  <Col span={16}>
                    <Text code>
                      {variableValues[variable.name]?.toString() || variable.default?.toString() || '-'}
                    </Text>
                  </Col>
                </Row>
              ))}
            </Space>
          </div>
        )}

        {useStep === 2 && (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
            <Title level={4} style={{ marginTop: 16 }}>
              Ready to Create Workflow
            </Title>
            <Paragraph type="secondary">
              Click "Create Workflow" to instantiate the template with your configuration.
            </Paragraph>
          </div>
        )}
      </Modal>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              <ThunderboltOutlined /> Template Market
            </Title>
            <Text type="secondary">
              Browse and use pre-built workflow templates to accelerate your development
            </Text>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<RocketOutlined />}
              onClick={() => navigate('/workflows/new')}
            >
              Create Custom Workflow
            </Button>
          </Col>
        </Row>
      </div>

      {/* Featured */}
      {renderFeaturedSection()}

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Search
              placeholder="Search templates..."
              allowClear
              onSearch={handleSearch}
              style={{ width: 300 }}
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col>
            <Select
              placeholder="Category"
              allowClear
              style={{ width: 150 }}
              value={filters.category}
              onChange={(value) => {
                setFilters({ category: value });
                setCurrentPage(1);
              }}
              options={TEMPLATE_CATEGORIES.map((c) => ({ label: `${c.icon} ${c.label}`, value: c.value }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="Complexity"
              allowClear
              style={{ width: 130 }}
              value={filters.complexity}
              onChange={(value) => {
                setFilters({ complexity: value });
                setCurrentPage(1);
              }}
              options={COMPLEXITY_OPTIONS.map((c) => ({ label: `${c.icon} ${c.label}`, value: c.value }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="Sort By"
              style={{ width: 130 }}
              value={filters.sort_by}
              onChange={(value) => {
                setFilters({ sort_by: value });
                setCurrentPage(1);
              }}
              options={SORT_OPTIONS.map((s) => ({ label: s.label, value: s.value }))}
            />
          </Col>
          <Col>
            <Button icon={<FilterOutlined />} onClick={resetFilters}>
              Reset
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Categories */}
      {renderCategories()}

      {/* Template Grid */}
      <div>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <FilterOutlined />
              <Text strong>
                {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''} found
              </Text>
            </Space>
          </Col>
        </Row>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : paginatedTemplates.length > 0 ? (
          <>
            <Row gutter={[16, 16]}>{paginatedTemplates.map((t) => renderTemplateCard(t))}</Row>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Pagination
                current={currentPage}
                pageSize={pageSize}
                total={filteredTemplates.length}
                onChange={(page) => setCurrentPage(page)}
                showSizeChanger
                onShowSizeChange={(_, size) => setPageSize(size)}
                showTotal={(total) => `${total} templates`}
              />
            </div>
          </>
        ) : (
          <Empty
            description="No templates found"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: 48 }}
          >
            <Button type="primary" onClick={() => resetFilters()}>
              Reset Filters
            </Button>
          </Empty>
        )}
      </div>

      {/* Modals */}
      {renderPreviewModal()}
      {renderUseModal()}
    </div>
  );
};

export default TemplateMarketPage;
