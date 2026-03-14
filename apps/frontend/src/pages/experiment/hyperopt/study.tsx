/**
 * Hyperparameter Optimization Study Detail Page
 *
 * Shows study details with trials list, optimization history chart, and best parameters.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Tag,
  Button,
  Space,
  Tooltip,
  Statistic,
  Progress,
  message,
  Tabs,
  Descriptions,
  Alert,
  Divider,
  Badge,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  TrophyOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useHyperoptStore } from '@/stores/hyperopt';
import type { OptimizationStudy, Trial, StudyStatus } from '@/stores/hyperopt';
import ReactECharts from 'echarts-for-react';

const { TabPane } = Tabs;

const StudyDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const { studyId } = useParams<{ studyId: string }>();

  const {
    currentStudy,
    trials,
    history,
    loading,
    fetchStudy,
    fetchTrials,
    fetchHistory,
    deleteStudy,
    clearError,
  } = useHyperoptStore();

  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (studyId) {
      fetchStudy(studyId);
      fetchTrials(studyId);
      fetchHistory(studyId);
    }
  }, [studyId, fetchStudy, fetchTrials, fetchHistory]);

  const getStatusBadge = (status: StudyStatus) => {
    const statusConfig: Record<StudyStatus, { color: string; icon: React.ReactNode; text: string }> = {
      created: { color: 'default', icon: <ExperimentOutlined />, text: 'Created' },
      running: { color: 'processing', icon: <ThunderboltOutlined spin />, text: 'Running' },
      completed: { color: 'success', icon: <CheckCircleOutlined />, text: 'Completed' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Failed' },
      cancelled: { color: 'default', icon: <PauseCircleOutlined />, text: 'Cancelled' },
    };

    const config = statusConfig[status];
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

  const getTrialStatusTag = (status: string) => {
    const colors: Record<string, string> = {
      running: 'blue',
      completed: 'green',
      failed: 'red',
      pruned: 'orange',
    };
    return <Tag color={colors[status] || 'default'}>{status}</Tag>;
  };

  // Generate optimization history chart option
  const getHistoryChartOption = () => {
    if (!history || !history.trials) {
      return {};
    }

    const trials = history.trials
      .filter((t: any) => t.status === 'completed')
      .sort((a: any, b: any) => a.trial_number - b.trial_number);

    const bestValues: number[] = [];
    let currentBest = history.direction === 'maximize' ? -Infinity : Infinity;

    trials.forEach((trial: any) => {
      if (history.direction === 'maximize') {
        currentBest = Math.max(currentBest, trial.value);
      } else {
        currentBest = Math.min(currentBest, trial.value);
      }
      bestValues.push(currentBest);
    });

    return {
      title: {
        text: 'Optimization History',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
      },
      xAxis: {
        type: 'category',
        data: trials.map((t: any) => t.trial_number),
        name: 'Trial',
      },
      yAxis: {
        type: 'value',
        name: history.metric,
      },
      series: [
        {
          name: 'Objective Value',
          type: 'scatter',
          data: trials.map((t: any) => [t.trial_number, t.value]),
          itemStyle: {
            color: '#1890ff',
          },
        },
        {
          name: 'Best Value',
          type: 'line',
          data: bestValues,
          smooth: true,
          itemStyle: {
            color: '#52c41a',
          },
          lineStyle: {
            width: 2,
          },
        },
      ],
    };
  };

  // Generate parameter importance chart option
  const getImportanceChartOption = () => {
    // Placeholder - would compute from actual parameter importance
    return {
      title: {
        text: 'Parameter Importance',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
      },
      xAxis: {
        type: 'value',
      },
      yAxis: {
        type: 'category',
        data: ['learning_rate', 'batch_size', 'weight_decay', 'dropout', 'layers'],
      },
      series: [
        {
          type: 'bar',
          data: [0.85, 0.62, 0.45, 0.32, 0.18],
          itemStyle: {
            color: '#1890ff',
          },
        },
      ],
    };
  };

  // Parallel coordinates plot for hyperparameter relationships
  const getParallelChartOption = () => {
    if (!history || !history.trials) {
      return {};
    }

    const trials = history.trials
      .filter((t: any) => t.status === 'completed')
      .slice(0, 50); // Limit for performance

    // Extract unique parameter values
    const paramNames = new Set<string>();
    trials.forEach((trial: any) => {
      Object.keys(trial.params || {}).forEach((key) => paramNames.add(key));
    });

    const dimensions = ['value', ...Array.from(paramNames)];

    return {
      title: {
        text: 'Parallel Coordinates Plot',
        left: 'center',
      },
      tooltip: {
        trigger: 'item',
      },
      parallelAxis: dimensions.map((dim) => ({
        dim: dimensions.indexOf(dim),
        name: dim,
        type: dim === 'value' ? 'value' : 'category',
      })),
      parallel: {
        left: '5%',
        right: '13%',
        bottom: 100,
        parallelAxisDefault: {
          type: 'category',
          name: 'Param',
          nameLocation: 'end',
          nameGap: 20,
        },
      },
      series: [
        {
          name: 'Trials',
          type: 'parallel',
          lineStyle: {
            width: 1,
            opacity: 0.5,
          },
          data: trials.map((t: any) => [
            t.value,
            ...Array.from(paramNames).map((p) => t.params?.[p] || '-'),
          ]),
        },
      ],
    };
  };

  const trialColumns = [
    {
      title: 'Trial',
      dataIndex: 'trial_number',
      key: 'trial_number',
      width: 80,
      render: (num: number, trial: Trial) => (
        <a onClick={() => {/* Navigate to trial detail */}}>
          #{num}
        </a>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getTrialStatusTag(status),
    },
    {
      title: 'Objective Value',
      dataIndex: 'value',
      key: 'value',
      width: 120,
      render: (value: number) => (
        <Tag color={currentStudy?.direction === 'maximize' ? 'green' : 'orange'}>
          {typeof value === 'number' ? value.toFixed(6) : value}
        </Tag>
      ),
    },
    {
      title: 'Parameters',
      key: 'params',
      ellipsis: true,
      render: (_: any, trial: Trial) => {
        const params = trial.params || {};
        const entries = Object.entries(params).slice(0, 3);
        return (
          <Space size="small" wrap>
            {entries.map(([key, value]) => (
              <Tag key={key}>
                {key}: {String(value).slice(0, 10)}
              </Tag>
            ))}
            {Object.keys(params).length > 3 && (
              <Tag>+{Object.keys(params).length - 3}</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 100,
      render: (_: any, trial: Trial) => {
        if (!trial.start_time || !trial.end_time) return '-';
        const duration = new Date(trial.end_time).getTime() - new Date(trial.start_time).getTime();
        return `${Math.floor(duration / 1000)}s`;
      },
    },
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
  ];

  const study = currentStudy;
  const bestTrial = study?.best_trial;

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/experiments/hyperopt')}
          >
            Back
          </Button>
        </Col>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>
            {study?.name}
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            {studyId}
          </p>
        </Col>
        <Col>
          <Space>
            {study?.status === 'created' && (
              <Button type="primary" icon={<PlayCircleOutlined />}>
                Start Optimization
              </Button>
            )}
            {study?.status === 'running' && (
              <Button danger icon={<PauseCircleOutlined />}>
                Stop Study
              </Button>
            )}
            <Button icon={<SyncOutlined />} onClick={() => fetchStudy(studyId!)}>
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="Status"
              value=""
              prefix={study ? getStatusBadge(study.status) : '-'}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Best Value"
              value={study?.best_value || '-'}
              precision={4}
              valueStyle={{ color: study?.direction === 'maximize' ? '#52c41a' : '#faad14' }}
              prefix={<TrophyOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Completed Trials"
              value={study?.completed_trials || 0}
              suffix={`/ ${study?.n_trials || 0}`}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Progress"
              value={study ? Math.round(study.progress * 100) : 0}
              suffix="%"
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Sampler"
              value={study?.sampler || '-'}
              valueStyle={{ fontSize: '18px', textTransform: 'uppercase' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Direction"
              value={study?.direction || '-'}
              valueStyle={{
                fontSize: '18px',
                textTransform: 'capitalize',
                color: study?.direction === 'maximize' ? '#52c41a' : '#faad14',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Content Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="Overview" key="overview">
            <Row gutter={16}>
              <Col span={12}>
                <Card title="Optimization History" extra={<LineChartOutlined />}>
                  <ReactECharts
                    option={getHistoryChartOption()}
                    style={{ height: '300px' }}
                    opts={{ renderer: 'svg' }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="Parameter Importance" extra={<BarChartOutlined />}>
                  <ReactECharts
                    option={getImportanceChartOption()}
                    style={{ height: '300px' }}
                    opts={{ renderer: 'svg' }}
                  />
                </Card>
              </Col>
            </Row>

            {bestTrial && (
              <Card
                title="Best Trial"
                style={{ marginTop: 16 }}
                extra={<Tag color="gold">Best Result</Tag>}
              >
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="Trial Number">
                    #{bestTrial.trial_number}
                  </Descriptions.Item>
                  <Descriptions.Item label="Objective Value">
                    <Tag color="green">{bestTrial.value?.toFixed(6)}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Start Time" span={2}>
                    {bestTrial.start_time ? new Date(bestTrial.start_time).toLocaleString() : '-'}
                  </Descriptions.Item>
                </Descriptions>

                <Divider orientation="left">Best Hyperparameters</Divider>

                <Row gutter={[16, 8]}>
                  {Object.entries(bestTrial.params || {}).map(([key, value]) => (
                    <Col span={8} key={key}>
                      <Space>
                        <strong>{key}:</strong>
                        <Tag>{String(value)}</Tag>
                      </Space>
                    </Col>
                  ))}
                </Row>
              </Card>
            )}
          </TabPane>

          <TabPane tab="Trials" key="trials">
            <Table
              columns={trialColumns}
              dataSource={trials}
              rowKey="trial_id"
              loading={loading}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `Total ${total} trials`,
              }}
            />
          </TabPane>

          <TabPane tab="Parallel Plot" key="parallel">
            <Card>
              <Alert
                message="Parallel Coordinates Plot"
                description="Visualize relationships between hyperparameters and objective values."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <ReactECharts
                option={getParallelChartOption()}
                style={{ height: '500px' }}
                opts={{ renderer: 'svg' }}
              />
            </Card>
          </TabPane>

          <TabPane tab="Settings" key="settings">
            <Card title="Study Configuration">
              {study && (
                <Descriptions column={2} bordered>
                  <Descriptions.Item label="Study ID" span={2}>
                    {study.study_id}
                  </Descriptions.Item>
                  <Descriptions.Item label="Name" span={2}>
                    {study.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="Metric">
                    {study.metric}
                  </Descriptions.Item>
                  <Descriptions.Item label="Direction">
                    <Tag color={study.direction === 'maximize' ? 'green' : 'orange'}>
                      {study.direction}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Sampler">
                    {study.sampler}
                  </Descriptions.Item>
                  <Descriptions.Item label="Pruner">
                    {study.pruner}
                  </Descriptions.Item>
                  <Descriptions.Item label="Number of Trials">
                    {study.n_trials}
                  </Descriptions.Item>
                  <Descriptions.Item label="Parallel Jobs">
                    {study.n_jobs}
                  </Descriptions.Item>
                  <Descriptions.Item label="Warmup Steps">
                    {study.n_warmup_steps}
                  </Descriptions.Item>
                  <Descriptions.Item label="Early Stopping Rounds">
                    {study.early_stopping_rounds}
                  </Descriptions.Item>
                  <Descriptions.Item label="Created At">
                    {new Date(study.created_at).toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="Start Time">
                    {study.start_time ? new Date(study.start_time).toLocaleString() : '-'}
                  </Descriptions.Item>
                </Descriptions>
              )}
            </Card>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default StudyDetailPage;
