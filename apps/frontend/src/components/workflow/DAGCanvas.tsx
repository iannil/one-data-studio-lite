/**
 * DAG Canvas Component
 *
 * Interactive canvas for visualizing and editing workflow DAGs
 * with zoom, pan, and grid background support.
 */

import React, {
  useRef,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from 'react';
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
  CompressOutlined,
  ReloadOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { Button, Space, Tooltip, InputNumber } from 'antd';
import type { DAGNode, DAGEdge, Position, CanvasState } from '@/types/workflow';
import { dagre } from 'dagre';

interface DAGCanvasProps {
  nodes: DAGNode[];
  edges: DAGEdge[];
  selectedNodeIds?: string[];
  onNodeSelect?: (node: DAGNode) => void;
  onNodeDeselect?: () => void;
  onNodeMove?: (nodeId: string, position: Position) => void;
  onNodeDelete?: (nodeId: string) => void;
  onEdgeAdd?: (source: string, target: string) => void;
  onEdgeDelete?: (edgeId: string) => void;
  onCanvasClick?: () => void;
  editable?: boolean;
  viewMode?: 'edit' | 'view' | 'monitor';
  children?: React.ReactNode;
}

const DEFAULT_CANVAS_STATE: CanvasState = {
  scale: 1,
  position: { x: 0, y: 0 },
  minScale: 0.25,
  maxScale: 3,
};

const GRID_SIZE = 20;
const GRID_COLOR = '#e0e0e0';
const GRID_COLOR_DARK = '#d0d0d0';

export const DAGCanvas: React.FC<DAGCanvasProps> = ({
  nodes,
  edges,
  selectedNodeIds = [],
  onNodeSelect,
  onNodeDeselect,
  onNodeMove,
  onNodeDelete,
  onEdgeAdd,
  onEdgeDelete,
  onCanvasClick,
  editable = true,
  viewMode = 'edit',
  children,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const [canvasState, setCanvasState] = useState<CanvasState>(DEFAULT_CANVAS_STATE);
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState<Position>({ x: 0, y: 0 });
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<Position>({ x: 0, y: 0 });
  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);
  const [mousePosition, setMousePosition] = useState<Position>({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Node dimensions
  const nodeWidth = 160;
  const nodeHeight = 70;
  const portRadius = 7;

  // Get transform style
  const transformStyle = useMemo(() => {
    return {
      transform: `translate(${canvasState.position.x}px, ${canvasState.position.y}px) scale(${canvasState.scale})`,
      transformOrigin: '0 0',
      transition: isPanning || draggingNode ? 'none' : 'transform 0.1s ease-out',
    };
  }, [canvasState, isPanning, draggingNode]);

  // Handle wheel zoom
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newScale = Math.max(
          canvasState.minScale,
          Math.min(canvasState.maxScale, canvasState.scale + delta)
        );

        // Zoom towards mouse position
        const rect = containerRef.current?.getBoundingClientRect();
        if (rect) {
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;

          const scaleChange = newScale / canvasState.scale;
          const newPosition = {
            x: mouseX - (mouseX - canvasState.position.x) * scaleChange,
            y: mouseY - (mouseY - canvasState.position.y) * scaleChange,
          };

          setCanvasState({
            ...canvasState,
            scale: newScale,
            position: newPosition,
          });
        }
      } else {
        // Pan with scroll
        setCanvasState((prev) => ({
          ...prev,
          position: {
            x: prev.position.x - e.deltaX,
            y: prev.position.y - e.deltaY,
          },
        }));
      }
    },
    [canvasState]
  );

  // Handle pan start
  const handlePanStart = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      // Middle mouse or Alt+Left click
      setIsPanning(true);
      setPanStart({ x: e.clientX - canvasState.position.x, y: e.clientY - canvasState.position.y });
      e.preventDefault();
    } else if (e.button === 0 && e.target === canvasRef.current) {
      // Left click on canvas - deselect
      onCanvasClick?.();
      setConnectingFrom(null);
    }
  }, [canvasState.position, onCanvasClick]);

  // Handle pan move
  const handlePanMove = useCallback(
    (e: MouseEvent) => {
      if (isPanning) {
        const newPosition = {
          x: e.clientX - panStart.x,
          y: e.clientY - panStart.y,
        };
        setCanvasState((prev) => ({ ...prev, position: newPosition }));
      } else if (draggingNode && onNodeMove) {
        const rect = containerRef.current?.getBoundingClientRect();
        if (rect) {
          const x = (e.clientX - rect.left - canvasState.position.x - dragOffset.x) / canvasState.scale;
          const y = (e.clientY - rect.top - canvasState.position.y - dragOffset.y) / canvasState.scale;
          onNodeMove(draggingNode, { x, y });
        }
      }

      // Update mouse position for edge creation preview
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        setMousePosition({
          x: (e.clientX - rect.left - canvasState.position.x) / canvasState.scale,
          y: (e.clientY - rect.top - canvasState.position.y) / canvasState.scale,
        });
      }
    },
    [isPanning, panStart, draggingNode, dragOffset, canvasState, onNodeMove]
  );

  // Handle pan end
  const handlePanEnd = useCallback(() => {
    setIsPanning(false);
    setDraggingNode(null);
  }, []);

  // Handle node drag start
  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, node: DAGNode) => {
      if (!editable) return;

      // Check if clicking on output port
      if ((e.target as HTMLElement).classList.contains('dag-port-output')) {
        setConnectingFrom(node.id);
        e.stopPropagation();
        return;
      }

      // Check if clicking on input port for edge completion
      if ((e.target as HTMLElement).classList.contains('dag-port-input')) {
        if (connectingFrom) {
          onEdgeAdd?.(connectingFrom, node.id);
          setConnectingFrom(null);
        }
        e.stopPropagation();
        return;
      }

      // Start dragging node
      setDraggingNode(node.id);
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      onNodeSelect?.(node);
      e.stopPropagation();
    },
    [editable, connectingFrom, onEdgeAdd, onNodeSelect]
  );

  // Handle node hover for edge creation
  const handleNodeMouseEnter = useCallback((nodeId: string) => {
    setHoveredNode(nodeId);
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    setCanvasState((prev) => ({
      ...prev,
      scale: Math.min(prev.maxScale, prev.scale + 0.2),
    }));
  }, []);

  const handleZoomOut = useCallback(() => {
    setCanvasState((prev) => ({
      ...prev,
      scale: Math.max(prev.minScale, prev.scale - 0.2),
    }));
  }, []);

  const handleZoomFit = useCallback(() => {
    if (!containerRef.current || nodes.length === 0) return;

    const rect = containerRef.current.getBoundingClientRect();
    const bounds = calculateNodesBounds(nodes);

    const padding = 50;
    const scaleX = (rect.width - padding * 2) / (bounds.maxX - bounds.minX + nodeWidth);
    const scaleY = (rect.height - padding * 2) / (bounds.maxY - bounds.minY + nodeHeight);
    const newScale = Math.min(scaleX, scaleY, 2);

    const centerX = (bounds.minX + bounds.maxX) / 2 + nodeWidth / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2 + nodeHeight / 2;

    const newPosition = {
      x: rect.width / 2 - centerX * newScale,
      y: rect.height / 2 - centerY * newScale,
    };

    setCanvasState((prev) => ({
      ...prev,
      scale: Math.max(prev.minScale, Math.min(prev.maxScale, newScale)),
      position: newPosition,
    }));
  }, [nodes]);

  const handleZoomReset = useCallback(() => {
    setCanvasState(DEFAULT_CANVAS_STATE);
  }, []);

  const handleAutoLayout = useCallback(() => {
    // Auto-layout using dagre
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 120, edgesep: 40 });

    // Add nodes
    nodes.forEach((node) => {
      g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    // Add edges
    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    dagre.layout(g);

    // Update node positions
    nodes.forEach((node) => {
      const nodeWithPosition = g.node(node.id);
      if (nodeWithPosition && onNodeMove) {
        onNodeMove(node.id, {
          x: nodeWithPosition.x - nodeWidth / 2,
          y: nodeWithPosition.y - nodeHeight / 2,
        });
      }
    });
  }, [nodes, edges, onNodeMove]);

  // Calculate bounds of all nodes
  const calculateNodesBounds = (nodes: DAGNode[]) => {
    if (nodes.length === 0) {
      return { minX: 0, minY: 0, maxX: 0, maxY: 0 };
    }

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    nodes.forEach((node) => {
      minX = Math.min(minX, node.position.x);
      minY = Math.min(minY, node.position.y);
      maxX = Math.max(maxX, node.position.x + nodeWidth);
      maxY = Math.max(maxY, node.position.y + nodeHeight);
    });

    return { minX, minY, maxX, maxY };
  };

  // Render node
  const renderNode = (node: DAGNode) => {
    const { x, y } = node.position;
    const isSelected = selectedNodeIds.includes(node.id);
    const isTarget = hoveredNode === node.id && connectingFrom;
    const isSource = connectingFrom === node.id;

    return (
      <g
        key={node.id}
        transform={`translate(${x}, ${y})`}
        onMouseDown={(e) => handleNodeMouseDown(e as any, node)}
        onMouseEnter={() => handleNodeMouseEnter(node.id)}
        onMouseLeave={handleNodeMouseLeave}
        style={{ cursor: editable ? 'grab' : 'default' }}
      >
        {/* Node shadow */}
        <rect
          x={2}
          y={2}
          width={nodeWidth}
          height={nodeHeight}
          rx={10}
          fill="rgba(0,0,0,0.1)"
        />

        {/* Node background */}
        <rect
          x={0}
          y={0}
          width={nodeWidth}
          height={nodeHeight}
          rx={10}
          fill="#fff"
          stroke={isSelected ? '#1890ff' : isSource ? '#52c41a' : isTarget ? '#52c41a' : '#d9d9d9'}
          strokeWidth={isSelected || isSource || isTarget ? 2 : 1}
          filter={isSelected ? 'url(#selectedShadow)' : undefined}
        />

        {/* Task type indicator */}
        <rect
          x={4}
          y={4}
          width={nodeWidth - 8}
          height={4}
          fill={getTaskTypeColor(node.task_type)}
          opacity={0.8}
          rx={2}
        />

        {/* Task icon */}
        <text x={12} y={24} fontSize={14} style={{ pointerEvents: 'none' }}>
          {getTaskIcon(node.task_type)}
        </text>

        {/* Task name */}
        <text
          x={nodeWidth / 2}
          y={nodeHeight / 2 + 4}
          textAnchor="middle"
          fontSize={13}
          fontWeight={500}
          fill="#333"
          style={{ pointerEvents: 'none' }}
        >
          {truncateText(node.name, 16)}
        </text>

        {/* Task type label */}
        <text
          x={nodeWidth / 2}
          y={nodeHeight - 10}
          textAnchor="middle"
          fontSize={10}
          fill="#999"
          style={{ pointerEvents: 'none' }}
        >
          {node.task_type}
        </text>

        {/* Status indicator */}
        {node.status && viewMode === 'monitor' && (
          <circle
            cx={nodeWidth - 12}
            cy={12}
            r={5}
            fill={getStatusColor(node.status)}
          />
        )}

        {/* Input port */}
        <circle
          className="dag-port-input"
          cx={0}
          cy={nodeHeight / 2}
          r={portRadius}
          fill="#1890ff"
          style={{ cursor: editable ? 'crosshair' : 'default' }}
        />
        <circle
          cx={0}
          cy={nodeHeight / 2}
          r={portRadius + 2}
          fill="none"
          stroke="#1890ff"
          strokeOpacity={isTarget ? 0.5 : 0}
          strokeWidth={2}
        />

        {/* Output port */}
        <circle
          className="dag-port-output"
          cx={nodeWidth}
          cy={nodeHeight / 2}
          r={portRadius}
          fill="#1890ff"
          style={{ cursor: editable ? 'crosshair' : 'default' }}
        />
        <circle
          cx={nodeWidth}
          cy={nodeHeight / 2}
          r={portRadius + 2}
          fill="none"
          stroke="#52c41a"
          strokeOpacity={isSource ? 0.5 : 0}
          strokeWidth={2}
        />

        {/* Delete button */}
        {editable && isSelected && (
          <foreignObject
            x={nodeWidth - 24}
            y={4}
            width={16}
            height={16}
            style={{ pointerEvents: 'all' }}
          >
            <div
              onClick={(e) => {
                e.stopPropagation();
                onNodeDelete?.(node.id);
              }}
              style={{
                cursor: 'pointer',
                color: '#ff4d4f',
                fontSize: '16px',
                textAlign: 'center',
                lineHeight: '16px',
                fontWeight: 'bold',
              }}
            >
              ×
            </div>
          </foreignObject>
        )}
      </g>
    );
  };

  // Render edge
  const renderEdge = (edge: DAGEdge) => {
    const sourceNode = nodes.find((n) => n.id === edge.source);
    const targetNode = nodes.find((n) => n.id === edge.target);

    if (!sourceNode || !targetNode) return null;

    const startX = sourceNode.position.x + nodeWidth;
    const startY = sourceNode.position.y + nodeHeight / 2;
    const endX = targetNode.position.x;
    const endY = targetNode.position.y + nodeHeight / 2;

    // Create bezier curve
    const midX = (startX + endX) / 2;
    const ctrlOffset = Math.abs(endX - startX) * 0.5;

    return (
      <g key={edge.id}>
        {/* Edge path */}
        <path
          d={`M ${startX} ${startY} C ${startX + ctrlOffset} ${startY}, ${endX - ctrlOffset} ${endY}, ${endX} ${endY}`}
          fill="none"
          stroke="#999"
          strokeWidth={2}
          markerEnd="url(#arrowhead)"
          style={{ pointerEvents: 'none' }}
        />

        {/* Delete button on edge */}
        {editable && (
          <circle
            cx={midX}
            cy={(startY + endY) / 2}
            r={8}
            fill="#fff"
            stroke="#999"
            style={{ cursor: 'pointer' }}
            onClick={(e) => {
              e.stopPropagation();
              onEdgeDelete?.(edge.id);
            }}
          />
        )}
      </g>
    );
  };

  // Render connecting edge preview
  const renderConnectingEdge = () => {
    if (!connectingFrom) return null;

    const sourceNode = nodes.find((n) => n.id === connectingFrom);
    if (!sourceNode) return null;

    const startX = sourceNode.position.x + nodeWidth;
    const startY = sourceNode.position.y + nodeHeight / 2;

    let targetX = mousePosition.x;
    let targetY = mousePosition.y;

    // Snap to hovered node's input port
    if (hoveredNode) {
      const targetNode = nodes.find((n) => n.id === hoveredNode);
      if (targetNode) {
        targetX = targetNode.position.x;
        targetY = targetNode.position.y + nodeHeight / 2;
      }
    }

    const ctrlOffset = Math.abs(targetX - startX) * 0.5;

    return (
      <path
        d={`M ${startX} ${startY} C ${startX + ctrlOffset} ${startY}, ${targetX - ctrlOffset} ${targetY}, ${targetX} ${targetY}`}
        fill="none"
        stroke="#52c41a"
        strokeWidth={2}
        strokeDasharray="5,5"
        markerEnd="url(#arrowhead-green)"
        style={{ pointerEvents: 'none' }}
      />
    );
  };

  // Register global event listeners
  useEffect(() => {
    window.addEventListener('mousemove', handlePanMove);
    window.addEventListener('mouseup', handlePanEnd);

    return () => {
      window.removeEventListener('mousemove', handlePanMove);
      window.removeEventListener('mouseup', handlePanEnd);
    };
  }, [handlePanMove, handlePanEnd]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        background: '#f5f5f5',
        cursor: isPanning ? 'grabbing' : 'grab',
      }}
      onWheel={handleWheel}
      onMouseDown={handlePanStart}
    >
      {/* Zoom controls */}
      <Space
        style={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 10,
          background: 'rgba(255, 255, 255, 0.9)',
          padding: '8px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        }}
      >
        <Tooltip title="Zoom In (Ctrl + Scroll)">
          <Button
            type="text"
            icon={<ZoomInOutlined />}
            onClick={handleZoomIn}
            disabled={canvasState.scale >= canvasState.maxScale}
          />
        </Tooltip>
        <InputNumber
          size="small"
          min={canvasState.minScale}
          max={canvasState.maxScale}
          step={0.1}
          value={Math.round(canvasState.scale * 100)}
          onChange={(value) => {
            if (value !== null) {
              setCanvasState((prev) => ({ ...prev, scale: value / 100 }));
            }
          }}
          addonAfter="%"
          style={{ width: 80 }}
        />
        <Tooltip title="Zoom Out (Ctrl + Scroll)">
          <Button
            type="text"
            icon={<ZoomOutOutlined />}
            onClick={handleZoomOut}
            disabled={canvasState.scale <= canvasState.minScale}
          />
        </Tooltip>
        <Tooltip title="Fit to Screen">
          <Button type="text" icon={<ExpandOutlined />} onClick={handleZoomFit} />
        </Tooltip>
        <Tooltip title="Reset View">
          <Button type="text" icon={<CompressOutlined />} onClick={handleZoomReset} />
        </Tooltip>
        {editable && (
          <Tooltip title="Auto Layout">
            <Button type="text" icon={<ReloadOutlined />} onClick={handleAutoLayout} />
          </Tooltip>
        )}
      </Space>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        style={{
          background: `radial-gradient(${GRID_COLOR_DARK} 1px, transparent 1px)`,
          backgroundSize: `${GRID_SIZE * canvasState.scale}px ${GRID_SIZE * canvasState.scale}px`,
        }}
      >
        <defs>
          {/* Arrowhead marker */}
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
          </marker>
          {/* Green arrowhead for connecting */}
          <marker
            id="arrowhead-green"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#52c41a" />
          </marker>
          {/* Selected shadow filter */}
          <filter id="selectedShadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1890ff" floodOpacity={0.3} />
          </filter>
        </defs>

        <g ref={canvasRef as any} style={transformStyle as any}>
          {/* Render edges first */}
          {edges.map(renderEdge)}

          {/* Render connecting edge preview */}
          {renderConnectingEdge()}

          {/* Render nodes */}
          {nodes.map(renderNode)}
        </g>
      </svg>

      {/* Status bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: 10,
          background: 'rgba(255, 255, 255, 0.9)',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '12px',
          color: '#666',
          display: 'flex',
          gap: 16,
        }}
      >
        <span>Nodes: {nodes.length}</span>
        <span>Edges: {edges.length}</span>
        <span>Zoom: {Math.round(canvasState.scale * 100)}%</span>
      </div>

      {/* Children (for overlays) */}
      {children}
    </div>
  );
};

