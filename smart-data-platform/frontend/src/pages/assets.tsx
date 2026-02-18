'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Card,
  Input,
  Space,
  Tag,
  Button,
  Typography,
  Row,
  Col,
  Statistic,
  Modal,
  Descriptions,
  Badge,
  message,
  Slider,
  Spin,
  Progress,
  Tabs,
} from 'antd';
import {
  SearchOutlined,
  SafetyCertificateOutlined,
  FolderOutlined,
  ReloadOutlined,
  BranchesOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { assetsApi } from '@/services/api';
import type { DataAsset } from '@/types';

const { Title, Text } = Typography;
const { Search } = Input;

interface LineageNode {
  id: string;
  name: string;
  type: string;
  assetType?: string;
  description?: string;
  domain?: string;
  category?: string;
  depth?: number;
}

interface LineageEdge {
  source: string;
  target: string;
}

interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
}

interface ValueEvaluation {
  asset_id: string;
  value_score: number;
  value_level: string;
  factors: {
    usage_frequency: { score: number; max: number; metric: number };
    user_reach: { score: number; max: number; metric: number };
    business_impact: { score: number; max: number; metric: number };
    dependency_count: { score: number; max: number; metric: number };
    certification_bonus: number;
    metadata_quality: number;
  };
}

const LineageGraph = ({ data }: { data: LineageGraph }) => {
  const nodeColors: Record<string, string> = {
    current: '#1890ff',
    upstream: '#52c41a',
    downstream: '#faad14',
  };

  const getNodeStyle = (type: string) => ({
    background: nodeColors[type] || '#d9d9d9',
    color: '#fff',
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
    marginBottom: '8px',
    display: 'inline-block',
  });

  const currentNode = data.nodes.find((n) => n.type === 'current');
  const upstreamNodes = data.nodes.filter((n) => n.type === 'upstream');
  const downstreamNodes = data.nodes.filter((n) => n.type === 'downstream');

  return (
    <div style={{ padding: '20px' }}>
      <Row gutter={[24, 24]}>
        <Col span={8}>
          <Card
            title={
              <Space>
                <span style={{ color: nodeColors.upstream }}>●</span>
                上游数据源 ({upstreamNodes.length})
              </Space>
            }
            size="small"
          >
            {upstreamNodes.length > 0 ? (
              upstreamNodes.map((node) => (
                <div key={node.id} style={{ marginBottom: 8 }}>
                  <Tag color="green" style={{ marginRight: 8 }}>
                    {node.assetType || 'unknown'}
                  </Tag>
                  <Text strong>{node.name}</Text>
                  {node.depth && node.depth > 1 && (
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      (层级 {node.depth})
                    </Text>
                  )}
                  {node.description && (
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {node.description.substring(0, 50)}
                        {node.description.length > 50 ? '...' : ''}
                      </Text>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <Text type="secondary">无上游数据</Text>
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title={
              <Space>
                <span style={{ color: nodeColors.current }}>●</span>
                当前资产
              </Space>
            }
            size="small"
            style={{ borderColor: nodeColors.current, borderWidth: 2 }}
          >
            {currentNode && (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <div style={getNodeStyle('current')}>
                  <BranchesOutlined style={{ marginRight: 8 }} />
                  {currentNode.name}
                </div>
                <div style={{ marginTop: 8 }}>
                  <Tag>{currentNode.assetType || 'unknown'}</Tag>
                  {currentNode.domain && <Tag color="blue">{currentNode.domain}</Tag>}
                </div>
                {currentNode.description && (
                  <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                    {currentNode.description}
                  </Text>
                )}
              </div>
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title={
              <Space>
                <span style={{ color: nodeColors.downstream }}>●</span>
                下游消费者 ({downstreamNodes.length})
              </Space>
            }
            size="small"
          >
            {downstreamNodes.length > 0 ? (
              downstreamNodes.map((node) => (
                <div key={node.id} style={{ marginBottom: 8 }}>
                  <Tag color="orange" style={{ marginRight: 8 }}>
                    {node.assetType || 'unknown'}
                  </Tag>
                  <Text strong>{node.name}</Text>
                  {node.depth && node.depth > 1 && (
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      (层级 {node.depth})
                    </Text>
                  )}
                  {node.description && (
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {node.description.substring(0, 50)}
                        {node.description.length > 50 ? '...' : ''}
                      </Text>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <Text type="secondary">无下游消费者</Text>
            )}
          </Card>
        </Col>
      </Row>

      <div style={{ marginTop: 16 }}>
        <Card size="small" title="数据流向">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px 0' }}>
            {upstreamNodes.length > 0 && (
              <>
                <Tag color="green">{upstreamNodes.length} 上游</Tag>
                <span style={{ margin: '0 10px' }}>→</span>
              </>
            )}
            <Tag color="blue" style={{ fontWeight: 'bold' }}>
              {currentNode?.name || '当前资产'}
            </Tag>
            {downstreamNodes.length > 0 && (
              <>
                <span style={{ margin: '0 10px' }}>→</span>
                <Tag color="orange">{downstreamNodes.length} 下游</Tag>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

const ValueAssessment = ({ evaluation }: { evaluation: ValueEvaluation }) => {
  const levelColors: Record<string, string> = {
    high: '#52c41a',
    medium: '#faad14',
    low: '#ff4d4f',
  };

  const levelLabels: Record<string, string> = {
    high: '高价值',
    medium: '中等价值',
    low: '低价值',
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card>
            <Statistic
              title="价值评分"
              value={evaluation.value_score}
              suffix="/ 100"
              valueStyle={{ color: levelColors[evaluation.value_level] }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <Statistic
              title="价值等级"
              value={levelLabels[evaluation.value_level]}
              valueStyle={{ color: levelColors[evaluation.value_level] }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="评估因素" size="small">
        <div style={{ marginBottom: 16 }}>
          <Text>使用频率 ({evaluation.factors.usage_frequency.metric} 次访问)</Text>
          <Progress
            percent={(evaluation.factors.usage_frequency.score / evaluation.factors.usage_frequency.max) * 100}
            size="small"
            format={() => `${evaluation.factors.usage_frequency.score}/${evaluation.factors.usage_frequency.max}`}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <Text>用户覆盖 ({evaluation.factors.user_reach.metric} 用户)</Text>
          <Progress
            percent={(evaluation.factors.user_reach.score / evaluation.factors.user_reach.max) * 100}
            size="small"
            format={() => `${evaluation.factors.user_reach.score}/${evaluation.factors.user_reach.max}`}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <Text>业务影响 (下游深度: {evaluation.factors.business_impact.metric})</Text>
          <Progress
            percent={(evaluation.factors.business_impact.score / evaluation.factors.business_impact.max) * 100}
            size="small"
            format={() => `${evaluation.factors.business_impact.score}/${evaluation.factors.business_impact.max}`}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <Text>依赖关系 ({evaluation.factors.dependency_count.metric} 依赖)</Text>
          <Progress
            percent={(evaluation.factors.dependency_count.score / evaluation.factors.dependency_count.max) * 100}
            size="small"
            format={() => `${evaluation.factors.dependency_count.score}/${evaluation.factors.dependency_count.max}`}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <Text>认证加分</Text>
          <Progress
            percent={(evaluation.factors.certification_bonus / 10) * 100}
            size="small"
            format={() => `${evaluation.factors.certification_bonus}/10`}
          />
        </div>
        <div>
          <Text>元数据质量</Text>
          <Progress
            percent={(evaluation.factors.metadata_quality / 10) * 100}
            size="small"
            format={() => `${evaluation.factors.metadata_quality}/10`}
          />
        </div>
      </Card>
    </div>
  );
};

export default function AssetsPage() {
  const [assets, setAssets] = useState<DataAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<DataAsset | null>(null);
  const [lineageOpen, setLineageOpen] = useState(false);
  const [lineageData, setLineageData] = useState<{ lineage_graph: LineageGraph } | null>(null);
  const [lineageDepth, setLineageDepth] = useState(1);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [valueEvaluation, setValueEvaluation] = useState<ValueEvaluation | null>(null);
  const [valueLoading, setValueLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('lineage');

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const response = await assetsApi.list();
      setAssets(response.data);
    } catch (error) {
      message.error('获取数据资产列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchAssets();
      return;
    }

    setLoading(true);
    try {
      const response = await assetsApi.search({ query: searchQuery, limit: 50 });
      setAssets(response.data.results);
      if (response.data.ai_summary) {
        message.info(response.data.ai_summary);
      }
    } catch (error) {
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAISearch = async () => {
    if (!searchQuery.trim()) {
      message.warning('请输入搜索关键词');
      return;
    }

    setLoading(true);
    try {
      const response = await assetsApi.aiSearch(searchQuery);
      if (response.data.results && response.data.results.length > 0) {
        const matchedIds = response.data.results.map((r: any) => r.id);
        const filtered = assets.filter((a) => matchedIds.includes(a.id));
        setAssets(filtered.length > 0 ? filtered : []);
        message.success(response.data.ai_summary || `找到 ${response.data.total} 个匹配结果`);
      } else {
        setAssets([]);
        message.info('未找到匹配的资产');
      }
    } catch (error) {
      message.error('AI 搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchLineage = useCallback(
    async (assetId: string, depth: number) => {
      setLineageLoading(true);
      try {
        const response = await assetsApi.getLineage(assetId, depth);
        setLineageData(response.data);
      } catch (error) {
        message.error('获取血缘关系失败');
      } finally {
        setLineageLoading(false);
      }
    },
    []
  );

  const handleViewLineage = async (asset: DataAsset) => {
    setSelectedAsset(asset);
    setActiveTab('lineage');
    setLineageOpen(true);
    await fetchLineage(asset.id, lineageDepth);
  };

  const handleDepthChange = async (value: number) => {
    setLineageDepth(value);
    if (selectedAsset) {
      await fetchLineage(selectedAsset.id, value);
    }
  };

  const handleViewValue = async (asset: DataAsset) => {
    setSelectedAsset(asset);
    setActiveTab('value');
    setLineageOpen(true);
    setValueLoading(true);
    try {
      const response = await assetsApi.getValue(asset.id);
      setValueEvaluation(response.data);
    } catch (error) {
      message.error('获取价值评估失败');
    } finally {
      setValueLoading(false);
    }
  };

  const handleCertify = async (id: string) => {
    try {
      await assetsApi.certify(id);
      message.success('认证成功');
      fetchAssets();
    } catch (error) {
      message.error('认证失败');
    }
  };

  const handleRefreshAllValues = async () => {
    setLoading(true);
    try {
      const response = await assetsApi.batchRefreshValues();
      message.success(`已更新 ${response.data.updated} 个资产的价值评分`);
      fetchAssets();
    } catch (error) {
      message.error('批量更新价值评分失败');
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<DataAsset> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <FolderOutlined />
          <a onClick={() => setSelectedAsset(record)}>{name}</a>
          {record.is_certified && (
            <Badge status="success" text={<SafetyCertificateOutlined style={{ color: '#52c41a' }} />} />
          )}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'asset_type',
      key: 'asset_type',
      render: (type) => <Tag>{type}</Tag>,
    },
    {
      title: '访问级别',
      dataIndex: 'access_level',
      key: 'access_level',
      render: (level) => {
        const colors: Record<string, string> = {
          public: 'green',
          internal: 'blue',
          restricted: 'orange',
          confidential: 'red',
        };
        return <Tag color={colors[level]}>{level}</Tag>;
      },
    },
    {
      title: '领域',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => tags?.slice(0, 3).map((t) => <Tag key={t}>{t}</Tag>),
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      sorter: (a, b) => a.usage_count - b.usage_count,
    },
    {
      title: '价值评分',
      dataIndex: 'value_score',
      key: 'value_score',
      render: (score) => {
        if (!score) return '-';
        const color = score >= 70 ? '#52c41a' : score >= 40 ? '#faad14' : '#ff4d4f';
        return <Text style={{ color }}>{score.toFixed(1)}</Text>;
      },
      sorter: (a, b) => (a.value_score || 0) - (b.value_score || 0),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<BranchesOutlined />} onClick={() => handleViewLineage(record)}>
            血缘
          </Button>
          <Button size="small" icon={<BarChartOutlined />} onClick={() => handleViewValue(record)}>
            价值
          </Button>
          {!record.is_certified && (
            <Button size="small" type="primary" onClick={() => handleCertify(record.id)}>
              认证
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Row gutter={24}>
            <Col span={6}>
              <Statistic title="总资产数" value={assets.length} />
            </Col>
            <Col span={6}>
              <Statistic title="已认证" value={assets.filter((a) => a.is_certified).length} />
            </Col>
            <Col span={6}>
              <Statistic
                title="平均价值评分"
                value={
                  assets.filter((a) => a.value_score).length > 0
                    ? (
                        assets.reduce((sum, a) => sum + (a.value_score || 0), 0) /
                        assets.filter((a) => a.value_score).length
                      ).toFixed(1)
                    : '-'
                }
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总使用次数"
                value={assets.reduce((sum, a) => sum + a.usage_count, 0)}
              />
            </Col>
          </Row>
        </Card>

        <Card
          title={<Title level={4}>数据资产目录</Title>}
          extra={
            <Space>
              <Search
                placeholder="搜索资产..."
                allowClear
                style={{ width: 300 }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onSearch={handleSearch}
                enterButton={<SearchOutlined />}
              />
              <Button onClick={handleAISearch} type="dashed">
                AI 搜索
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleRefreshAllValues}>
                刷新价值评分
              </Button>
            </Space>
          }
        >
          <Table columns={columns} dataSource={assets} rowKey="id" loading={loading} />
        </Card>
      </Space>

      <Modal
        title="资产详情"
        open={!!selectedAsset && !lineageOpen}
        onCancel={() => setSelectedAsset(null)}
        footer={null}
        width={700}
      >
        {selectedAsset && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="名称" span={2}>
              {selectedAsset.name}
            </Descriptions.Item>
            <Descriptions.Item label="类型">{selectedAsset.asset_type}</Descriptions.Item>
            <Descriptions.Item label="访问级别">{selectedAsset.access_level}</Descriptions.Item>
            <Descriptions.Item label="领域">{selectedAsset.domain || '-'}</Descriptions.Item>
            <Descriptions.Item label="分类">{selectedAsset.category || '-'}</Descriptions.Item>
            <Descriptions.Item label="源表">{selectedAsset.source_table || '-'}</Descriptions.Item>
            <Descriptions.Item label="使用次数">{selectedAsset.usage_count}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>
              {selectedAsset.description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="AI 摘要" span={2}>
              {selectedAsset.ai_summary || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="标签" span={2}>
              {selectedAsset.tags?.map((t) => <Tag key={t}>{t}</Tag>) || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal
        title={
          <Space>
            {selectedAsset?.name}
            <Tag>{selectedAsset?.asset_type}</Tag>
          </Space>
        }
        open={lineageOpen}
        onCancel={() => {
          setLineageOpen(false);
          setLineageData(null);
          setValueEvaluation(null);
        }}
        footer={null}
        width={1000}
      >
        <Tabs
          activeKey={activeTab}
          onChange={async (key) => {
            setActiveTab(key);
            if (key === 'lineage' && selectedAsset && !lineageData) {
              await fetchLineage(selectedAsset.id, lineageDepth);
            }
            if (key === 'value' && selectedAsset && !valueEvaluation) {
              setValueLoading(true);
              try {
                const response = await assetsApi.getValue(selectedAsset.id);
                setValueEvaluation(response.data);
              } finally {
                setValueLoading(false);
              }
            }
          }}
          items={[
            {
              key: 'lineage',
              label: (
                <Space>
                  <BranchesOutlined />
                  数据血缘
                </Space>
              ),
              children: lineageLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                </div>
              ) : lineageData?.lineage_graph ? (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text>血缘深度: </Text>
                    <Slider
                      min={1}
                      max={3}
                      value={lineageDepth}
                      onChange={handleDepthChange}
                      style={{ width: 200, display: 'inline-block', marginLeft: 16 }}
                      marks={{ 1: '1层', 2: '2层', 3: '3层' }}
                    />
                  </div>
                  <LineageGraph data={lineageData.lineage_graph} />
                </div>
              ) : (
                <Text type="secondary">无血缘数据</Text>
              ),
            },
            {
              key: 'value',
              label: (
                <Space>
                  <BarChartOutlined />
                  价值评估
                </Space>
              ),
              children: valueLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                </div>
              ) : valueEvaluation ? (
                <ValueAssessment evaluation={valueEvaluation} />
              ) : (
                <Text type="secondary">加载价值评估...</Text>
              ),
            },
          ]}
        />
      </Modal>
    </AuthGuard>
  );
}
