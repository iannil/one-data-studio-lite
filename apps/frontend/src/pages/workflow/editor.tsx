/**
 * Workflow DAG Editor Page
 *
 * Visual drag-and-drop editor for creating workflow DAGs.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Row,
  Col,
  Tag,
  Tooltip,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  SaveOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  NodeIndexOutlined,
  ArrowRightOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dynamic from 'next/dynamic';
import { DAGGraph } from '@/components/workflow/DAGGraph';
import { NodeConfigPanel } from '@/components/workflow/NodeConfig';
import { DAGExportImport } from '@/components/workflow/DAGExportImport';
import type { DAGNode, DAGEdge, TaskType } from '@/types/workflow';

const DAGEditor = dynamic(() => import('@/components/workflow/DAGEditor'), {
  ssr: false,
  loading: () => <div>Loading editor...</div>,
});

const WorkflowEditorPage: React.FC = () => {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLDivElement>(null);

  const [dagId, setDagId] = useState<string | undefined>();
  const [dagName, setDagName] = useState('My Workflow');
  const [dagDescription, setDagDescription] = useState('');
  const [scheduleInterval, setScheduleInterval] = useState<string | undefined>();

  const [nodes, setNodes] = useState<DAGNode[]>([]);
  const [edges, setEdges] = useState<DAGEdge[]>([]);

  const [selectedNode, setSelectedNode] = useState<DAGNode | null>(null);
  const [nodeConfigOpen, setNodeConfigOpen] = useState(false);

  const [saving, setSaving] = useState(false);
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);

  useEffect(() => {
    // Load available task types
    fetch('/api/v1/workflows/task-types')
      .then((res) => res.json())
      .then((data) => setTaskTypes(data));
  }, []);

  const handleAddNode = useCallback(
    (taskType: TaskType) => {
      const newNode: DAGNode = {
        id: `node_${Date.now()}`,
        task_type: taskType.type,
        name: `${taskType.name} ${nodes.length + 1}`,
        config: {},
        position: { x: 100 + nodes.length * 50, y: 100 + nodes.length * 30 },
      };
      setNodes([...nodes, newNode]);
    },
    [nodes]
  );

  const handleNodeSelect = useCallback(
    (node: DAGNode) => {
      setSelectedNode(node);
      setNodeConfigOpen(true);
    },
    []
  );

  const handleNodeUpdate = useCallback(
    (updatedNode: DAGNode) => {
      setNodes(nodes.map((n) => (n.id === updatedNode.id ? updatedNode : n)));
      setSelectedNode(updatedNode);
    },
    [nodes]
  );

  const handleNodeDelete = useCallback(
    (nodeId: string) => {
      setNodes(nodes.filter((n) => n.id !== nodeId));
      setEdges(edges.filter((e) => e.source !== nodeId && e.target !== nodeId));
    },
    [nodes, edges]
  );

  const handleEdgeAdd = useCallback(
    (source: string, target: string) => {
      // Check if edge already exists
      const exists = edges.some(
        (e) => e.source === source && e.target === target
      );

      if (!exists && source !== target) {
        // Check for circular dependency
        const hasCircular = checkCircularDependency(source, target, [...edges, { source, target }]);
        if (!hasCircular) {
          setEdges([...edges, { id: `edge_${Date.now()}`, source, target }]);
        } else {
          message.error('Circular dependency detected!');
        }
      }
    },
    [edges]
  );

  const checkCircularDependency = (
    source: string,
    target: string,
    allEdges: DAGEdge[]
  ): boolean => {
    const buildGraph = (edges: DAGEdge[]): Map<string, string[]> => {
      const graph = new Map<string, string[]>();
      edges.forEach((e) => {
        if (!graph.has(e.source)) {
          graph.set(e.source, []);
        }
        graph.get(e.source)!.push(e.target);
      });
      return graph;
    };

    const hasCycleDFS = (
      node: string,
      graph: Map<string, string[]>,
      visited: Set<string>,
      recStack: Set<string>
    ): boolean => {
      if (recStack.has(node)) {
        return true;
      }
      if (visited.has(node)) {
        return false;
      }

      visited.add(node);
      recStack.add(node);

      const neighbors = graph.get(node) || [];
      for (const neighbor of neighbors) {
        if (hasCycleDFS(neighbor, graph, visited, recStack)) {
          return true;
        }
      }

      recStack.delete(node);
      return false;
    };

    // Add the new edge and check for cycles
    const graph = buildGraph(allEdges);
    const visited = new Set<string>();
    const recStack = new Set<string>();

    return hasCycleDFS(target, graph, visited, recStack);
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      // Prepare DAG configuration
      const dagConfig = {
        dag_id: dagId || `workflow_${Date.now()}`,
        name: dagName,
        description: dagDescription,
        schedule_interval: scheduleInterval,
        tags: [],
        tasks: nodes.map((node) => ({
          task_id: node.id,
          task_type: node.task_type,
          name: node.name,
          description: node.config?.description,
          depends_on: edges
            .filter((e) => e.target === node.id)
            .map((e) => e.source),
          retry_count: node.config?.retry_count || 0,
          retry_delay_seconds: node.config?.retry_delay_seconds || 300,
          timeout_seconds: node.config?.timeout_seconds,
          parameters: node.config?.parameters || {},
        })),
      };

      // Create or update DAG
      const method = dagId ? 'PUT' : 'POST';
      const url = dagId ? `/api/v1/workflows/dags/${dagId}` : '/api/v1/workflows/dags';

      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dagConfig),
      });

      message.success('DAG saved successfully');
      navigate('/workflows');
    } catch (error) {
      message.error('Failed to save DAG');
    } finally {
      setSaving(false);
    }
  }, [dagId, dagName, dagDescription, scheduleInterval, nodes, edges, navigate]);

  const handleTrigger = useCallback(async () => {
    if (!dagId) {
      message.warning('Please save the DAG first');
      return;
    }

    try {
      await fetch(`/api/v1/workflows/dags/${dagId}/run`, {
        method: 'POST',
      });
      message.success('DAG triggered successfully');
    } catch (error) {
      message.error('Failed to trigger DAG');
    }
  }, [dagId]);

  const handleDelete = useCallback(async () => {
    if (!dagId) {
      navigate('/workflows');
      return;
    }

    try {
      await fetch(`/api/v1/workflows/dags/${dagId}`, {
        method: 'DELETE',
      });
      message.success('DAG deleted successfully');
      navigate('/workflows');
    } catch (error) {
      message.error('Failed to delete DAG');
    }
  }, [dagId, navigate]);

  const handleImport = useCallback((data: any) => {
    const dagData = data.dag;
    if (!dagData) return;

    // Set DAG info
    setDagId(undefined); // New DAG on import
    setDagName(dagData.name || 'Imported Workflow');
    setDagDescription(dagData.description || '');
    setScheduleInterval(dagData.schedule_interval);

    // Rebuild nodes from tasks
    const importedNodes: DAGNode[] = (dagData.tasks || []).map((task: any) => ({
      id: task.task_id,
      task_type: task.task_type,
      name: task.name,
      config: {
        description: task.description,
        depends_on: task.depends_on,
        retry_count: task.retry_count,
        retry_delay_seconds: task.retry_delay_seconds,
        timeout_seconds: task.timeout_seconds,
        parameters: task.parameters,
      },
      position: task.position || { x: 100, y: 100 },
    }));
    setNodes(importedNodes);

    // Rebuild edges from dependencies
    const importedEdges: DAGEdge[] = [];
    importedNodes.forEach((node) => {
      const dependsOn = node.config?.depends_on || [];
      dependsOn.forEach((depId: string) => {
        importedEdges.push({
          id: `edge_${depId}_${node.id}`,
          source: depId,
          target: node.id,
        });
      });
    });
    setEdges(importedEdges);

    message.success('DAG imported successfully');
  }, []);

  const handleClone = useCallback(async (newName: string) => {
    if (!dagId) return;

    try {
      const response = await fetch(`/api/v1/workflows/dags/${dagId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
      });

      if (response.ok) {
        message.success('DAG cloned successfully');
        navigate('/workflows');
      } else {
        message.error('Failed to clone DAG');
      }
    } catch (error) {
      message.error('Failed to clone DAG');
    }
  }, [dagId, navigate]);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          background: '#fff',
          borderBottom: '1px solid #d9d9d9',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Space>
          <Button
            type="text"
            icon={<ArrowRightOutlined />}
            onClick={() => navigate('/workflows')}
          >
            Workflows
          </Button>
          <Input
            value={dagName}
            onChange={(e) => setDagName(e.target.value)}
            placeholder="Workflow Name"
            style={{ width: 200 }}
          />
          <Input
            value={scheduleInterval}
            onChange={(e) => setScheduleInterval(e.target.value)}
            placeholder="Cron (e.g., 0 0 * * *)"
            style={{ width: 150 }}
          />
          <Tag>State: {nodes.length > 0 ? 'Active' : 'Draft'}</Tag>
          <Tag>{nodes.length} nodes</Tag>
          <Tag>{edges.length} edges</Tag>
        </Space>

        <Space>
          <DAGExportImport
            dagId={dagId}
            dagName={dagName}
            nodes={nodes}
            edges={edges}
            onImport={handleImport}
            onClone={handleClone}
          />
          <Button
            icon={<DeleteOutlined />}
            danger
            disabled={!dagId}
            onClick={handleDelete}
          >
            Delete
          </Button>
          <Button
            icon={<PlayCircleOutlined />}
            disabled={!dagId}
            onClick={handleTrigger}
          >
            Run
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSave}
          >
            Save
          </Button>
        </Space>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Task Palette */}
        <div
          style={{
            width: 200,
            background: '#fafafa',
            borderRight: '1px solid #d9d9d9',
            padding: '16px',
            overflowY: 'auto',
          }}
        >
          <h4 style={{ marginBottom: '16px' }}>Task Types</h4>

          {taskTypes.map((taskType) => (
            <Card
              key={taskType.type}
              size="small"
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('taskType', JSON.stringify(taskType));
              }}
              style={{ marginBottom: '8px', cursor: 'grab' }}
              bodyStyle={{ padding: '8px' }}
            >
              <Tag color={getCategoryColor(taskType.category)}>
                {taskType.type}
              </Tag>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                {taskType.name}
              </div>
            </Card>
          ))}
        </div>

        {/* Canvas */}
        <div
          ref={canvasRef}
          style={{
            flex: 1,
            background: '#f5f5f5',
            backgroundImage:
              'radial-gradient(#ddd 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            position: 'relative',
            overflow: 'hidden',
          }}
          onDrop={(e) => {
            e.preventDefault();
            const taskType = JSON.parse(e.dataTransfer.getData('taskType') || '{}');
            const rect = canvasRef.current?.getBoundingClientRect();
            const x = e.clientX - (rect?.left || 0);
            const y = e.clientY - (rect?.top || 0);
            handleAddNode(taskType);
          }}
          onDragOver={(e) => e.preventDefault()}
        >
          <DAGGraph
            nodes={nodes}
            edges={edges}
            onNodeSelect={handleNodeSelect}
            onNodeDelete={handleNodeDelete}
            onEdgeAdd={handleEdgeAdd}
          />
        </div>
      </div>

      {/* Node Configuration Panel */}
      <Drawer
        title="Node Configuration"
        placement="right"
        width={400}
        open={nodeConfigOpen}
        onClose={() => setNodeConfigOpen(false)}
      >
        {selectedNode && (
          <NodeConfigPanel
            node={selectedNode}
            taskTypes={taskTypes}
            nodes={nodes}
            onUpdate={handleNodeUpdate}
            onClose={() => setNodeConfigOpen(false)}
          />
        )}
      </Drawer>
    </div>
  );
};

function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    'Data': 'blue',
    'Code': 'green',
    'Machine Learning': 'purple',
    'Control Flow': 'orange',
    'Notification': 'cyan',
    'Data Transfer': 'geekblue',
    'Notebook': 'red',
  };
  return colors[category] || 'default';
}

export default WorkflowEditorPage;