export default DAGCanvas;

// Helper functions
function getTaskTypeColor(taskType: string): string {
  const colors: Record<string, string> = {
    sql: '#1890ff',
    python: '#52c41a',
    shell: '#faad14',
    etl: '#13c2c2',
    training: '#722ed1',
    inference: '#eb2f96',
    evaluation: '#fa8c16',
    model_register: '#fadb14',
    wait: '#8c8c8c',
    sensor: '#52c41a',
    email: '#1890ff',
    webhook: '#722ed1',
    slack: '#eb2f96',
    export: '#faad14',
    import: '#13c2c2',
    notebook: '#fa541c',
  };
  return colors[taskType] || '#d9d9d9';
}

function getTaskIcon(taskType: string): string {
  const icons: Record<string, string> = {
    sql: '🔍',
    python: '🐍',
    shell: '⌨️',
    etl: '🔄',
    training: '🧠',
    inference: '🔮',
    evaluation: '📊',
    model_register: '📦',
    wait: '⏳',
    sensor: '📡',
    email: '📧',
    webhook: '🔗',
    slack: '💬',
    export: '📤',
    import: '📥',
    notebook: '📓',
  };
  return icons[taskType] || '📄';
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: '#faad14',
    running: '#1890ff',
    success: '#52c41a',
    failed: '#ff4d4f',
    skipped: '#d9d9d9',
    upstream_failed: '#ff4d4f',
  };
  return colors[status] || '#d9d9d9';
}

function truncateText(text: string, maxLength: number): string {
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}
