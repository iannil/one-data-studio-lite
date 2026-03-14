/**
 * Workflow List Page
 *
 * Lists all workflow DAGs with filtering, search, and management actions.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Tooltip,
  Popconfirm,
  message,
  Modal,
  Form,
  Row,
  Col,
  Statistic,
  Badge,
  Dropdown,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  CopyOutlined,
  DownloadOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  MoreOutlined,
  ReloadOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useWorkflowStore, useWorkflowLoading } from '@/stores/workflow';
import type { DAG, DAGRun, ColumnsType } from '@/types/workflow';

const WorkflowListPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    dags,
    loading,
    error,
    fetchDags,
    createDag,
    deleteDag,
    triggerDagRun,
    pauseDag,
    unpauseDag,
    exportDag,
    cloneDag,
    clearError,
  } = useWorkflowStore();

  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [tagFilter, setTagFilter] = useState<string>('all');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedDagId, setSelectedDagId] = useState<string | null>(null);
  const [runsModalOpen, setRunsModalOpen] = useState(false);
  const [dagRuns, setDagRuns] = useState<DAGRun[]>([]);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchDags().catch((err) => {
      if (error) message.error(error);
    });
  }, [fetchDags]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleCreateDag = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const newDag = await createDag(values);
      message.success('Workflow created successfully');
      setCreateModalOpen(false);
      form.resetFields();
      navigate(`/workflows/editor/${newDag.dag_id}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to create workflow');
    }
  }, [createDag, form, navigate]);

  const handleDeleteDag = useCallback(
    async (dagId: string) => {
      try {
        await deleteDag(dagId);
        message.success('Workflow deleted successfully');
      } catch (err: any) {
        message.error(err.message || 'Failed to delete workflow');
      }
    },
    [deleteDag]
  );

  const handleTriggerRun = useCallback(
    async (dagId: string) => {
      try {
        await triggerDagRun(dagId);
        message.success('Workflow triggered successfully');
      } catch (err: any) {
        message.error(err.message || 'Failed to trigger workflow');
      }
    },
    [triggerDagRun]
  );

  const handleTogglePause = useCallback(
    async (dag: DAG) => {
      try {
        if (dag.is_paused) {
          await unpauseDag(dag.dag_id);
          message.success('Workflow unpaused successfully');
        } else {
          await pauseDag(dag.dag_id);
          message.success('Workflow paused successfully');
        }
      } catch (err: any) {
        message.error(err.message || 'Failed to toggle pause state');
      }
    },
    [pauseDag, unpauseDag]
  );

  const handleExport = useCallback(
    async (dagId: string, dagName: string) => {
      try {
        const data = await exportDag(dagId);

        // Download as file
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${dagName}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        message.success('Workflow exported successfully');
      } catch (err: any) {
        message.error(err.message || 'Failed to export workflow');
      }
    },
    [exportDag]
  );

  const handleClone = useCallback(
    async (dagId: string, dagName: string) => {
      Modal.prompt({
        title: 'Clone Workflow',
        content: 'Enter a name for the cloned workflow:',
        placeholder: `Copy of ${dagName}`,
        async onOk(value) {
          try {
            await cloneDag(dagId, value || `Copy of ${dagName}`);
            message.success('Workflow cloned successfully');
            fetchDags();
          } catch (err: any) {
            message.error(err.message || 'Failed to clone workflow');
          }
        },
      });
    },
    [cloneDag, fetchDags]
  );

  const handleViewRuns = useCallback(
    async (dagId: string) => {
      setSelectedDagId(dagId);
      setRunsModalOpen(true);

      try {
        const { getDagRuns } = useWorkflowStore.getState();
        const runs = await getDagRuns(dagId);
        setDagRuns(runs);
      } catch (err: any) {
        message.error(err.message || 'Failed to fetch workflow runs');
      }
    },
    []
  );

  // Filter DAGs
  const filteredDags = dags.filter((dag) => {
    const matchesSearch =
      !searchText ||
      dag.name.toLowerCase().includes(searchText.toLowerCase()) ||
      dag.dag_id.toLowerCase().includes(searchText.toLowerCase()) ||
      (dag.description?.toLowerCase().includes(searchText.toLowerCase()));

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && dag.is_active && !dag.is_paused) ||
      (statusFilter === 'paused' && dag.is_paused) ||
      (statusFilter === 'inactive' && !dag.is_active);

    const matchesTag =
      tagFilter === 'all' || dag.tags.includes(tagFilter);

    return matchesSearch && matchesStatus && matchesTag;
  });

  // Get all unique tags
  const allTags = Array.from(
    new Set(dags.flatMap((dag) => dag.tags))
  ).sort();

  // Status badge
  const getStatusBadge = (dag: DAG) => {
    if (!dag.is_active) {
      return <Badge status="default" text="Inactive" />;
    }
    if (dag.is_paused) {
      return <Badge status="warning" text="Paused" />;
    }
    return <Badge status="processing" text="Active" />;
  };

  // Schedule badge
  const getScheduleBadge = (schedule: string | undefined) => {
    if (!schedule) {
      return <Tag color="default">Manual</Tag>;
    }
    return <Tag color="blue">{schedule}</Tag>;
  };

  // Table columns
  const columns: ColumnsType<DAG> = [
    {
      title: 'Workflow',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DAG) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={() => navigate(`/workflows/editor/${record.dag_id}`)}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          <span style={{ fontSize: '12px', color: '#999' }}>
            {record.dag_id}
          </span>
        </Space>
      ),
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => (
        <span style={{ color: '#666' }}>{desc || '-'}</span>
      ),
    },
    {
      title: 'Schedule',
      dataIndex: 'schedule_interval',
      key: 'schedule_interval',
      width: 150,
      render: getScheduleBadge,
      filters: [
        { text: 'Manual', value: null },
        { text: 'Scheduled', value: 'scheduled' },
      ],
      onFilter: (value, record) =>
        value === null ? !record.schedule_interval : !!record.schedule_interval,
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_, record: DAG) => getStatusBadge(record),
      filters: [
        { text: 'Active', value: 'active' },
        { text: 'Paused', value: 'paused' },
        { text: 'Inactive', value: 'inactive' },
      ],
      onFilter: (value, record) => {
        if (value === 'active') return record.is_active && !record.is_paused;
        if (value === 'paused') return record.is_paused;
        if (value === 'inactive') return !record.is_active;
        return true;
      },
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      render: (tags: string[]) => (
        <Space size={4} wrap>
          {tags.slice(0, 2).map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
          {tags.length > 2 && (
            <Tag>+{tags.length - 2}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
      sorter: (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record: DAG) => (
        <Space size="small">
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => navigate(`/workflows/editor/${record.dag_id}`)}
            />
          </Tooltip>
          <Tooltip title={record.is_paused ? 'Unpause' : 'Pause'}>
            <Button
              type="text"
              icon={record.is_paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              onClick={() => handleTogglePause(record)}
            />
          </Tooltip>
          <Tooltip title="Run Now">
            <Button
              type="text"
              icon={<ThunderboltOutlined />}
              disabled={!record.is_active || record.is_paused}
              onClick={() => handleTriggerRun(record.dag_id)}
            />
          </Tooltip>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'runs',
                  label: 'View Runs',
                  icon: <ClockCircleOutlined />,
                  onClick: () => handleViewRuns(record.dag_id),
                },
                {
                  key: 'export',
                  label: 'Export',
                  icon: <DownloadOutlined />,
                  onClick: () => handleExport(record.dag_id, record.name),
                },
                {
                  key: 'clone',
                  label: 'Clone',
                  icon: <CopyOutlined />,
                  onClick: () => handleClone(record.dag_id, record.name),
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  label: 'Delete',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => handleDeleteDag(record.dag_id),
                },
              ],
            }}
            trigger={['click']}
          >
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // Run status badge
  const getRunStatusBadge = (state: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      queued: { color: 'default', icon: <ClockCircleOutlined />, text: 'Queued' },
      running: { color: 'processing', icon: <ReloadOutlined spin />, text: 'Running' },
      success: { color: 'success', icon: <CheckCircleOutlined />, text: 'Success' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Failed' },
      cancelled: { color: 'default', icon: <CloseCircleOutlined />, text: 'Cancelled' },
      paused: { color: 'warning', icon: <PauseCircleOutlined />, text: 'Paused' },
    };

    const config = statusConfig[state] || statusConfig.queued;
    return (
      <Badge
        status={config.color as any}
        text={
          <Space size={4}>
            {config.icon}
            {config.text}
          </Space>
        }
      />
    );
  };

  // Run table columns
  const runColumns: ColumnsType<DAGRun> = [
    {
      title: 'Run ID',
      dataIndex: 'run_id',
      key: 'run_id',
      ellipsis: true,
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => getRunStatusBadge(state),
    },
    {
      title: 'Execution Date',
      dataIndex: 'execution_date',
      key: 'execution_date',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: 'Start Time',
      dataIndex: 'start_date',
      key: 'start_date',
      render: (date: string) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: 'End Time',
      dataIndex: 'end_date',
      key: 'end_date',
      render: (date: string) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number) =>
        duration ? `${Math.round(duration)}s` : '-',
    },
    {
      title: 'Type',
      dataIndex: 'run_type',
      key: 'run_type',
      render: (type: string) => (
        <Tag color={type === 'manual' ? 'blue' : 'green'}>{type}</Tag>
      ),
    },
  ];

  // Calculate statistics
  const stats = {
    total: dags.length,
    active: dags.filter((d) => d.is_active && !d.is_paused).length,
    paused: dags.filter((d) => d.is_paused).length,
  };

  return (
    <div style={{ padding: '24px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col>
            <Space direction="vertical" size={0}>
              <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
                Workflows
              </h1>
              <span style={{ color: '#999' }}>
                Manage and monitor your workflow DAGs
              </span>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalOpen(true)}
            >
              New Workflow
            </Button>
          </Col>
        </Row>
      </div>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Workflows"
              value={stats.total}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Active"
              value={stats.active}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Paused"
              value={stats.paused}
              valueStyle={{ color: '#faad14' }}
              prefix={<PauseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: '16px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input
              placeholder="Search workflows..."
              prefix={<FilterOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              style={{ maxWidth: 300 }}
            />
          </Col>
          <Col>
            <Select
              placeholder="Status"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">All Status</Select.Option>
              <Select.Option value="active">Active</Select.Option>
              <Select.Option value="paused">Paused</Select.Option>
              <Select.Option value="inactive">Inactive</Select.Option>
            </Select>
          </Col>
          <Col>
            <Select
              placeholder="Tags"
              value={tagFilter}
              onChange={setTagFilter}
              style={{ width: 150 }}
              allowClear
            >
              <Select.Option value="all">All Tags</Select.Option>
              {allTags.map((tag) => (
                <Select.Option key={tag} value={tag}>
                  {tag}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchDags()}
              loading={loading}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card
        bodyStyle={{ padding: 0 }}
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
      >
        <Table
          columns={columns}
          dataSource={filteredDags}
          rowKey="dag_id"
          loading={loading}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} workflows`,
          }}
          scroll={{ y: 'calc(100vh - 520px)' }}
        />
      </Card>

      {/* Create Workflow Modal */}
      <Modal
        title="Create New Workflow"
        open={createModalOpen}
        onOk={handleCreateDag}
        onCancel={() => {
          setCreateModalOpen(false);
          form.resetFields();
        }}
        okText="Create & Edit"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="Workflow ID"
            name="dag_id"
            rules={[
              { required: true, message: 'Please enter a workflow ID' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: 'Only letters, numbers, and underscores' },
            ]}
          >
            <Input placeholder="my_workflow" />
          </Form.Item>
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="My Workflow" />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input.TextArea rows={3} placeholder="Describe your workflow..." />
          </Form.Item>
          <Form.Item label="Schedule (Cron)" name="schedule_interval">
            <Input placeholder="0 0 * * *" />
          </Form.Item>
          <Form.Item label="Tags" name="tags">
            <Select mode="tags" placeholder="Add tags..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Runs Modal */}
      <Modal
        title="Workflow Runs"
        open={runsModalOpen}
        onCancel={() => setRunsModalOpen(false)}
        footer={null}
        width={1000}
      >
        <Table
          columns={runColumns}
          dataSource={dagRuns}
          rowKey="run_id"
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Modal>
    </div>
  );
};

export default WorkflowListPage;
