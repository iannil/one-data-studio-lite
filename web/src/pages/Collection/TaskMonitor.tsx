import React, { useEffect, useState } from 'react';
import { Card, Table, Select, Tag, message, Typography, Space, Button, Spin, Drawer, Alert } from 'antd';
import { MonitorOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import { getProjects, getTaskInstances, getTaskLog, type Project, type TaskInstance } from '../../api/dolphinscheduler';

const { Title } = Typography;

const stateColors: Record<string, string> = {
  SUCCESS: 'success',
  RUNNING_EXECUTION: 'processing',
  FAILURE: 'error',
  STOP: 'default',
  KILL: 'warning',
  PAUSE: 'warning',
  SUBMITTED_SUCCESS: 'blue',
};

const TaskMonitor: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [instances, setInstances] = useState<TaskInstance[]>([]);
  const [loading, setLoading] = useState(false);
  const [stateFilter, setStateFilter] = useState<string | undefined>(undefined);
  const [logDrawerVisible, setLogDrawerVisible] = useState(false);
  const [logContent, setLogContent] = useState('');
  const [loadingLog, setLoadingLog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    setError(null);
    try {
      const data = await getProjects();
      const list = data?.data?.totalList || data?.data || [];
      setProjects(Array.isArray(list) ? list : []);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError('认证失败，请重新登录');
      } else if (status === 503 || status === 502) {
        setError('DolphinScheduler 服务不可用，请确认服务已启动');
      } else {
        setError('获取项目列表失败，请检查 DolphinScheduler 服务状态');
      }
    }
  };

  const fetchInstances = async (projectCode: string, stateType?: string) => {
    setLoading(true);
    try {
      const data = await getTaskInstances(projectCode, {
        pageNo: 1,
        pageSize: 50,
        stateType,
      });
      setInstances(data?.data?.totalList || data?.data || []);
    } catch {
      message.error('获取任务实例失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchInstances(selectedProject, stateFilter);
    }
  }, [selectedProject, stateFilter]);

  const handleViewLog = async (taskInstanceId: number) => {
    setLogDrawerVisible(true);
    setLoadingLog(true);
    setLogContent('');
    try {
      const data = await getTaskLog(selectedProject, taskInstanceId);
      setLogContent(data?.data || data?.message || '无日志内容');
    } catch {
      setLogContent('获取日志失败');
    } finally {
      setLoadingLog(false);
    }
  };

  const columns = [
    { title: '实例 ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '任务名称', dataIndex: 'name', key: 'name' },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => (
        <Tag color={stateColors[state] || 'default'}>{state || '-'}</Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'startTime',
      key: 'startTime',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '结束时间',
      dataIndex: 'endTime',
      key: 'endTime',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      render: (t: string) => t || '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: TaskInstance) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewLog(record.id)}
        >
          日志
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <MonitorOutlined /> 任务监控日志
      </Title>
      {error && (
        <Alert
          message={error}
          type="warning"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}
      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <span>项目：</span>
          <Select
            placeholder="选择项目"
            style={{ width: 250 }}
            value={selectedProject || undefined}
            onChange={setSelectedProject}
            options={projects.map((p) => ({ label: p.name, value: String(p.code) }))}
          />
          <span>状态筛选：</span>
          <Select
            placeholder="全部"
            allowClear
            style={{ width: 150 }}
            value={stateFilter}
            onChange={setStateFilter}
          >
            <Select.Option value="SUCCESS">成功</Select.Option>
            <Select.Option value="FAILURE">失败</Select.Option>
            <Select.Option value="RUNNING_EXECUTION">运行中</Select.Option>
            <Select.Option value="STOP">停止</Select.Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => selectedProject && fetchInstances(selectedProject, stateFilter)}>
            刷新
          </Button>
        </Space>
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={instances.map((inst, i) => ({ ...inst, key: inst.id || i }))}
            pagination={{ pageSize: 15, showTotal: (total) => `共 ${total} 条` }}
            size="small"
          />
        )}
      </Card>

      <Drawer
        title="任务日志"
        open={logDrawerVisible}
        onClose={() => setLogDrawerVisible(false)}
        size="large"
      >
        {loadingLog ? (
          <Spin />
        ) : (
          <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 4, overflow: 'auto', fontSize: 12, maxHeight: 'calc(100vh - 120px)' }}>
            {logContent}
          </pre>
        )}
      </Drawer>
    </div>
  );
};

export default TaskMonitor;
