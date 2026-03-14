/**
 * Notebook Card Component
 *
 * Displays a notebook server as a card with status and actions.
 */

import React from 'react';
import { Card, Tag, Space, Typography, Progress, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  CodeOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { Notebook } from '@/types/notebook';

const { Text } = Typography;

interface NotebookCardProps {
  notebook: Notebook;
  onStart?: () => void;
  onStop?: () => void;
  onDelete?: () => void;
  onOpen?: () => void;
  loading?: boolean;
}

const NotebookCard: React.FC<NotebookCardProps> = ({
  notebook,
  onStart,
  onStop,
  onDelete,
  onOpen,
  loading = false,
}) => {
  const isRunning = notebook.state === 'running';
  const isPending = notebook.state === 'pending';
  const isStopped = notebook.state === 'stopped';

  const getImageIcon = () => {
    const icons: Record<string, React.ReactNode> = {
      pytorch: <RocketOutlined style={{ color: '#EE4C2C', fontSize: '24px' }} />,
      tensorflow: <RocketOutlined style={{ color: '#FF6F00', fontSize: '24px' }} />,
      sklearn: <CodeOutlined style={{ color: '#F7931E', fontSize: '24px' }} />,
      nlp: <CodeOutlined style={{ color: '#76B900', fontSize: '24px' }} />,
      minimal: <CodeOutlined style={{ fontSize: '24px' }} />,
    };
    return icons[notebook.image] || <CodeOutlined style={{ fontSize: '24px' }} />;
  };

  const getStateColor = () => {
    const colors: Record<string, string> = {
      running: 'success',
      stopped: 'default',
      pending: 'processing',
      error: 'error',
    };
    return colors[notebook.state] || 'default';
  };

  const getStateText = () => {
    const texts: Record<string, string> = {
      running: 'Running',
      stopped: 'Stopped',
      pending: 'Starting...',
      error: 'Error',
    };
    return texts[notebook.state] || notebook.state;
  };

  return (
    <Card
      hoverable
      style={{ width: '100%' }}
      actions={[
        isRunning ? (
          <Tooltip title="Open Notebook">
            <PlayCircleOutlined key="open" onClick={onOpen} />
          </Tooltip>
        ) : (
          <Tooltip title={isStopped ? 'Start' : 'Starting...'}>
            <PlayCircleOutlined
              key="start"
              onClick={isStopped && !isPending ? onStart : undefined}
              style={{
                color: isStopped && !isPending ? '#52c41a' : undefined,
                opacity: isPending ? 0.5 : undefined,
              }}
            />
          </Tooltip>
        ),
        isRunning ? (
          <Tooltip title="Stop">
            <StopOutlined
              key="stop"
              onClick={onStop}
              style={{ color: '#ff4d4f' }}
            />
          </Tooltip>
        ) : undefined,
        <Tooltip title="Delete">
          <DeleteOutlined
            key="delete"
            onClick={onDelete}
            style={{ color: isStopped ? '#ff4d4f' : '#999' }}
          />
        </Tooltip>,
      ].filter(Boolean)}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Header with icon and name */}
        <Space>
          {getImageIcon()}
          <div>
            <Text strong>
              {notebook.name === 'default' ? 'Main Notebook' : notebook.name}
            </Text>
            <br />
            <Tag color={getStateColor()}>{getStateText()}</Tag>
          </div>
        </Space>

        {/* Resources */}
        <Space size="small">
          <Tag>{notebook.cpu_limit} CPU</Tag>
          <Tag>{notebook.mem_limit} RAM</Tag>
          {notebook.gpu_limit > 0 && <Tag color="blue">{notebook.gpu_limit} GPU</Tag>}
        </Space>

        {/* Last activity */}
        {notebook.last_activity && (
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Last active: {new Date(notebook.last_activity).toLocaleString()}
          </Text>
        )}

        {/* Progress when pending */}
        {isPending && (
          <Progress
            percent={50}
            status="active"
            size="small"
            showInfo={false}
          />
        )}
      </Space>
    </Card>
  );
};

export default NotebookCard;
