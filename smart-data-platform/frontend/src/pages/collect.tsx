'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Card,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tag,
  Popconfirm,
  Typography,
  Switch,
  Tooltip,
  List,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  ClockCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { collectApi, sourcesApi } from '@/services/api';
import type { DataSource } from '@/types';

const { Title, Text } = Typography;

interface CollectTask {
  id: string;
  name: string;
  description?: string;
  source_id: string;
  source_table?: string;
  source_query?: string;
  target_table: string;
  schedule_cron?: string;
  is_active: boolean;
  is_incremental: boolean;
  incremental_field?: string;
  status: string;
  last_run_at?: string;
  last_success_at?: string;
  last_error?: string;
  created_at: string;
}

interface ScheduleInfo {
  job_id: string;
  task_id: string;
  task_name: string;
  cron_expression?: string;
  is_scheduled: boolean;
  is_active: boolean;
  status: string;
  next_run_time?: string;
  last_run_at?: string;
  last_success_at?: string;
  last_error?: string;
}

const CRON_PRESETS = [
  { label: '每分钟', value: '* * * * *' },
  { label: '每5分钟', value: '*/5 * * * *' },
  { label: '每小时', value: '0 * * * *' },
  { label: '每天凌晨', value: '0 0 * * *' },
  { label: '每天上午9点', value: '0 9 * * *' },
  { label: '每周一凌晨', value: '0 0 * * 1' },
  { label: '每月1日凌晨', value: '0 0 1 * *' },
];

