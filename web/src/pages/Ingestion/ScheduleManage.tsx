import React, { useEffect, useState } from 'react';
import { Card, Table, Select, Tag, message, Typography, Space, Button, Spin, Alert } from 'antd';
import { ScheduleOutlined, ReloadOutlined } from '@ant-design/icons';
import { getProjects, getProcessDefinitions, getSchedules, updateScheduleState } from '../../api/dolphinscheduler';

const { Title } = Typography;

const ScheduleManage: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [definitions, setDefinitions] = useState<any[]>([]);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    setError(null);
    try {
      const data = await getProjects();
      const list = data?.data?.totalList || data?.data || [];
      setProjects(Array.isArray(list) ? list : []);
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 401) {
        setError('认证失败，请重新登录');
      } else if (status === 503 || status === 502) {
        setError('DolphinScheduler 服务不可用，请确认服务已启动');
      } else {
        setError('获取项目列表失败，请检查 DolphinScheduler 服务状态');
      }
    }
  };

  const fetchDefinitions = async (projectCode: string) => {
    setLoading(true);
    try {
      const data = await getProcessDefinitions(projectCode, { pageNo: 1, pageSize: 50 });
      setDefinitions(data?.data?.totalList || data?.data || []);
    } catch {
      message.error('获取流程定义失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedules = async (projectCode: string) => {
    try {
      const data = await getSchedules(projectCode);
      setSchedules(data?.data?.totalList || data?.data || []);
    } catch {
      // 调度可能为空
      setSchedules([]);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchDefinitions(selectedProject);
      fetchSchedules(selectedProject);
    }
  }, [selectedProject]);

  const handleToggleSchedule = async (scheduleId: number, currentState: string) => {
    const newState = currentState === 'ONLINE' ? 'OFFLINE' : 'ONLINE';
    try {
      await updateScheduleState(selectedProject, scheduleId, newState);
      message.success(`调度已${newState === 'ONLINE' ? '上线' : '下线'}`);
      fetchSchedules(selectedProject);
    } catch {
      message.error('操作失败');
    }
  };

  const defColumns = [
    { title: '流程名称', dataIndex: 'name', key: 'name' },
    { title: '流程编码', dataIndex: 'code', key: 'code' },
    {
      title: '上线状态',
      dataIndex: 'releaseState',
      key: 'releaseState',
      render: (state: string) => (
        <Tag color={state === 'ONLINE' ? 'green' : 'default'}>{state === 'ONLINE' ? '已上线' : '未上线'}</Tag>
      ),
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true, render: (t: string) => t || '-' },
    {
      title: '更新时间',
      dataIndex: 'updateTime',
      key: 'updateTime',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ];

  const scheduleColumns = [
    { title: '调度 ID', dataIndex: 'id', key: 'id' },
    { title: '流程名称', dataIndex: 'processDefinitionName', key: 'processDefinitionName' },
    { title: 'Crontab', dataIndex: 'crontab', key: 'crontab' },
    {
      title: '状态',
      dataIndex: 'releaseState',
      key: 'releaseState',
      render: (state: string) => (
        <Tag color={state === 'ONLINE' ? 'green' : 'default'}>{state === 'ONLINE' ? '运行中' : '已停止'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Button
          size="small"
          type={record.releaseState === 'ONLINE' ? 'default' : 'primary'}
          onClick={() => handleToggleSchedule(record.id, record.releaseState)}
        >
          {record.releaseState === 'ONLINE' ? '下线' : '上线'}
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <ScheduleOutlined /> 任务调度管理
      </Title>
      <Space style={{ width: '100%', display: 'flex', flexDirection: 'column' }} size="middle">
        {error && (
          <Alert
            message={error}
            type="warning"
            showIcon
            closable
            onClose={() => setError(null)}
          />
        )}
        <Card size="small">
          <Space>
            <span>选择项目：</span>
            <Select
              placeholder="请选择项目"
              style={{ width: 300 }}
              value={selectedProject || undefined}
              onChange={setSelectedProject}
              options={projects.map((p) => ({ label: p.name, value: String(p.code) }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchProjects}>刷新</Button>
          </Space>
        </Card>

        {selectedProject && (
          <>
            <Card title="流程定义" size="small">
              {loading ? (
                <Spin />
              ) : (
                <Table
                  columns={defColumns}
                  dataSource={definitions.map((d, i) => ({ ...d, key: d.code || i }))}
                  pagination={{ pageSize: 10 }}
                  size="small"
                />
              )}
            </Card>

            <Card title="调度管理" size="small">
              <Table
                columns={scheduleColumns}
                dataSource={schedules.map((s, i) => ({ ...s, key: s.id || i }))}
                pagination={{ pageSize: 10 }}
                size="small"
              />
            </Card>
          </>
        )}
      </Space>
    </div>
  );
};

export default ScheduleManage;
