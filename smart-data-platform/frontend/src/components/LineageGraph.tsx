'use client';

import { useMemo, useState, useCallback, useEffect, useRef } from 'react';
import {
  Card,
  Empty,
  Spin,
  Typography,
  Tooltip,
  Segmented,
  Space,
  Tag,
  Input,
  Select,
  Row,
  Col,
  Drawer,
  Descriptions,
  Divider,
  Badge,
  Button,
  Statistic,
  Alert,
  Switch,
} from 'antd';
import {
  ApartmentOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
  AimOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  NodeExpandOutlined,
  CompressOutlined,
} from '@ant-design/icons';
import { Graph, NodeEvent, GraphEvent } from '@antv/g6';

const { Text, Title } = Typography;
const { Search } = Input;

export interface LineageNode {
  id: string;
  type: string;
  name: string;
  description?: string;
  reference_id: string;
  reference_table: string;
  metadata?: Record<string, unknown>;
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  description?: string;
  transformation_details?: Record<string, unknown>;
}

export interface LineageGraphData {
  nodes: LineageNode[];
  edges: LineageEdge[];
  root_node_id?: string;
  depth?: number;
}

export interface LineageGraphProps {
  data: LineageGraphData;
  loading?: boolean;
  height?: number;
  onNodeClick?: (node: LineageNode) => void;
  onNodeSelect?: (node: LineageNode | null) => void;
  title?: string;
  showControls?: boolean;
  showSearch?: boolean;
  showFilter?: boolean;
  showNodeDetail?: boolean;
  onImpactAnalysis?: (nodeId: string) => Promise<ImpactAnalysisResult | null>;
}

interface ImpactAnalysisResult {
  impacted_assets: Array<{ id: string; name: string; type: string }>;
  impacted_pipelines: Array<{ id: string; name: string; type: string }>;
  impacted_tasks: Array<{ id: string; name: string; type: string }>;
  total_impacted: number;
}

const NODE_TYPE_COLORS: Record<string, string> = {
  data_source: '#1890ff',
  collect_task: '#52c41a',
  etl_pipeline: '#722ed1',
  data_asset: '#fa8c16',
  external: '#8c8c8c',
};

const NODE_TYPE_LABELS: Record<string, string> = {
  data_source: 'Data Source',
  collect_task: 'Collection Task',
  etl_pipeline: 'ETL Pipeline',
  data_asset: 'Data Asset',
  external: 'External',
};

const EDGE_TYPE_LABELS: Record<string, string> = {
  collects_from: 'Collects From',
  transforms: 'Transforms',
  produces: 'Produces',
  depends_on: 'Depends On',
};

const getConnectedNodes = (
  nodeId: string,
  edges: LineageEdge[],
  direction: 'upstream' | 'downstream' | 'both'
): string[] => {
  const connected: string[] = [];

  edges.forEach(edge => {
    if (direction === 'upstream' || direction === 'both') {
      if (edge.target === nodeId) {
        connected.push(edge.source);
      }
    }
    if (direction === 'downstream' || direction === 'both') {
      if (edge.source === nodeId) {
        connected.push(edge.target);
      }
    }
  });

  return connected;
};

const collectDownstreamIds = (
  startId: string,
  edges: LineageEdge[],
  visited: Set<string> = new Set()
): Set<string> => {
  if (visited.has(startId)) return visited;
  visited.add(startId);

  edges.forEach(edge => {
    if (edge.source === startId && !visited.has(edge.target)) {
      collectDownstreamIds(edge.target, edges, visited);
    }
  });

  return visited;
};

