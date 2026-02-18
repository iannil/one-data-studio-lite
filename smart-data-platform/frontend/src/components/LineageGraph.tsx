'use client';

import { useMemo, useState, useCallback } from 'react';
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
} from 'antd';
import {
  ApartmentOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  CloseOutlined,
} from '@ant-design/icons';

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

interface NodePosition {
  x: number;
  y: number;
}

const calculateNodePositions = (
  nodes: LineageNode[],
  edges: LineageEdge[],
  width: number,
  height: number,
  rootNodeId?: string
): Map<string, NodePosition> => {
  const positions = new Map<string, NodePosition>();
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  const adjacencyList = new Map<string, string[]>();
  const reverseAdjacencyList = new Map<string, string[]>();

  nodes.forEach(n => {
    adjacencyList.set(n.id, []);
    reverseAdjacencyList.set(n.id, []);
  });

  edges.forEach(e => {
    if (adjacencyList.has(e.source) && adjacencyList.has(e.target)) {
      adjacencyList.get(e.source)?.push(e.target);
      reverseAdjacencyList.get(e.target)?.push(e.source);
    }
  });

  const levels = new Map<string, number>();
  const visited = new Set<string>();

  const assignLevel = (nodeId: string, level: number): void => {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);

    const currentLevel = levels.get(nodeId) ?? -1;
    levels.set(nodeId, Math.max(currentLevel, level));

    adjacencyList.get(nodeId)?.forEach(targetId => {
      assignLevel(targetId, level + 1);
    });
  };

  const rootNodes = nodes.filter(n => {
    const incoming = reverseAdjacencyList.get(n.id) ?? [];
    return incoming.length === 0;
  });

  if (rootNodes.length === 0 && rootNodeId && nodeMap.has(rootNodeId)) {
    assignLevel(rootNodeId, 0);
  } else {
    rootNodes.forEach((n) => assignLevel(n.id, 0));
  }

  nodes.forEach(n => {
    if (!levels.has(n.id)) {
      levels.set(n.id, 0);
    }
  });

  const levelGroups = new Map<number, string[]>();
  levels.forEach((level, nodeId) => {
    if (!levelGroups.has(level)) {
      levelGroups.set(level, []);
    }
    levelGroups.get(level)!.push(nodeId);
  });

  const maxLevel = Math.max(...Array.from(levels.values()), 0);
  const levelWidth = width / (maxLevel + 2);

  levelGroups.forEach((nodeIds, level) => {
    const levelHeight = height / (nodeIds.length + 1);
    nodeIds.forEach((nodeId, index) => {
      positions.set(nodeId, {
        x: levelWidth * (level + 1),
        y: levelHeight * (index + 1),
      });
    });
  });

  return positions;
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
}: LineageGraphProps) {
  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [filterTypes, setFilterTypes] = useState<string[]>([]);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [detailNode, setDetailNode] = useState<LineageNode | null>(null);

  const svgWidth = 800;
  const svgHeight = height - 100;

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

  const nodePositions = useMemo(() => {
    if (!filteredData.nodes.length) return new Map<string, NodePosition>();
    return calculateNodePositions(
      filteredData.nodes,
      filteredData.edges,
      svgWidth,
      svgHeight,
      filteredData.root_node_id
    );
  }, [filteredData.nodes, filteredData.edges, filteredData.root_node_id, svgWidth, svgHeight]);

  const handleNodeClick = useCallback((node: LineageNode) => {
    const newSelectedId = node.id === selectedNode ? null : node.id;
    setSelectedNode(newSelectedId);
    onNodeClick?.(node);

    if (showNodeDetail && newSelectedId) {
      setDetailNode(node);
      setDetailDrawerOpen(true);
      onNodeSelect?.(node);
    } else {
      onNodeSelect?.(null);
    }
  }, [selectedNode, onNodeClick, onNodeSelect, showNodeDetail]);

  const handleCloseDetail = useCallback(() => {
    setDetailDrawerOpen(false);
    setDetailNode(null);
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.2, 2));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5));
  const handleReset = () => setZoom(1);

  const handleSearch = (value: string) => {
    setSearchKeyword(value);
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

  const renderGraph = () => (
    <svg
      width="100%"
      height={svgHeight}
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      style={{ background: '#fafafa', borderRadius: 8 }}
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#8c8c8c" />
        </marker>
        <marker
          id="arrowhead-highlight"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#1890ff" />
        </marker>
      </defs>

      <g transform={`scale(${zoom})`}>
        {filteredData.edges.map(edge => {
          const sourcePos = nodePositions.get(edge.source);
          const targetPos = nodePositions.get(edge.target);
          if (!sourcePos || !targetPos) return null;

          const nodeRadius = 30;
          const dx = targetPos.x - sourcePos.x;
          const dy = targetPos.y - sourcePos.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          if (distance === 0) return null;

          const offsetX = (dx / distance) * nodeRadius;
          const offsetY = (dy / distance) * nodeRadius;

          const isHighlighted =
            selectedNode &&
            (edge.source === selectedNode || edge.target === selectedNode);

          return (
            <g key={edge.id}>
              <line
                x1={sourcePos.x + offsetX}
                y1={sourcePos.y + offsetY}
                x2={targetPos.x - offsetX}
                y2={targetPos.y - offsetY}
                stroke={isHighlighted ? '#1890ff' : '#8c8c8c'}
                strokeWidth={isHighlighted ? 3 : 2}
                markerEnd={isHighlighted ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)'}
              />
              {edge.description && (
                <text
                  x={(sourcePos.x + targetPos.x) / 2}
                  y={(sourcePos.y + targetPos.y) / 2 - 5}
                  fontSize={10}
                  fill={isHighlighted ? '#1890ff' : '#8c8c8c'}
                  textAnchor="middle"
                >
                  {EDGE_TYPE_LABELS[edge.type] || edge.type}
                </text>
              )}
            </g>
          );
        })}

        {filteredData.nodes.map(node => {
          const pos = nodePositions.get(node.id);
          if (!pos) return null;

          const isSelected = selectedNode === node.id;
          const isRoot = node.id === filteredData.root_node_id;
          const isMatched = matchedNodeIds.has(node.id);
          const nodeColor = NODE_TYPE_COLORS[node.type] || '#8c8c8c';

          const dimmed = searchKeyword.trim() && !isMatched;

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              style={{ cursor: 'pointer' }}
              onClick={() => handleNodeClick(node)}
            >
              {isMatched && (
                <circle
                  r={38}
                  fill="none"
                  stroke="#faad14"
                  strokeWidth={3}
                  strokeDasharray="4 2"
                >
                  <animate
                    attributeName="r"
                    values="35;40;35"
                    dur="1.5s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}
              <circle
                r={30}
                fill={nodeColor}
                stroke={isSelected ? '#1890ff' : isRoot ? '#faad14' : 'white'}
                strokeWidth={isSelected || isRoot ? 4 : 2}
                opacity={dimmed ? 0.4 : 0.9}
              />
              <text
                y={4}
                fontSize={11}
                fill="white"
                textAnchor="middle"
                fontWeight="bold"
                opacity={dimmed ? 0.5 : 1}
              >
                {node.name.length > 8 ? node.name.slice(0, 8) + '...' : node.name}
              </text>
              <text
                y={45}
                fontSize={10}
                fill={dimmed ? '#bfbfbf' : '#595959'}
                textAnchor="middle"
              >
                {NODE_TYPE_LABELS[node.type] || node.type}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );

  const renderList = () => (
    <div style={{ maxHeight: svgHeight, overflow: 'auto' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {filteredData.nodes.map(node => {
          const isMatched = matchedNodeIds.has(node.id);
          const dimmed = searchKeyword.trim() && !isMatched;

          return (
            <Card
              key={node.id}
              size="small"
              hoverable
              onClick={() => handleNodeClick(node)}
              style={{
                borderLeft: `4px solid ${NODE_TYPE_COLORS[node.type] || '#8c8c8c'}`,
                background: selectedNode === node.id
                  ? '#e6f7ff'
                  : isMatched
                    ? '#fffbe6'
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
          <Tag color={NODE_TYPE_COLORS[detailNode.type]}>
            {NODE_TYPE_LABELS[detailNode.type] || detailNode.type}
          </Tag>
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
                    handleNodeClick(node);
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
                    handleNodeClick(node);
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
                <Text type="secondary">{Math.round(zoom * 100)}%</Text>
                <Tooltip title="Zoom In">
                  <ZoomInOutlined onClick={handleZoomIn} style={{ cursor: 'pointer' }} />
                </Tooltip>
                <Tooltip title="Reset">
                  <ReloadOutlined onClick={handleReset} style={{ cursor: 'pointer' }} />
                </Tooltip>
              </>
            )}
          </Space>
        )
      }
    >
      {(showSearch || showFilter) && renderSearchAndFilter()}

      {viewMode === 'graph' ? renderGraph() : renderList()}

      {/* Legend */}
      <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
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
      </div>

      {showNodeDetail && renderNodeDetail()}
    </Card>
  );
}