export default function CollectPage() {
  const [tasks, setTasks] = useState<CollectTask[]>([]);
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<CollectTask | null>(null);
  const [form] = Form.useForm();

  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [scheduleTask, setScheduleTask] = useState<CollectTask | null>(null);
  const [scheduleInfo, setScheduleInfo] = useState<ScheduleInfo | null>(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleForm] = Form.useForm();
  const [previewTimes, setPreviewTimes] = useState<string[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await collectApi.listTasks();
      setTasks(response.data);
    } catch (error) {
      message.error('获取采集任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchSources = async () => {
    try {
      const response = await sourcesApi.list();
      setSources(response.data);
    } catch (error) {
      console.error('Failed to fetch sources');
    }
  };

  useEffect(() => {
    fetchTasks();
    fetchSources();
  }, []);

  const handleCreate = () => {
    setEditingTask(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record: CollectTask) => {
    setEditingTask(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await collectApi.deleteTask(id);
      message.success('删除成功');
      fetchTasks();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleRun = async (id: string) => {
    try {
      await collectApi.runTask(id);
      message.success('任务已启动');
      fetchTasks();
    } catch (error) {
      message.error('任务启动失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingTask) {
        await collectApi.updateTask(editingTask.id, values);
        message.success('更新成功');
      } else {
        await collectApi.createTask(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchTasks();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleOpenSchedule = async (task: CollectTask) => {
    setScheduleTask(task);
    setScheduleModalOpen(true);
    setScheduleLoading(true);
    setPreviewTimes([]);

    try {
      const response = await collectApi.getSchedule(task.id);
      setScheduleInfo(response.data);
      if (response.data.cron_expression) {
        scheduleForm.setFieldsValue({ cron_expression: response.data.cron_expression });
        handlePreviewSchedule(response.data.cron_expression);
      }
    } catch (error) {
      setScheduleInfo(null);
    } finally {
      setScheduleLoading(false);
    }
  };

  const handlePreviewSchedule = async (cronExpression: string) => {
    if (!cronExpression) {
      setPreviewTimes([]);
      return;
    }

    setPreviewLoading(true);
    try {
      const response = await collectApi.previewSchedule(cronExpression, 5);
      setPreviewTimes(response.data.next_run_times || []);
    } catch (error) {
      setPreviewTimes([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveSchedule = async () => {
    if (!scheduleTask) return;

    const values = await scheduleForm.validateFields();
    setScheduleLoading(true);

    try {
      await collectApi.addSchedule(scheduleTask.id, values.cron_expression);
      message.success('调度已设置');
      setScheduleModalOpen(false);
      fetchTasks();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '设置调度失败');
    } finally {
      setScheduleLoading(false);
    }
  };

  const handleRemoveSchedule = async () => {
    if (!scheduleTask) return;

    setScheduleLoading(true);
    try {
      await collectApi.removeSchedule(scheduleTask.id);
      message.success('调度已移除');
      setScheduleModalOpen(false);
      fetchTasks();
    } catch (error) {
      message.error('移除调度失败');
    } finally {
      setScheduleLoading(false);
    }
  };

  const handlePauseSchedule = async (taskId: string) => {
    try {
      await collectApi.pauseSchedule(taskId);
      message.success('调度已暂停');
      fetchTasks();
    } catch (error) {
      message.error('暂停调度失败');
    }
  };

  const handleResumeSchedule = async (taskId: string) => {
    try {
      await collectApi.resumeSchedule(taskId);
      message.success('调度已恢复');
      fetchTasks();
    } catch (error) {
      message.error('恢复调度失败');
    }
  };

  const columns: ColumnsType<CollectTask> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '目标表',
      dataIndex: 'target_table',
      key: 'target_table',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          paused: 'warning',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
    {
      title: '增量同步',
      dataIndex: 'is_incremental',
      key: 'is_incremental',
      render: (val) => (val ? <Tag color="blue">增量</Tag> : <Tag>全量</Tag>),
    },
    {
      title: '调度',
      dataIndex: 'schedule_cron',
      key: 'schedule_cron',
      render: (cron, record) => {
        if (!cron) return <Text type="secondary">未设置</Text>;
        return (
          <Space>
            <Tag color={record.is_active ? 'green' : 'orange'} icon={<ClockCircleOutlined />}>
              {cron}
            </Tag>
            {!record.is_active && <Tag color="warning">已暂停</Tag>}
          </Space>
        );
      },
    },
    {
      title: '最后运行',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      render: (date) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="执行">
            <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleRun(record.id)} />
          </Tooltip>
          <Tooltip title="调度设置">
            <Button
              size="small"
              icon={<ClockCircleOutlined />}
              onClick={() => handleOpenSchedule(record)}
              type={record.schedule_cron ? 'primary' : 'default'}
            />
          </Tooltip>
          {record.schedule_cron && record.is_active && (
            <Tooltip title="暂停调度">
              <Button
                size="small"
                icon={<PauseCircleOutlined />}
                onClick={() => handlePauseSchedule(record.id)}
              />
            </Tooltip>
          )}
          {record.schedule_cron && !record.is_active && (
            <Tooltip title="恢复调度">
              <Button
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleResumeSchedule(record.id)}
              />
            </Tooltip>
          )}
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const isIncremental = Form.useWatch('is_incremental', form);
  const cronExpression = Form.useWatch('cron_expression', scheduleForm);

  useEffect(() => {
    if (cronExpression && scheduleModalOpen) {
      const timer = setTimeout(() => {
        handlePreviewSchedule(cronExpression);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [cronExpression, scheduleModalOpen]);

  return (
    <AuthGuard>
      <Card
        title={<Title level={4}>数据采集</Title>}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建任务
          </Button>
        }
      >
        <Table columns={columns} dataSource={tasks} rowKey="id" loading={loading} />
      </Card>

      <Modal
        title={editingTask ? '编辑采集任务' : '创建采集任务'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="source_id" label="数据源" rules={[{ required: true }]}>
            <Select
              options={sources.map((s) => ({ value: s.id, label: s.name }))}
              placeholder="选择数据源"
            />
          </Form.Item>
          <Form.Item name="source_table" label="源表名">
            <Input placeholder="输入源表名" />
          </Form.Item>
          <Form.Item name="source_query" label="自定义 SQL (可选)">
            <Input.TextArea rows={3} placeholder="SELECT * FROM ..." />
          </Form.Item>
          <Form.Item name="target_table" label="目标表名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="is_incremental" label="增量同步" valuePropName="checked">
            <Switch />
          </Form.Item>
          {isIncremental && (
            <Form.Item name="incremental_field" label="增量字段" rules={[{ required: true }]}>
              <Input placeholder="例如: updated_at, id" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title={
          <Space>
            <ClockCircleOutlined />
            调度设置
            {scheduleTask && <Tag>{scheduleTask.name}</Tag>}
          </Space>
        }
        open={scheduleModalOpen}
        onCancel={() => {
          setScheduleModalOpen(false);
          setScheduleTask(null);
          setScheduleInfo(null);
          setPreviewTimes([]);
          scheduleForm.resetFields();
        }}
        footer={
          <Space>
            {scheduleInfo?.is_scheduled && (
              <Popconfirm title="确定移除调度?" onConfirm={handleRemoveSchedule}>
                <Button danger loading={scheduleLoading}>
                  移除调度
                </Button>
              </Popconfirm>
            )}
            <Button onClick={() => setScheduleModalOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSaveSchedule} loading={scheduleLoading}>
              保存调度
            </Button>
          </Space>
        }
        width={600}
      >
        {scheduleLoading && !scheduleInfo ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : (
          <>
            {scheduleInfo?.is_scheduled && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">状态: </Text>
                    <Tag color={scheduleInfo.is_active ? 'green' : 'orange'}>
                      {scheduleInfo.is_active ? '运行中' : '已暂停'}
                    </Tag>
                  </div>
                  {scheduleInfo.next_run_time && (
                    <div>
                      <Text type="secondary">下次执行: </Text>
                      <Text strong>{new Date(scheduleInfo.next_run_time).toLocaleString()}</Text>
                    </div>
                  )}
                  {scheduleInfo.last_run_at && (
                    <div>
                      <Text type="secondary">上次执行: </Text>
                      <Text>{new Date(scheduleInfo.last_run_at).toLocaleString()}</Text>
                    </div>
                  )}
                  {scheduleInfo.last_error && (
                    <div>
                      <Text type="secondary">上次错误: </Text>
                      <Text type="danger">{scheduleInfo.last_error}</Text>
                    </div>
                  )}
                </Space>
              </Card>
            )}

            <Form form={scheduleForm} layout="vertical">
              <Form.Item
                name="cron_expression"
                label="Cron 表达式"
                rules={[{ required: true, message: '请输入 Cron 表达式' }]}
                extra="格式: 分 时 日 月 周 (如: 0 0 * * * 表示每天凌晨)"
              >
                <Input placeholder="0 0 * * *" />
              </Form.Item>

              <Form.Item label="快速选择">
                <Space wrap>
                  {CRON_PRESETS.map((preset) => (
                    <Button
                      key={preset.value}
                      size="small"
                      onClick={() => {
                        scheduleForm.setFieldsValue({ cron_expression: preset.value });
                        handlePreviewSchedule(preset.value);
                      }}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </Space>
              </Form.Item>
            </Form>

            {(previewLoading || previewTimes.length > 0) && (
              <Card size="small" title="预计执行时间">
                {previewLoading ? (
                  <Spin size="small" />
                ) : (
                  <List
                    size="small"
                    dataSource={previewTimes}
                    renderItem={(time, index) => (
                      <List.Item>
                        <Space>
                          <Tag color="blue">{index + 1}</Tag>
                          {new Date(time).toLocaleString()}
                        </Space>
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            )}
          </>
        )}
      </Modal>
    </AuthGuard>
  );
}