export default function LineageGraph({
  data,
  loading = false,
  height = 500,
  onNodeClick,
  onNodeSelect,
  title = 'Data Lineage',
  showControls = true,
  showSearch = true,
  showFilter = true,
  showNodeDetail = true,
  onImpactAnalysis,
}: LineageGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const isGraphDestroyedRef = useRef(false);

  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [filterTypes, setFilterTypes] = useState<string[]>([]);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [detailNode, setDetailNode] = useState<LineageNode | null>(null);
  const [impactMode, setImpactMode] = useState(false);
  const [impactNodeIds, setImpactNodeIds] = useState<Set<string>>(new Set());
  const [impactStats, setImpactStats] = useState<ImpactAnalysisResult | null>(null);
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [graphReady, setGraphReady] = useState(false);

  const graphHeight = isFullscreen ? window.innerHeight - 200 : height - 100;

  const availableTypes = useMemo(() => {
    const types = new Set(data.nodes.map(n => n.type));
    return Array.from(types);
  }, [data.nodes]);

  const filteredData = useMemo(() => {
    let filteredNodes = data.nodes;

    if (filterTypes.length > 0) {
      filteredNodes = filteredNodes.filter(n => filterTypes.includes(n.type));
    }

    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = data.edges.filter(
      e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    );

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
      root_node_id: data.root_node_id,
      depth: data.depth,
    };
  }, [data, filterTypes]);

  const matchedNodeIds = useMemo(() => {
    if (!searchKeyword.trim()) return new Set<string>();

    const keyword = searchKeyword.toLowerCase();
    return new Set(
      filteredData.nodes
        .filter(n =>
          n.name.toLowerCase().includes(keyword) ||
          n.description?.toLowerCase().includes(keyword)
        )
        .map(n => n.id)
    );
  }, [filteredData.nodes, searchKeyword]);

  const transformDataForG6 = useCallback(() => {
    const nodeMap = new Map(filteredData.nodes.map(n => [n.id, n]));

    const visibleNodeIds = new Set<string>();
    filteredData.nodes.forEach(n => {
      if (!collapsedNodes.has(n.id)) {
        visibleNodeIds.add(n.id);
      } else {
        visibleNodeIds.add(n.id);
      }
    });

    const hiddenByCollapse = new Set<string>();
    collapsedNodes.forEach(collapsedId => {
      const downstreamIds = collectDownstreamIds(collapsedId, filteredData.edges);
      downstreamIds.forEach(id => {
        if (id !== collapsedId) {
          hiddenByCollapse.add(id);
        }
      });
    });

    const finalVisibleIds = new Set(
      Array.from(visibleNodeIds).filter(id => !hiddenByCollapse.has(id))
    );

    const nodes = filteredData.nodes
      .filter(n => finalVisibleIds.has(n.id))
      .map(node => {
        const isRoot = node.id === filteredData.root_node_id;
        const isSelected = selectedNode === node.id;
        const isMatched = matchedNodeIds.has(node.id);
        const isImpacted = impactMode && impactNodeIds.has(node.id);
        const isCollapsed = collapsedNodes.has(node.id);
        const dimmed = searchKeyword.trim() && !isMatched;
        const hasChildren = filteredData.edges.some(e => e.source === node.id);

        const baseColor = NODE_TYPE_COLORS[node.type] || '#8c8c8c';

        return {
          id: node.id,
          data: {
            originalNode: node,
            label: node.name.length > 12 ? node.name.slice(0, 12) + '...' : node.name,
            fullLabel: node.name,
            nodeType: node.type,
            typeLabel: NODE_TYPE_LABELS[node.type] || node.type,
            isRoot,
            isSelected,
            isMatched,
            isImpacted,
            isCollapsed,
            hasChildren,
          },
          style: {
            fill: baseColor,
            stroke: isSelected
              ? '#1890ff'
              : isMatched
                ? '#faad14'
                : isImpacted
                  ? '#ff4d4f'
                  : isRoot
                    ? '#faad14'
                    : '#fff',
            lineWidth: isSelected || isMatched || isImpacted || isRoot ? 4 : 2,
            opacity: dimmed ? 0.4 : impactMode && !isImpacted && selectedNode !== node.id ? 0.3 : 1,
            cursor: 'pointer' as const,
            labelText: node.name.length > 12 ? node.name.slice(0, 12) + '...' : node.name,
            labelFill: '#fff',
            labelFontSize: 11,
            labelFontWeight: 'bold' as const,
            badges: isCollapsed && hasChildren
              ? [{ text: '+', position: 'right-bottom', fill: '#52c41a' }]
              : [],
          },
        };
      });

    const edges = filteredData.edges
      .filter(e => finalVisibleIds.has(e.source) && finalVisibleIds.has(e.target))
      .map(edge => {
        const isHighlighted = selectedNode &&
          (edge.source === selectedNode || edge.target === selectedNode);
        const isImpactPath = impactMode &&
          impactNodeIds.has(edge.source) &&
          impactNodeIds.has(edge.target);

        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          data: {
            originalEdge: edge,
            edgeType: edge.type,
            description: edge.description,
          },
          style: {
            stroke: isImpactPath
              ? '#ff4d4f'
              : isHighlighted
                ? '#1890ff'
                : '#8c8c8c',
            lineWidth: isImpactPath ? 3 : isHighlighted ? 2 : 1,
            opacity: impactMode && !isImpactPath ? 0.2 : 1,
            endArrow: true,
            endArrowSize: 8,
            labelText: EDGE_TYPE_LABELS[edge.type] || edge.type,
            labelFontSize: 10,
            labelFill: isHighlighted ? '#1890ff' : '#8c8c8c',
            labelBackground: true,
            labelBackgroundFill: '#fff',
            labelBackgroundOpacity: 0.8,
            labelBackgroundLineWidth: 0,
            labelBackgroundRadius: 2,
          },
        };
      });

    return { nodes, edges };
  }, [
    filteredData,
    selectedNode,
    matchedNodeIds,
    searchKeyword,
    impactMode,
    impactNodeIds,
    collapsedNodes,
  ]);

  useEffect(() => {
    if (viewMode !== 'graph' || !containerRef.current || !filteredData.nodes.length) {
      return;
    }

    const g6Data = transformDataForG6();

    if (!graphRef.current) {
      isGraphDestroyedRef.current = false;
      const graph = new Graph({
        container: containerRef.current,
        width: containerRef.current.clientWidth,
        height: graphHeight,
        autoFit: 'view',
        padding: [40, 40, 40, 40],
        layout: {
          type: 'dagre',
          rankdir: 'LR',
          nodesep: 50,
          ranksep: 80,
        },
        node: {
          type: 'circle',
          style: {
            size: 60,
          },
        },
        edge: {
          type: 'polyline',
          style: {
            radius: 10,
          },
        },
        behaviors: [
          'drag-canvas',
          'zoom-canvas',
          'drag-element',
          'click-select',
        ],
        plugins: [
          {
            type: 'minimap',
            key: 'minimap',
            position: 'right-bottom',
            size: [150, 100],
          },
          {
            type: 'tooltip',
            key: 'tooltip',
            getContent: (e: any, items: any[]) => {
              if (!items.length) return '';
              const item = items[0];
              if (item.data?.originalNode) {
                const node = item.data.originalNode;
                return `
                  <div style="padding: 8px; max-width: 200px;">
                    <div style="font-weight: bold;">${node.name}</div>
                    <div style="color: #8c8c8c; font-size: 12px;">${NODE_TYPE_LABELS[node.type] || node.type}</div>
                    ${node.description ? `<div style="margin-top: 4px; font-size: 12px;">${node.description}</div>` : ''}
                  </div>
                `;
              }
              return '';
            },
          },
        ],
        animation: true,
      });

      graph.on(NodeEvent.CLICK, (e: any) => {
        const nodeId = e.target?.id;
        if (nodeId) {
          const nodeData = filteredData.nodes.find(n => n.id === nodeId);
          if (nodeData) {
            handleNodeClickInternal(nodeData);
          }
        }
      });

      graph.on(NodeEvent.DBLCLICK, (e: any) => {
        const nodeId = e.target?.id;
        if (nodeId) {
          handleToggleCollapse(nodeId);
        }
      });

      graph.on(GraphEvent.AFTER_RENDER, () => {
        const zoom = graph.getZoom();
        setZoomLevel(Math.round(zoom * 100));
        setGraphReady(true);
      });

      graphRef.current = graph;
    }

    const graph = graphRef.current;
    try {
      graph.setData(g6Data);
      graph.render().then(() => setGraphReady(true)).catch((err: Error) => {
        console.error('Graph render error:', err);
        setGraphReady(false);
      });
    } catch (err) {
      console.error('Graph render error:', err);
      setGraphReady(false);
    }

    return () => {
      // Cleanup is handled by the separate unmount effect
      // This prevents issues with React Fast Refresh
    };
  }, [viewMode, filteredData.nodes.length, graphHeight]);

  useEffect(() => {
    if (graphRef.current && viewMode === 'graph' && graphReady && !isGraphDestroyedRef.current) {
      const g6Data = transformDataForG6();
      // Check if graph is still valid before drawing (handles Fast Refresh)
      try {
        graphRef.current.setData(g6Data);
        graphRef.current.draw().catch((err: Error) => {
          console.error('Graph draw error:', err);
        });
      } catch (error) {
        console.warn('Graph instance invalid, skipping draw:', error);
      }
    }
  }, [
    transformDataForG6,
    viewMode,
    selectedNode,
    searchKeyword,
    impactMode,
    impactNodeIds,
    collapsedNodes,
    graphReady,
  ]);

  useEffect(() => {
    if (graphRef.current && containerRef.current && !isGraphDestroyedRef.current) {
      graphRef.current.setSize(containerRef.current.clientWidth, graphHeight);
    }
  }, [graphHeight, isFullscreen]);

  useEffect(() => {
    return () => {
      isGraphDestroyedRef.current = true;
      if (graphRef.current) {
        try {
          graphRef.current.destroy();
        } catch (error) {
          console.warn('Graph destroy warning:', error);
        } finally {
          graphRef.current = null;
          setGraphReady(false);
        }
      }
    };
  }, []);

  const handleNodeClickInternal = useCallback((node: LineageNode) => {
    const newSelectedId = node.id === selectedNode ? null : node.id;
    setSelectedNode(newSelectedId);
    onNodeClick?.(node);

    if (showNodeDetail && newSelectedId) {
      setDetailNode(node);
      setDetailDrawerOpen(true);
      onNodeSelect?.(node);
    } else {
      setDetailDrawerOpen(false);
      onNodeSelect?.(null);
    }
  }, [selectedNode, onNodeClick, onNodeSelect, showNodeDetail]);

  const handleCloseDetail = useCallback(() => {
    setDetailDrawerOpen(false);
    setDetailNode(null);
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  const handleToggleCollapse = useCallback((nodeId: string) => {
    setCollapsedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const handleImpactAnalysis = useCallback(async (nodeId: string) => {
    if (!onImpactAnalysis) {
      const downstreamIds = collectDownstreamIds(nodeId, filteredData.edges);
      setImpactNodeIds(downstreamIds);
      setImpactMode(true);
      setImpactStats({
        impacted_assets: [],
        impacted_pipelines: [],
        impacted_tasks: [],
        total_impacted: downstreamIds.size - 1,
      });
      return;
    }

    const result = await onImpactAnalysis(nodeId);
    if (result) {
      const impactedIds = new Set<string>([nodeId]);
      result.impacted_assets.forEach(a => impactedIds.add(a.id));
      result.impacted_pipelines.forEach(p => impactedIds.add(p.id));
      result.impacted_tasks.forEach(t => impactedIds.add(t.id));
      setImpactNodeIds(impactedIds);
      setImpactStats(result);
      setImpactMode(true);
    }
  }, [onImpactAnalysis, filteredData.edges]);

  const handleExitImpactMode = useCallback(() => {
    setImpactMode(false);
    setImpactNodeIds(new Set());
    setImpactStats(null);
  }, []);

  const handleZoomIn = useCallback(() => {
    if (graphRef.current && !isGraphDestroyedRef.current) {
      const currentZoom = graphRef.current.getZoom();
      graphRef.current.zoomTo(Math.min(currentZoom * 1.2, 3));
      setZoomLevel(Math.round(graphRef.current.getZoom() * 100));
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (graphRef.current && !isGraphDestroyedRef.current) {
      const currentZoom = graphRef.current.getZoom();
      graphRef.current.zoomTo(Math.max(currentZoom / 1.2, 0.3));
      setZoomLevel(Math.round(graphRef.current.getZoom() * 100));
    }
  }, []);

  const handleReset = useCallback(() => {
    if (graphRef.current && !isGraphDestroyedRef.current) {
      graphRef.current.fitView();
      setZoomLevel(100);
    }
  }, []);

  const handleFocusNode = useCallback((nodeId: string) => {
    if (graphRef.current && !isGraphDestroyedRef.current) {
      graphRef.current.focusElement(nodeId);
    }
  }, []);

  const handleSearch = (value: string) => {
    setSearchKeyword(value);
    if (value.trim() && graphRef.current && !isGraphDestroyedRef.current) {
      const matchedNodes = filteredData.nodes.filter(n =>
        n.name.toLowerCase().includes(value.toLowerCase()) ||
        n.description?.toLowerCase().includes(value.toLowerCase())
      );
      if (matchedNodes.length > 0) {
        handleFocusNode(matchedNodes[0].id);
      }
    }
  };

  const handleFilterChange = (types: string[]) => {
    setFilterTypes(types);
  };

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            Loading lineage data...
          </Text>
        </div>
      </Card>
    );
  }

  if (!data.nodes.length) {
    return (
      <Card title={title}>
        <Empty
          image={<ApartmentOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
          description="No lineage data available"
        />
      </Card>
    );
  }

  const renderSearchAndFilter = () => (
    <Row gutter={16} style={{ marginBottom: 16 }}>
      {showSearch && (
        <Col span={12}>
          <Search
            placeholder="Search nodes by name..."
            prefix={<SearchOutlined />}
            allowClear
            value={searchKeyword}
            onChange={e => handleSearch(e.target.value)}
            style={{ width: '100%' }}
          />
        </Col>
      )}
      {showFilter && (
        <Col span={12}>
          <Select
            mode="multiple"
            placeholder="Filter by type..."
            value={filterTypes}
            onChange={handleFilterChange}
            style={{ width: '100%' }}
            allowClear
            suffixIcon={<FilterOutlined />}
            options={availableTypes.map(type => ({
              value: type,
              label: (
                <Space>
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: NODE_TYPE_COLORS[type] || '#8c8c8c',
                    }}
                  />
                  {NODE_TYPE_LABELS[type] || type}
                </Space>
              ),
            }))}
          />
        </Col>
      )}
    </Row>
  );

  const renderImpactPanel = () => {
    if (!impactMode || !impactStats) return null;

    return (
      <Alert
        type="warning"
        showIcon
        icon={<AimOutlined />}
        message={
          <Space>
            <span>Impact Analysis Mode</span>
            <Tag color="red">{impactStats.total_impacted} items impacted</Tag>
          </Space>
        }
        description={
          <Row gutter={16} style={{ marginTop: 8 }}>
            <Col span={8}>
              <Statistic
                title="Impacted Assets"
                value={impactStats.impacted_assets.length}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Impacted Pipelines"
                value={impactStats.impacted_pipelines.length}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Impacted Tasks"
                value={impactStats.impacted_tasks.length}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
          </Row>
        }
        action={
          <Button size="small" onClick={handleExitImpactMode}>
            Exit Impact Mode
          </Button>
        }
        style={{ marginBottom: 16 }}
      />
    );
  };

  const renderGraph = () => (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: graphHeight,
        background: '#fafafa',
        borderRadius: 8,
        position: 'relative',
      }}
    />
  );

  const renderList = () => (
    <div style={{ maxHeight: graphHeight, overflow: 'auto' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {filteredData.nodes.map(node => {
          const isMatched = matchedNodeIds.has(node.id);
          const dimmed = searchKeyword.trim() && !isMatched;
          const isImpacted = impactMode && impactNodeIds.has(node.id);

          return (
            <Card
              key={node.id}
              size="small"
              hoverable
              onClick={() => handleNodeClickInternal(node)}
              style={{
                borderLeft: `4px solid ${isImpacted ? '#ff4d4f' : NODE_TYPE_COLORS[node.type] || '#8c8c8c'}`,
                background: selectedNode === node.id
                  ? '#e6f7ff'
                  : isMatched
                    ? '#fffbe6'
                    : isImpacted
                      ? '#fff1f0'
                      : undefined,
                opacity: dimmed ? 0.5 : 1,
              }}
            >
              <Space direction="vertical" size={2}>
                <Space>
                  <Text strong>{node.name}</Text>
                  <Tag color={NODE_TYPE_COLORS[node.type]}>
                    {NODE_TYPE_LABELS[node.type] || node.type}
                  </Tag>
                  {node.id === filteredData.root_node_id && (
                    <Tag color="gold">Root</Tag>
                  )}
                  {isMatched && <Tag color="orange">Match</Tag>}
                  {isImpacted && <Tag color="red">Impacted</Tag>}
                </Space>
                {node.description && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {node.description}
                  </Text>
                )}
              </Space>
            </Card>
          );
        })}
      </Space>
    </div>
  );

  const renderNodeDetail = () => {
    if (!detailNode) return null;

    const upstreamNodes = getConnectedNodes(detailNode.id, filteredData.edges, 'upstream');
    const downstreamNodes = getConnectedNodes(detailNode.id, filteredData.edges, 'downstream');
    const nodeMap = new Map(filteredData.nodes.map(n => [n.id, n]));

    return (
      <Drawer
        title={
          <Space>
            <div
              style={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                background: NODE_TYPE_COLORS[detailNode.type] || '#8c8c8c',
              }}
            />
            <span>{detailNode.name}</span>
          </Space>
        }
        placement="right"
        width={400}
        open={detailDrawerOpen}
        onClose={handleCloseDetail}
        extra={
          <Space>
            <Tooltip title="Impact Analysis">
              <Button
                type="text"
                icon={<AimOutlined />}
                onClick={() => handleImpactAnalysis(detailNode.id)}
              />
            </Tooltip>
            <Tag color={NODE_TYPE_COLORS[detailNode.type]}>
              {NODE_TYPE_LABELS[detailNode.type] || detailNode.type}
            </Tag>
          </Space>
        }
      >
        <Descriptions column={1} size="small">
          <Descriptions.Item label="ID">{detailNode.id}</Descriptions.Item>
          <Descriptions.Item label="Type">
            {NODE_TYPE_LABELS[detailNode.type] || detailNode.type}
          </Descriptions.Item>
          <Descriptions.Item label="Reference ID">
            {detailNode.reference_id}
          </Descriptions.Item>
          <Descriptions.Item label="Reference Table">
            {detailNode.reference_table}
          </Descriptions.Item>
          {detailNode.description && (
            <Descriptions.Item label="Description">
              {detailNode.description}
            </Descriptions.Item>
          )}
        </Descriptions>

        {detailNode.metadata && Object.keys(detailNode.metadata).length > 0 && (
          <>
            <Divider orientation="left" style={{ fontSize: 12 }}>
              Metadata
            </Divider>
            <Descriptions column={1} size="small">
              {Object.entries(detailNode.metadata).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        )}

        <Divider orientation="left" style={{ fontSize: 12 }}>
          <Badge count={upstreamNodes.length} size="small" offset={[8, 0]}>
            Upstream Nodes
          </Badge>
        </Divider>
        {upstreamNodes.length > 0 ? (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {upstreamNodes.map(nodeId => {
              const node = nodeMap.get(nodeId);
              if (!node) return null;
              return (
                <Card
                  key={nodeId}
                  size="small"
                  hoverable
                  onClick={() => {
                    handleCloseDetail();
                    handleNodeClickInternal(node);
                    handleFocusNode(node.id);
                  }}
                  style={{
                    borderLeft: `3px solid ${NODE_TYPE_COLORS[node.type] || '#8c8c8c'}`,
                  }}
                >
                  <Space>
                    <Text strong>{node.name}</Text>
                    <Tag color={NODE_TYPE_COLORS[node.type]} style={{ margin: 0 }}>
                      {NODE_TYPE_LABELS[node.type] || node.type}
                    </Tag>
                  </Space>
                </Card>
              );
            })}
          </Space>
        ) : (
          <Text type="secondary">No upstream nodes</Text>
        )}

        <Divider orientation="left" style={{ fontSize: 12 }}>
          <Badge count={downstreamNodes.length} size="small" offset={[8, 0]}>
            Downstream Nodes
          </Badge>
        </Divider>
        {downstreamNodes.length > 0 ? (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {downstreamNodes.map(nodeId => {
              const node = nodeMap.get(nodeId);
              if (!node) return null;
              return (
                <Card
                  key={nodeId}
                  size="small"
                  hoverable
                  onClick={() => {
                    handleCloseDetail();
                    handleNodeClickInternal(node);
                    handleFocusNode(node.id);
                  }}
                  style={{
                    borderLeft: `3px solid ${NODE_TYPE_COLORS[node.type] || '#8c8c8c'}`,
                  }}
                >
                  <Space>
                    <Text strong>{node.name}</Text>
                    <Tag color={NODE_TYPE_COLORS[node.type]} style={{ margin: 0 }}>
                      {NODE_TYPE_LABELS[node.type] || node.type}
                    </Tag>
                  </Space>
                </Card>
              );
            })}
          </Space>
        ) : (
          <Text type="secondary">No downstream nodes</Text>
        )}

        <Divider />
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button
            block
            icon={<AimOutlined />}
            onClick={() => handleImpactAnalysis(detailNode.id)}
          >
            Analyze Impact
          </Button>
          <Button
            block
            icon={collapsedNodes.has(detailNode.id) ? <NodeExpandOutlined /> : <CompressOutlined />}
            onClick={() => handleToggleCollapse(detailNode.id)}
          >
            {collapsedNodes.has(detailNode.id) ? 'Expand Children' : 'Collapse Children'}
          </Button>
        </Space>
      </Drawer>
    );
  };

  return (
    <Card
      title={
        <Space>
          <ApartmentOutlined />
          <span>{title}</span>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
            ({filteredData.nodes.length} nodes, {filteredData.edges.length} edges)
          </Text>
          {searchKeyword && matchedNodeIds.size > 0 && (
            <Tag color="orange">{matchedNodeIds.size} matches</Tag>
          )}
          {impactMode && (
            <Tag color="red">Impact Mode</Tag>
          )}
        </Space>
      }
      extra={
        showControls && (
          <Space>
            <Segmented
              value={viewMode}
              onChange={(v) => setViewMode(v as 'graph' | 'list')}
              options={[
                { value: 'graph', label: 'Graph' },
                { value: 'list', label: 'List' },
              ]}
              size="small"
            />
            {viewMode === 'graph' && (
              <>
                <Tooltip title="Zoom Out">
                  <ZoomOutOutlined onClick={handleZoomOut} style={{ cursor: 'pointer' }} />
                </Tooltip>
                <Text type="secondary">{zoomLevel}%</Text>
                <Tooltip title="Zoom In">
                  <ZoomInOutlined onClick={handleZoomIn} style={{ cursor: 'pointer' }} />
                </Tooltip>
                <Tooltip title="Fit View">
                  <ReloadOutlined onClick={handleReset} style={{ cursor: 'pointer' }} />
                </Tooltip>
                <Tooltip title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}>
                  {isFullscreen ? (
                    <FullscreenExitOutlined
                      onClick={() => setIsFullscreen(false)}
                      style={{ cursor: 'pointer' }}
                    />
                  ) : (
                    <FullscreenOutlined
                      onClick={() => setIsFullscreen(true)}
                      style={{ cursor: 'pointer' }}
                    />
                  )}
                </Tooltip>
              </>
            )}
          </Space>
        )
      }
      style={isFullscreen ? { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000 } : undefined}
    >
      {(showSearch || showFilter) && renderSearchAndFilter()}
      {renderImpactPanel()}

      {viewMode === 'graph' ? renderGraph() : renderList()}

      {/* Legend */}
      <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
        {Object.entries(NODE_TYPE_COLORS).map(([type, color]) => (
          <Space key={type} size={4}>
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: color,
              }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {NODE_TYPE_LABELS[type]}
            </Text>
          </Space>
        ))}
        <Divider type="vertical" />
        <Text type="secondary" style={{ fontSize: 12 }}>
          Double-click to expand/collapse
        </Text>
      </div>

      {showNodeDetail && renderNodeDetail()}
    </Card>
  );
}
