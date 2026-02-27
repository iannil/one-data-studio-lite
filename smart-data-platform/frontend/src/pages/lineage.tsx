'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Space,
  Typography,
  Button,
  Select,
  Row,
  Col,
  Spin,
  Empty,
  Tabs,
  Alert,
  Modal,
  Table,
  Tag,
  Slider,
  Tooltip,
  Progress,
  Descriptions,
  Badge,
  App,
} from 'antd';
import {
  ApartmentOutlined,
  ReloadOutlined,
  BuildOutlined,
  NodeIndexOutlined,
  RadarChartOutlined,
  CheckOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import LineageGraph from '@/components/LineageGraph';
import { lineageApi, assetsApi } from '@/services/api';

const { Title, Text } = Typography;

interface Asset {
  id: string;
  name: string;
  description?: string;
  asset_type: string;
}

interface LineageGraphData {
  nodes: Array<{
    id: string;
    type: string;
    name: string;
    description?: string;
    reference_id: string;
    reference_table: string;
    metadata?: Record<string, unknown>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
    description?: string;
    transformation_details?: Record<string, unknown>;
  }>;
  root_node_id?: string;
  depth?: number;
}

interface RelationColumn {
  source_id: string;
  source_name: string;
  table_name: string;
  column_name: string;
}

interface DiscoveredRelation {
  source_column: RelationColumn;
  target_column: RelationColumn;
  confidence: number;
  relation_type: string;
  reason: string;
}

interface DiscoverRelationsResponse {
  relations: DiscoveredRelation[];
  summary: string;
  recommendations: string[];
  sources_analyzed: number;
  columns_analyzed: number;
}

export default function LineagePage() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [buildLoading, setBuildLoading] = useState(false);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<LineageGraphData | null>(null);
  const [globalGraphData, setGlobalGraphData] = useState<LineageGraphData | null>(null);
  const [direction, setDirection] = useState<'both' | 'upstream' | 'downstream'>('both');
  const [depth, setDepth] = useState(3);
  const [activeTab, setActiveTab] = useState('global');

  const [discoverModalOpen, setDiscoverModalOpen] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverResult, setDiscoverResult] = useState<DiscoverRelationsResponse | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.7);
  const [selectedRelations, setSelectedRelations] = useState<Set<number>>(new Set());

  const fetchAssets = useCallback(async () => {
    try {
      const response = await assetsApi.list({ limit: 100 });
      setAssets(response.data);
    } catch (error) {
      message.error('加载资产列表失败');
    }
  }, []);

  const fetchGlobalGraph = useCallback(async () => {
    setLoading(true);
    try {
      const response = await lineageApi.getGlobalGraph(undefined, 100);
      setGlobalGraphData(response.data);
    } catch (error) {
      message.error('加载全局血缘图失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAssetLineage = useCallback(async (assetId: string) => {
    setLoading(true);
    try {
      const response = await lineageApi.getAssetLineage(assetId, direction, depth);
      setGraphData(response.data);
    } catch (error) {
      message.error('加载资产血缘失败');
    } finally {
      setLoading(false);
    }
  }, [direction, depth]);

  const handleBuildLineage = async (rebuildAll = false) => {
    setBuildLoading(true);
    try {
      const response = await lineageApi.buildLineage({ rebuild_all: rebuildAll });
      message.success(
        `血缘构建完成：创建 ${response.data.nodes_created} 个节点，${response.data.edges_created} 条边`
      );
      if (activeTab === 'global') {
        await fetchGlobalGraph();
      } else if (selectedAssetId) {
        await fetchAssetLineage(selectedAssetId);
      }
    } catch (error) {
      message.error('构建血缘失败');
    } finally {
      setBuildLoading(false);
    }
  };

  const handleRefresh = useCallback(() => {
    if (activeTab === 'global') {
      fetchGlobalGraph();
    } else if (selectedAssetId) {
      fetchAssetLineage(selectedAssetId);
    }
    fetchAssets();
  }, [activeTab, selectedAssetId, fetchGlobalGraph, fetchAssetLineage, fetchAssets]);

  useEffect(() => {
    fetchAssets();
    fetchGlobalGraph();
  }, [fetchAssets, fetchGlobalGraph]);

  useEffect(() => {
    if (selectedAssetId && activeTab === 'asset') {
      fetchAssetLineage(selectedAssetId);
    }
  }, [selectedAssetId, activeTab, fetchAssetLineage]);

  const handleNodeClick = (node: LineageGraphData['nodes'][0]) => {
    if (node.reference_table === 'data_assets') {
      setSelectedAssetId(node.reference_id);
      setActiveTab('asset');
    }
  };

  const handleDiscoverRelations = async () => {
    setDiscoverLoading(true);
    setDiscoverResult(null);
    setSelectedRelations(new Set());

    try {
      const response = await lineageApi.discoverRelations({
        confidence_threshold: confidenceThreshold,
      });
      setDiscoverResult(response.data);

      if (response.data.relations.length === 0) {
        message.info('未发现符合条件的跨源关联');
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发现关联失败');
    } finally {
      setDiscoverLoading(false);
    }
  };

  const handleOpenDiscoverModal = () => {
    setDiscoverModalOpen(true);
    setDiscoverResult(null);
    setSelectedRelations(new Set());
  };

  const handleConfirmRelations = async () => {
    if (selectedRelations.size === 0) {
      message.warning('请先选择要确认的关联');
      return;
    }

    message.success(`已确认 ${selectedRelations.size} 条关联关系`);
    setDiscoverModalOpen(false);
    handleBuildLineage(false);
  };

  const toggleRelationSelection = (index: number) => {
    const newSelected = new Set(selectedRelations);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedRelations(newSelected);
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return '#52c41a';
    if (confidence >= 0.8) return '#73d13d';
    if (confidence >= 0.7) return '#faad14';
    return '#ff7a45';
  };

  const getRelationTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      foreign_key: 'blue',
      join_key: 'green',
      semantic_link: 'purple',
      potential_join: 'orange',
    };
    return colors[type] || 'default';
  };

  const relationColumns: ColumnsType<DiscoveredRelation & { index: number }> = [
    {
      title: '源列',
      key: 'source',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.source_column.column_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.source_column.source_name}.{record.source_column.table_name}
          </Text>
        </Space>
      ),
    },
    {
      title: '',
      key: 'arrow',
      width: 50,
      render: () => <LinkOutlined style={{ color: '#1890ff' }} />,
    },
    {
      title: '目标列',
      key: 'target',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.target_column.column_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.target_column.source_name}.{record.target_column.table_name}
          </Text>
        </Space>
      ),
    },
    {
      title: '置信度',
      key: 'confidence',
      width: 120,
      render: (_, record) => (
        <Progress
          percent={Math.round(record.confidence * 100)}
          size="small"
          strokeColor={getConfidenceColor(record.confidence)}
          format={(p) => `${p}%`}
        />
      ),
      sorter: (a, b) => a.confidence - b.confidence,
      defaultSortOrder: 'descend',
    },
    {
      title: '关联类型',
      key: 'type',
      width: 120,
      render: (_, record) => (
        <Tag color={getRelationTypeColor(record.relation_type)}>
          {record.relation_type}
        </Tag>
      ),
    },
    {
      title: '原因',
      key: 'reason',
      ellipsis: true,
      render: (_, record) => (
        <Tooltip title={record.reason}>
          <Text style={{ cursor: 'pointer' }}>{record.reason}</Text>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, record) => {
        const isSelected = selectedRelations.has(record.index);
        return (
          <Space>
            <Tooltip title={isSelected ? '取消选择' : '选择确认'}>
              <Button
                type={isSelected ? 'primary' : 'default'}
                icon={isSelected ? <CheckOutlined /> : <CheckOutlined />}
                size="small"
                onClick={() => toggleRelationSelection(record.index)}
              />
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  const renderDiscoverModal = () => (
    <Modal
      title={
        <Space>
          <RadarChartOutlined />
          <span>发现跨源关联</span>
        </Space>
      }
      open={discoverModalOpen}
      onCancel={() => setDiscoverModalOpen(false)}
      width={1000}
      footer={[
        <Button key="cancel" onClick={() => setDiscoverModalOpen(false)}>
          关闭
        </Button>,
        <Button
          key="confirm"
          type="primary"
          disabled={selectedRelations.size === 0}
          onClick={handleConfirmRelations}
        >
          确认选中 ({selectedRelations.size})
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Card size="small">
          <Row gutter={16} align="middle">
            <Col span={16}>
              <Space>
                <Text>置信度阈值：</Text>
                <Slider
                  style={{ width: 200 }}
                  min={0.5}
                  max={1}
                  step={0.05}
                  value={confidenceThreshold}
                  onChange={setConfidenceThreshold}
                  marks={{ 0.5: '50%', 0.7: '70%', 0.9: '90%', 1: '100%' }}
                />
                <Text type="secondary">{Math.round(confidenceThreshold * 100)}%</Text>
              </Space>
            </Col>
            <Col span={8} style={{ textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<RadarChartOutlined />}
                onClick={handleDiscoverRelations}
                loading={discoverLoading}
              >
                开始发现
              </Button>
            </Col>
          </Row>
        </Card>

        {discoverLoading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
              正在分析列名、类型和元数据以发现潜在关联...
            </Text>
          </div>
        )}

        {discoverResult && !discoverLoading && (
          <>
            <Alert
              message={discoverResult.summary}
              description={
                <Space direction="vertical">
                  <Text>
                    分析了 {discoverResult.sources_analyzed} 个数据源，
                    {discoverResult.columns_analyzed} 个列
                  </Text>
                  {discoverResult.recommendations.length > 0 && (
                    <div>
                      <Text strong>建议：</Text>
                      <ul style={{ margin: '4px 0 0 20px', paddingLeft: 0 }}>
                        {discoverResult.recommendations.map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Space>
              }
              type="info"
              showIcon
              icon={<InfoCircleOutlined />}
            />

            {discoverResult.relations.length > 0 ? (
              <Table
                columns={relationColumns}
                dataSource={discoverResult.relations.map((r, idx) => ({
                  ...r,
                  index: idx,
                }))}
                rowKey={(record) => `${record.index}`}
                size="small"
                pagination={{ pageSize: 10 }}
                rowClassName={(record) =>
                  selectedRelations.has(record.index) ? 'ant-table-row-selected' : ''
                }
              />
            ) : (
              <Empty description="未发现符合条件的跨源关联" />
            )}
          </>
        )}

        {!discoverResult && !discoverLoading && (
          <Empty
            description={
              <Space direction="vertical">
                <Text>点击「开始发现」分析跨数据源的潜在关联关系</Text>
                <Text type="secondary">
                  系统将比较列名、数据类型、主键/外键信息，并使用 AI 推断关联关系
                </Text>
              </Space>
            }
          />
        )}
      </Space>
    </Modal>
  );

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <ApartmentOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                <Title level={4} style={{ margin: 0 }}>
                  数据血缘
                </Title>
              </Space>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<RadarChartOutlined />}
                  onClick={handleOpenDiscoverModal}
                >
                  发现关联
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleRefresh}
                  loading={loading}
                >
                  刷新
                </Button>
                <Button
                  icon={<BuildOutlined />}
                  onClick={() => handleBuildLineage(false)}
                  loading={buildLoading}
                >
                  构建血缘
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => handleBuildLineage(true)}
                  loading={buildLoading}
                  danger
                >
                  重建全部
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>

        <Alert
          message="数据血缘追踪"
          description="可视化展示数据在平台中的流转路径 - 从数据源、采集任务、ETL 管道到最终的数据资产。点击节点可查看详细血缘。使用「发现关联」功能可以自动发现跨数据源的潜在关联关系。"
          type="info"
          showIcon
          icon={<NodeIndexOutlined />}
        />

        <Card>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'global',
                label: '全局血缘',
                children: (
                  <Spin spinning={loading}>
                    {globalGraphData && globalGraphData.nodes.length > 0 ? (
                      <LineageGraph
                        data={globalGraphData}
                        height={600}
                        title="全局数据血缘图"
                        onNodeClick={handleNodeClick}
                        showSearch
                        showFilter
                        showNodeDetail
                        onImpactAnalysis={async (nodeId) => {
                          try {
                            const node = globalGraphData.nodes.find(n => n.id === nodeId);
                            if (node?.reference_table === 'data_assets') {
                              const response = await lineageApi.impactAnalysis(node.reference_id);
                              return response.data;
                            }
                            return null;
                          } catch (error) {
                            message.error('影响分析失败');
                            return null;
                          }
                        }}
                      />
                    ) : (
                      <Empty
                        description={
                          <Space direction="vertical">
                            <Text>暂无血缘数据</Text>
                            <Text type="secondary">
                              点击「构建血缘」从数据源、管道和资产生成血缘图
                            </Text>
                          </Space>
                        }
                      >
                        <Button
                          type="primary"
                          icon={<BuildOutlined />}
                          onClick={() => handleBuildLineage(false)}
                          loading={buildLoading}
                        >
                          立即构建血缘
                        </Button>
                      </Empty>
                    )}
                  </Spin>
                ),
              },
              {
                key: 'asset',
                label: '资产血缘',
                children: (
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Select
                          style={{ width: '100%' }}
                          placeholder="选择资产"
                          value={selectedAssetId}
                          onChange={setSelectedAssetId}
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                          }
                          options={assets.map((a) => ({
                            value: a.id,
                            label: a.name,
                          }))}
                        />
                      </Col>
                      <Col span={6}>
                        <Select
                          style={{ width: '100%' }}
                          value={direction}
                          onChange={setDirection}
                          options={[
                            { value: 'both', label: '双向' },
                            { value: 'upstream', label: '仅上游' },
                            { value: 'downstream', label: '仅下游' },
                          ]}
                        />
                      </Col>
                      <Col span={4}>
                        <Select
                          style={{ width: '100%' }}
                          value={depth}
                          onChange={setDepth}
                          options={[
                            { value: 1, label: '深度: 1' },
                            { value: 2, label: '深度: 2' },
                            { value: 3, label: '深度: 3' },
                            { value: 5, label: '深度: 5' },
                            { value: 10, label: '深度: 10' },
                          ]}
                        />
                      </Col>
                      <Col>
                        <Button
                          icon={<ReloadOutlined />}
                          onClick={() => selectedAssetId && fetchAssetLineage(selectedAssetId)}
                          disabled={!selectedAssetId}
                        >
                          刷新
                        </Button>
                      </Col>
                    </Row>

                    <Spin spinning={loading}>
                      {selectedAssetId && graphData && graphData.nodes.length > 0 ? (
                        <LineageGraph
                          data={graphData}
                          height={500}
                          title={`${assets.find(a => a.id === selectedAssetId)?.name || '所选资产'} 的血缘图`}
                          onNodeClick={handleNodeClick}
                          showSearch
                          showFilter
                          showNodeDetail
                          onImpactAnalysis={async (nodeId) => {
                            try {
                              const node = graphData.nodes.find(n => n.id === nodeId);
                              if (node?.reference_table === 'data_assets') {
                                const response = await lineageApi.impactAnalysis(node.reference_id);
                                return response.data;
                              }
                              return null;
                            } catch (error) {
                              message.error('影响分析失败');
                              return null;
                            }
                          }}
                        />
                      ) : (
                        <Empty
                          description={
                            selectedAssetId
                              ? '该资产暂无血缘数据'
                              : '请选择资产以查看其血缘'
                          }
                        />
                      )}
                    </Spin>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Space>

      {renderDiscoverModal()}
    </AuthGuard>
  );
}
