/**
 * Template Market Page
 *
 * Browse and discover workflow templates from the template marketplace.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Input,
  Select,
  Tag,
  Button,
  Space,
  Pagination,
  Empty,
  Spin,
  Rate,
  Badge,
  Tooltip,
  Tabs,
  message,
} from 'antd';
import {
  SearchOutlined,
  StarOutlined,
  StarFilled,
  DownloadOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useTemplateStore } from '@/stores/template';
import type { TemplateCategory, TemplateComplexity } from '@/types/template';

const { Search } = Input;
const { Option } = Select;

const TemplateMarketPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    templates,
    categories,
    featuredTemplates,
    trendingTemplates,
    loading,
    error,
    fetchMarketTemplates,
    fetchCategories,
    fetchFeaturedTemplates,
    fetchTrendingTemplates,
    recordUsage,
  } = useTemplateStore();

  // Filters
  const [searchValue, setSearchValue] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [selectedComplexity, setSelectedComplexity] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState('popular');
  const [verifiedOnly, setVerifiedOnly] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);

  // Active tab
  const [activeTab, setActiveTab] = useState('all');

  // Fetch initial data
  useEffect(() => {
    fetchCategories();
    fetchFeaturedTemplates();
    fetchTrendingTemplates();
  }, [fetchCategories, fetchFeaturedTemplates, fetchTrendingTemplates]);

  // Fetch templates when filters change
  useEffect(() => {
    fetchMarketTemplates({
      category: selectedCategory,
      complexity: selectedComplexity as TemplateComplexity,
      search: searchValue || undefined,
      sort_by: sortBy,
      verified_only: verifiedOnly,
    });
  }, [selectedCategory, selectedComplexity, searchValue, sortBy, verifiedOnly, fetchMarketTemplates]);

  // Filtered and paginated templates
  const displayTemplates = useMemo(() => {
    let filtered = [...templates];

    if (activeTab === 'featured') {
      filtered = featuredTemplates;
    } else if (activeTab === 'trending') {
      filtered = trendingTemplates;
    }

    // Apply pagination
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;

    return filtered.slice(start, end);
  }, [templates, featuredTemplates, trendingTemplates, activeTab, currentPage, pageSize]);

  // Complexity colors
  const complexityColors: Record<string, string> = {
    beginner: 'green',
    intermediate: 'blue',
    advanced: 'orange',
  };

  // Category icons
  const categoryIcons: Record<string, string> = {
    etl: '🔄',
    ml_training: '🧠',
    data_quality: '📊',
    monitoring: '📈',
    batch_inference: '🔮',
    data_sync: '🔄',
    reporting: '📄',
    notification: '🔔',
    backup: '💾',
    data_pipeline: '⚙️',
  };

  // Handle template click
  const handleTemplateClick = (templateId: string) => {
    navigate(`/templates/${templateId}`);
  };

  // Handle template use
  const handleUseTemplate = async (templateId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await recordUsage(templateId);
    navigate(`/workflows/editor/new?template=${templateId}`);
  };

  // Render template card
  const renderTemplateCard = (template: any) => {
    const stats = template.stats || {};
    const avgRating = stats.avg_rating || 0;
    const ratingCount = stats.rating_count || 0;

    return (
      <Badge.Ribbon
        key={template.id}
        text={template.official ? 'Official' : template.verified ? 'Verified' : undefined}
        color={template.official ? 'blue' : 'green'}
      >
        <Card
          hoverable
          onClick={() => handleTemplateClick(template.id)}
          cover={
            <div
              style={{
                height: 140,
                background: `linear-gradient(135deg, ${getCategoryColor(template.category)} 0%, ${getCategoryColor(template.category)}33 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 48,
              }}
            >
              {template.icon || categoryIcons[template.category] || '📦'}
            </div>
          }
          actions={[
            <Tooltip title="Use this template">
              <Button
                type="primary"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={(e) => handleUseTemplate(template.id, e)}
              >
                Use
              </Button>
            </Tooltip>,
            <Tooltip title={`Downloaded ${stats.download_count || 0} times`}>
              <Button size="small" icon={<DownloadOutlined />}>
                {stats.download_count || 0}
              </Button>
            </Tooltip>,
          ]}
        >
          <Card.Meta
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{template.name}</span>
                {template.complexity && (
                  <Tag color={complexityColors[template.complexity]}>
                    {template.complexity}
                  </Tag>
                )}
              </div>
            }
            description={
              <div>
                <div style={{ marginBottom: 8 }}>
                  {template.description}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Rate
                    disabled
                    value={avgRating}
                    style={{ fontSize: 12 }}
                  />
                  <span style={{ fontSize: 12, color: '#999' }}>
                    ({ratingCount})
                  </span>
                </div>
                <div style={{ marginTop: 8 }}>
                  {template.tags?.slice(0, 3).map((tag: string) => (
                    <Tag key={tag} style={{ marginBottom: 4 }}>
                      {tag}
                    </Tag>
                  ))}
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  By {template.author || 'Unknown'} • {template.task_count || 0} tasks
                </div>
              </div>
            }
          />
        </Card>
      </Badge.Ribbon>
    );
  };

  // Get category color
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      etl: '#1890ff',
      ml_training: '#722ed1',
      data_quality: '#52c41a',
      monitoring: '#fa8c16',
      batch_inference: '#eb2f96',
      data_sync: '#13c2c2',
      reporting: '#2f54eb',
      notification: '#faad14',
      backup: '#595959',
      data_pipeline: '#1890ff',
    };
    return colors[category] || '#1890ff';
  };

  // Tab items
  const tabItems = [
    {
      key: 'all',
      label: `All Templates (${templates.length})`,
    },
    {
      key: 'featured',
      label: `Featured`,
    },
    {
      key: 'trending',
      label: `Trending`,
    },
  ];

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, marginBottom: 8 }}>Template Market</h1>
        <p style={{ margin: 0, color: '#666' }}>
          Discover and use pre-built workflow templates for common data operations
        </p>
      </div>

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Search
              placeholder="Search templates..."
              allowClear
              prefix={<SearchOutlined />}
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onSearch={setSearchValue}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="Category"
              allowClear
              style={{ width: '100%' }}
              value={selectedCategory}
              onChange={setSelectedCategory}
            >
              {categories.map((cat) => (
                <Option key={cat.value} value={cat.value}>
                  {cat.icon} {cat.label} ({cat.count})
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="Complexity"
              allowClear
              style={{ width: '100%' }}
              value={selectedComplexity}
              onChange={setSelectedComplexity}
            >
              <Option value="beginner">Beginner</Option>
              <Option value="intermediate">Intermediate</Option>
              <Option value="advanced">Advanced</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Select
              style={{ width: '100%' }}
              value={sortBy}
              onChange={setSortBy}
            >
              <Option value="popular">Most Popular</Option>
              <Option value="newest">Newest</Option>
              <Option value="rating">Highest Rated</Option>
              <Option value="verified">Verified Only</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Space>
              <Button
                icon={<CheckCircleOutlined />}
                type={verifiedOnly ? 'primary' : 'default'}
                onClick={() => setVerifiedOnly(!verifiedOnly)}
              >
                Verified
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Content */}
      <Tabs activeKey={activeTab} items={tabItems} onChange={setActiveTab} />

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : displayTemplates.length === 0 ? (
        <Empty
          description={
            activeTab === 'all' && (searchValue || selectedCategory || selectedComplexity)
              ? 'No templates match your filters'
              : 'No templates available'
          }
        />
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {displayTemplates.map((template) => (
              <Col key={template.id} xs={24} sm={12} md={8} lg={6}>
                {renderTemplateCard(template)}
              </Col>
            ))}
          </Row>

          {/* Pagination */}
          {activeTab === 'all' && (
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Pagination
                current={currentPage}
                pageSize={pageSize}
                total={templates.length}
                showSizeChanger
                showTotal={(total) => `${total} templates`}
                onChange={(page, size) => {
                  setCurrentPage(page);
                  setPageSize(size || 12);
                }}
              />
            </div>
          )}
        </>
      )}

      {error && message.error(error)}
    </div>
  );
};

export default TemplateMarketPage;
