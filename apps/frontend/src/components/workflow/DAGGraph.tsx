/**
 * DAG Graph Component
 *
 * Visualizes DAG nodes and edges using SVG.
 */

import React, { useRef, useCallback, useState } from 'react';
import { message, Popconfirm } from 'antd';
import {
  DeleteOutlined,
  SettingOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import type { DAGNode, DAGEdge } from '@/types/workflow';

interface DAGGraphProps {
  nodes: DAGNode[];
  edges: DAGEdge[];
  onNodeSelect?: (node: DAGNode) => void;
  onNodeDelete?: (nodeId: string) => void;
  onEdgeAdd?: (source: string, target: string) => void;
  onEdgeDelete?: (edgeId: string) => void;
  editable?: boolean;
}

export const DAGGraph: React.FC<DAGGraphProps> = ({
  nodes,
  edges,
  onNodeSelect,
  onNodeDelete,
  onEdgeAdd,
  onEdgeDelete,
  editable = true,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Node dimensions
  const nodeWidth = 140;
  const nodeHeight = 60;
  const portRadius = 6;

  // Handle node drag start
  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, node: DAGNode) => {
      if (!editable) return;

      // Check if clicking on port
      if ((e.target as HTMLElement).classList.contains('dag-port')) {
        const port = (e.target as HTMLElement).dataset.port;
        if (port === 'output') {
          setConnectingFrom(node.id);
        }
        return;
      }

      setDraggingNode(node.id);
      const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      e.stopPropagation();
    },
    [editable]
  );

  // Handle node drag
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!draggingNode || !svgRef.current) return;

      const svgRect = svgRef.current.getBoundingClientRect();
      const x = e.clientX - svgRect.left - dragOffset.x;
      const y = e.clientY - svgRect.top - dragOffset.y;

      // Constrain to canvas
      const constrainedX = Math.max(0, Math.min(x, 800 - nodeWidth));
      const constrainedY = Math.max(0, Math.min(y, 600 - nodeHeight));

      // This would update the node position in parent
      // For now, we just log it
    },
    [draggingNode, dragOffset, nodeWidth, nodeHeight]
  );

  // Handle drag end
  const handleMouseUp = useCallback(() => {
    setDraggingNode(null);
  }, []);

  // Handle canvas click (for creating edges)
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      if (connectingFrom && hoveredNode) {
        onEdgeAdd?.(connectingFrom, hoveredNode);
        setConnectingFrom(null);
        setHoveredNode(null);
      }
    },
    [connectingFrom, hoveredNode, onEdgeAdd]
  );

  // Handle node hover for edge creation
  const handleNodeMouseEnter = useCallback((nodeId: string) => {
    setHoveredNode(nodeId);
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  // Handle edge delete
  const handleEdgeDelete = useCallback(
    (edgeId: string) => {
      onEdgeDelete?.(edgeId);
    },
    [onEdgeDelete]
  );

  // Render node
  const renderNode = (node: DAGNode) => {
    const { x, y } = node.position;

    return (
      <g
        key={node.id}
        transform={`translate(${x}, ${y})`}
        onMouseDown={(e) => handleNodeMouseDown(e as any, node)}
        onMouseEnter={() => handleNodeMouseEnter(node.id)}
        onMouseLeave={handleNodeMouseLeave}
        onClick={() => onNodeSelect?.(node)}
        style={{ cursor: editable ? 'pointer' : 'default' }}
      >
        {/* Node background */}
        <rect
          x={0}
          y={0}
          width={nodeWidth}
          height={nodeHeight}
          rx={8}
          fill="#fff"
          stroke={
            connectingFrom === node.id
              ? '#1890ff'
              : hoveredNode === node.id && connectingFrom
              ? '#52c41a'
              : '#d9d9d9'
          }
          strokeWidth={connectingFrom === node.id ? 2 : 1}
        />

        {/* Task type icon/color indicator */}
        <rect
          x={4}
          y={4}
          width={nodeWidth - 8}
          height={4}
          fill={getTaskTypeColor(node.task_type)}
          opacity={0.3}
          rx={2}
        />

        {/* Task name */}
        <text
          x={nodeWidth / 2}
          y={nodeHeight / 2 + 4}
          textAnchor="middle"
          fontSize={12}
          fill="#333"
          style={{ pointerEvents: 'none' }}
        >
          {node.name.length > 15 ? node.name.substring(0, 15) + '...' : node.name}
        </text>

        {/* Task type label */}
        <text
          x={nodeWidth / 2}
          y={nodeHeight - 8}
          textAnchor="middle"
          fontSize={10}
          fill="#999"
          style={{ pointerEvents: 'none' }}
        >
          {node.task_type}
        </text>

        {/* Input port */}
        <circle
          className="dag-port"
          data-port="input"
          cx={0}
          cy={nodeHeight / 2}
          r={portRadius}
          fill="#1890ff"
          style={{ cursor: editable ? 'crosshair' : 'default' }}
        />

        {/* Output port */}
        <circle
          className="dag-port"
          data-port="output"
          cx={nodeWidth}
          cy={nodeHeight / 2}
          r={portRadius}
          fill="#1890ff"
          style={{ cursor: editable ? 'crosshair' : 'default' }}
        />

        {/* Delete button */}
        {editable && (
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
                fontSize: '14px',
                textAlign: 'center',
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

    return (
      <g key={edge.id}>
        {/* Edge path */}
        <path
          d={`M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`}
          fill="none"
          stroke="#999"
          strokeWidth={2}
          markerEnd="url(#arrowhead)"
          style={{ pointerEvents: 'none' }}
        />

        {/* Delete button on edge (center) */}
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
              handleEdgeDelete(edge.id);
            }}
          />
        )}
      </g>
    );
  };

  return (
    <svg
      ref={svgRef}
      width="100%"
      height="100%"
      onMouseMove={handleMouseMove as any}
      onMouseUp={handleMouseUp}
      onClick={handleCanvasClick}
      style={{ background: 'transparent' }}
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
      </defs>

      {/* Render edges first (so nodes appear on top) */}
      {edges.map(renderEdge)}

      {/* Render nodes */}
      {nodes.map(renderNode)}
    </svg>
  );
};

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
  return colors[taskType] || '#d9d9d9d';
}

export default DAGGraph;
