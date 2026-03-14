/**
 * Workflow DAG Editor Page
 *
 * Visual drag-and-drop editor for creating workflow DAGs.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Space,
  message,
  Popconfirm,
  Drawer,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Row,
  Col,
  Divider,
  Tooltip,
  Breadcrumb,
} from 'antd';
import {
  SaveOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  SettingOutlined,
  HistoryOutlined,
  EyeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { NodePalette, DEFAULT_TASK_TYPES } from '@/components/workflow/NodePalette';
import { DAGCanvas } from '@/components/workflow/DAGCanvas';
import { NodeConfigPanel } from '@/components/workflow/NodeConfig';
import { DAGExportImport } from '@/components/workflow/DAGExportImport';
import { useWorkflowStore } from '@/stores/workflow';
import type {
  DAGNode,
  DAGEdge,
  TaskType,
  Position,
  ScheduleOptions,
} from '@/types/workflow';

interface WorkflowEditorPageProps {
  dagId?: string;
}

const WorkflowEditorPage: React.FC<WorkflowEditorPageProps> = ({ dagId: propDagId }) => {
  const { dagId: paramDagId } = useParams<{ dagId?: string }>();
  const navigate = useNavigate();

  const dagId = propDagId || paramDagId;

  const {
    currentDag,
    currentDagNodes,
    currentDagEdges,
    taskTypes,
    loading,
    error,
    fetchDag,
    createDag,
    updateDag,
    deleteDag,
    triggerDagRun,
    fetchTaskTypes,
    addNode,
    updateNode,
    deleteNode,
    addEdge,
    deleteEdge,
    clearCurrentDag,
    clearError,
  } = useWorkflowStore();

  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<DAGNode | null>(null);
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['Data', 'Code']);

  // Form for DAG settings
  const [settingsForm] = Form.useForm();

  // Enhanced task types with descriptions
  const enhancedTaskTypes = useMemo(() => {
    if (taskTypes.length > 0) {
      return taskTypes.map((tt) => {
        const defaultType = DEFAULT_TASK_TYPES.find((dt) => dt.type === tt.type);
        return {
          ...tt,
          description: defaultType?.description || tt.description,
          icon: defaultType?.icon,
          color: defaultType?.color,
        };
      });
    }
    return DEFAULT_TASK_TYPES;
  }, [taskTypes]);

  // Load DAG on mount
  useEffect(() => {
    fetchTaskTypes().catch((err) => {
      message.error('Failed to load task types');
    });

    if (dagId && dagId !== 'new') {
      fetchDag(dagId).catch((err) => {
        message.error('Failed to load workflow');
      });
    }

    return () => {
      clearCurrentDag();
    };
  }, [dagId, fetchDag, fetchTaskTypes, clearCurrentDag]);

  // Initialize settings form
  useEffect(() => {
    if (currentDag) {
      settingsForm.setFieldsValue({
        name: currentDag.name,
        description: currentDag.description,
        schedule_interval: currentDag.schedule_interval,
        tags: currentDag.tags || [],
      });
    }
  }, [currentDag, settingsForm]);

  // Track changes
  useEffect(() => {
    if (currentDagNodes.length > 0 || currentDagEdges.length > 0) {
      setHasChanges(true);
    }
  }, [currentDagNodes, currentDagEdges]);

  // Show errors
  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  // Handle adding a node
  const handleAddNode = useCallback(
    (taskType: TaskType, position?: Position) => {
      const newNode: DAGNode = {
        id: `${taskType.type}_${Date.now()}`,
        task_type: taskType.type,
        name: `${taskType.name}`,
        description: taskType.description,
        config: {
          description: taskType.description,
          retry_count: 0,
          retry_delay_seconds: 300,
          parameters: {},
        },
        position: position || {
          x: 100 + currentDagNodes.length * 50,
          y: 100 + currentDagNodes.length * 30,
        },
      };

      addNode(newNode);
      message.success(`Added ${taskType.name} node`);
    },
    [currentDagNodes.length, addNode]
  );

  // Handle node move
  const handleNodeMove = useCallback(
    (nodeId: string, position: Position) => {
      const node = currentDagNodes.find((n) => n.id === nodeId);
      if (node) {
        updateNode({ ...node, position });
        setHasChanges(true);
      }
    },
    [currentDagNodes, updateNode]
  );

  // Handle node select
  const handleNodeSelect = useCallback(
    (node: DAGNode) => {
      setSelectedNode(node);
      setSelectedNodeIds([node.id]);
      setConfigDrawerOpen(true);
    },
    []
  );

  // Handle node update from config panel
  const handleNodeUpdate = useCallback(
    (updatedNode: DAGNode) => {
      updateNode(updatedNode);
      setSelectedNode(updatedNode);
      setHasChanges(true);
    },
    [updateNode]
  );

  // Handle node delete
  const handleNodeDelete = useCallback(
    (nodeId: string) => {
      deleteNode(nodeId);
      if (selectedNode?.id === nodeId) {
        setSelectedNode(null);
        setConfigDrawerOpen(false);
      }
      message.success('Node deleted');
      setHasChanges(true);
    },
    [deleteNode, selectedNode]
  );

  // Handle edge add
  const handleEdgeAdd = useCallback(
    (source: string, target: string) => {
      // Check if edge already exists
      const exists = currentDagEdges.some(
        (e) => e.source === source && e.target === target
      );

      if (!exists && source !== target) {
        // Check for circular dependency
        if (!checkCircularDependency(source, target)) {
          addEdge({
            id: `edge_${source}_${target}`,
            source,
            target,
          });
          message.success('Edge added');
          setHasChanges(true);
        } else {
          message.error('Circular dependency detected!');
        }
      }
    },
    [currentDagEdges, addEdge]
  );

  // Check for circular dependency using DFS
  const checkCircularDependency = useCallback(
    (source: string, target: string): boolean => {
      const buildGraph = (): Map<string, string[]> => {
        const graph = new Map<string, string[]>();
        currentDagEdges.forEach((e) => {
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
        if (recStack.has(node)) return true;
        if (visited.has(node)) return false;

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
      const graph = buildGraph();
      if (!graph.has(source)) {
        graph.set(source, []);
      }
      graph.get(source)!.push(target);

      const visited = new Set<string>();
      const recStack = new Set<string>();

      return hasCycleDFS(target, graph, visited, recStack);
    },
    [currentDagEdges]
  );

  // Handle edge delete
  const handleEdgeDelete = useCallback(
    (edgeId: string) => {
      deleteEdge(edgeId);
      message.success('Edge deleted');
      setHasChanges(true);
    },
    [deleteEdge]
  );

  // Handle save
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const settings = settingsForm.getFieldsValue();

      // Prepare tasks with dependencies calculated from edges
      const tasks = currentDagNodes.map((node) => {
        const dependencies = currentDagEdges
          .filter((e) => e.target === node.id)
          .map((e) => e.source);

        return {
          task_id: node.id,
          task_type: node.task_type,
          name: node.name,
          description: node.config?.description,
          depends_on: dependencies,
          retry_count: node.config?.retry_count || 0,
          retry_delay_seconds: node.config?.retry_delay_seconds || 300,
          timeout_seconds: node.config?.timeout_seconds,
          parameters: node.config?.parameters || {},
        };
      });

      const dagConfig = {
        dag_id: dagId || `workflow_${Date.now()}`,
        name: settings.name,
        description: settings.description,
        schedule_interval: settings.schedule_interval,
        tags: settings.tags || [],
        tasks,
      };

      if (dagId && dagId !== 'new') {
        await updateDag(dagId, dagConfig);
      } else {
        const result = await createDag(dagConfig);
        navigate(`/workflows/editor/${result.dag_id}`, { replace: true });
      }

      message.success('Workflow saved successfully');
      setHasChanges(false);
    } catch (err: any) {
      message.error(err.message || 'Failed to save workflow');
    } finally {
      setSaving(false);
    }
  }, [
    dagId,
    currentDagNodes,
    currentDagEdges,
    settingsForm,
    createDag,
    updateDag,
    navigate
  ]);

  // Handle run
  const handleRun = useCallback(async () => {
    if (!dagId || dagId === 'new') {
      message.warning('Please save the workflow first');
      return;
    }

    try {
      await triggerDagRun(dagId);
      message.success('Workflow triggered successfully');
    } catch (err: any) {
      message.error(err.message || 'Failed to trigger workflow');
    }
  }, [dagId, triggerDagRun]);

  // Handle delete
  const handleDelete = useCallback(async () => {
    if (!dagId || dagId === 'new') {
      navigate('/workflows');
      return;
    }

    try {
      await deleteDag(dagId);
      message.success('Workflow deleted successfully');
      navigate('/workflows');
    } catch (err: any) {
      message.error(err.message || 'Failed to delete workflow');
    }
  }, [dagId, deleteDag, navigate]);

  // Handle import
  const handleImport = useCallback((data: any) => {
    const dagData = data.dag;
    if (!dagData) return;

    // Set DAG info
    settingsForm.setFieldsValue({
      name: dagData.name || 'Imported Workflow',
      description: dagData.description,
      schedule_interval: dagData.schedule_interval,
      tags: dagData.tags || [],
    });

    // Clear current nodes and edges
    clearCurrentDag();

    // Add imported nodes
    dagData.tasks?.forEach((task: any) => {
      addNode({
        id: task.task_id,
        task_type: task.task_type,
        name: task.name,
        description: task.description,
        config: {
          description: task.description,
          retry_count: task.retry_count,
          retry_delay_seconds: task.retry_delay_seconds,
          timeout_seconds: task.timeout_seconds,
          parameters: task.parameters,
        },
        position: task.position || { x: 100, y: 100 },
      });
    });

    // Add imported edges
    dagData.tasks?.forEach((task: any) => {
      const dependsOn = task.depends_on || [];
      dependsOn.forEach((depId: string) => {
        addEdge({
          id: `edge_${depId}_${task.task_id}`,
          source: depId,
          target: task.task_id,
        });
      });
    });

    setHasChanges(true);
    message.success('Workflow imported successfully');
  }, [clearCurrentDag, addNode, addEdge, settingsForm]);

  // Handle clone
  const handleClone = useCallback(async (newName: string) => {
    if (!dagId || dagId === 'new') return;

    try {
      const { cloneDag } = useWorkflowStore.getState();
      const result = await cloneDag(dagId, newName);
      message.success('Workflow cloned successfully');
      navigate(`/workflows/editor/${result.dag_id}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to clone workflow');
    }
  }, [dagId, navigate]);

  // Calculate DAG statistics
  const stats = useMemo(() => {
    return {
      nodes: currentDagNodes.length,
      edges: currentDagEdges.length,
      types: new Set(currentDagNodes.map((n) => n.task_type)).size,
    };
  }, [currentDagNodes, currentDagEdges]);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Space>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => {
              if (hasChanges) {
                Modal.confirm({
                  title: 'Unsaved Changes',
                  content: 'You have unsaved changes. Do you want to leave?',
                  onOk: () => navigate('/workflows'),
                });
              } else {
                navigate('/workflows');
              }
            }}
          >
            Back
          </Button>
          <Divider type="vertical" />
          <Breadcrumb
            items={[
              { title: 'Workflows', href: '/workflows' },
              { title: settingsForm.getFieldValue('name') || 'New Workflow' },
            ]}
          />
          <Tag color={hasChanges ? 'orange' : 'green'}>
            {hasChanges ? 'Unsaved' : 'Saved'}
          </Tag>
          <Divider type="vertical" />
          <Space size="small">
            <Tooltip title="Nodes">
              <Tag>{stats.nodes} nodes</Tag>
            </Tooltip>
            <Tooltip title="Edges">
              <Tag>{stats.edges} edges</Tag>
            </Tooltip>
            <Tooltip title="Task Types">
              <Tag>{stats.types} types</Tag>
            </Tooltip>
          </Space>
        </Space>

        <Space>
          <Tooltip title="Settings">
            <Button
              icon={<SettingOutlined />}
              onClick={() => setSettingsModalOpen(true)}
            >
              Settings
            </Button>
          </Tooltip>

          <DAGExportImport
            dagId={dagId === 'new' ? undefined : dagId}
            dagName={settingsForm.getFieldValue('name')}
            nodes={currentDagNodes}
            edges={currentDagEdges}
            onImport={handleImport}
            onClone={handleClone}
          />

          <Popconfirm
            title="Are you sure you want to delete this workflow?"
            onConfirm={handleDelete}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button icon={<DeleteOutlined />} danger disabled={!dagId || dagId === 'new'}>
              Delete
            </Button>
          </Popconfirm>

          <Button
            icon={<PlayCircleOutlined />}
            disabled={!dagId || dagId === 'new' || hasChanges}
            onClick={handleRun}
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
        {/* Left Panel - Node Palette */}
        <div
          style={{
            width: 280,
            background: '#fafafa',
            borderRight: '1px solid #f0f0f0',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ padding: '16px' }}>
            <h3 style={{ margin: 0, marginBottom: 12 }}>Task Palette</h3>
            <NodePalette
              taskTypes={enhancedTaskTypes}
              searchValue={searchValue}
              onSearchChange={setSearchValue}
              expandedCategories={expandedCategories}
              onCategoryChange={setExpandedCategories}
              onTaskSelect={(taskType) => {
                // Find a good position for the new node
                const lastNode = currentDagNodes[currentDagNodes.length - 1];
                const position = lastNode
                  ? {
                      x: lastNode.position.x + 200,
                      y: lastNode.position.y,
                    }
                  : { x: 100, y: 100 };

                handleAddNode(taskType, position);
              }}
            />
          </div>
        </div>

        {/* Canvas */}
        <div style={{ flex: 1 }}>
          <DAGCanvas
            nodes={currentDagNodes}
            edges={currentDagEdges}
            selectedNodeIds={selectedNodeIds}
            onNodeSelect={handleNodeSelect}
            onNodeMove={handleNodeMove}
            onNodeDelete={handleNodeDelete}
            onEdgeAdd={handleEdgeAdd}
            onEdgeDelete={handleEdgeDelete}
            onCanvasClick={() => {
              setSelectedNodeIds([]);
              setSelectedNode(null);
              setConfigDrawerOpen(false);
            }}
            editable={true}
            viewMode="edit"
          />
        </div>
      </div>

      {/* Node Configuration Drawer */}
      <Drawer
        title={
          <Space>
            <span>Node Configuration</span>
            {selectedNode && (
              <Tag color="blue">{selectedNode.task_type}</Tag>
            )}
          </Space>
        }
        placement="right"
        width={400}
        open={configDrawerOpen}
        onClose={() => setConfigDrawerOpen(false)}
      >
        {selectedNode && (
          <NodeConfigPanel
            node={selectedNode}
            taskTypes={enhancedTaskTypes}
            nodes={currentDagNodes}
            onUpdate={handleNodeUpdate}
            onClose={() => setConfigDrawerOpen(false)}
          />
        )}
      </Drawer>

      {/* DAG Settings Modal */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            Workflow Settings
          </Space>
        }
        open={settingsModalOpen}
        onOk={() => {
          settingsForm.validateFields().then(() => {
            setSettingsModalOpen(false);
            setHasChanges(true);
          });
        }}
        onCancel={() => setSettingsModalOpen(false)}
        width={600}
      >
        <Form form={settingsForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Workflow Name"
                name="name"
                rules={[{ required: true, message: 'Name is required' }]}
              >
                <Input placeholder="My Workflow" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Schedule (Cron)" name="schedule_interval">
                <Input placeholder="0 0 * * *" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Description" name="description">
            <Input.TextArea rows={3} placeholder="Describe your workflow..." />
          </Form.Item>

          <Form.Item label="Tags" name="tags">
            <Select mode="tags" placeholder="Add tags..." />
          </Form.Item>

          <Divider orientation="left">Schedule Options</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="Catchup" name={['scheduleOptions', 'catchup']} valuePropName="checked">
                <Select
                  defaultValue={false}
                  options={[
                    { label: 'Yes', value: true },
                    { label: 'No', value: false },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Max Active Runs" name={['scheduleOptions', 'maxActiveRuns']}>
                <Input type="number" placeholder={1} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Concurrency" name={['scheduleOptions', 'concurrency']}>
            <Input type="number" placeholder={16} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WorkflowEditorPage;
