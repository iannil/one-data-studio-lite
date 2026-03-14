/**
 * Notebook Workspace Page
 *
 * Embedded Jupyter Lab iframe for notebook development.
 */

import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Spin,
  Alert,
  Typography,
  Dropdown,
  Progress,
  Tag,
} from 'antd';
import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  ReloadOutlined,
  HomeOutlined,
  ExpandOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNotebookStore } from '@/stores/notebook';

const { Text } = Typography;

const NotebookWorkspacePage: React.FC = () => {
  const { user } = useNotebookStore();
  const { userId, serverName } = useParams();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const {
    notebooks,
    fetchNotebooks,
    startNotebook,
  } = useNotebookStore();

  const notebook = notebooks.find(
    (nb) => nb.user === userId && nb.name === (serverName || 'default')
  );

  useEffect(() => {
    fetchNotebooks();
  }, [userId, serverName]);

  useEffect(() => {
    if (notebook && notebook.state === 'stopped') {
      // Start the notebook
      handleStart();
    } else if (notebook && notebook.url) {
      setLoading(false);
    }
  }, [notebook]);

  const handleStart = async () => {
    setLoading(true);
    setStatusMessage('Starting notebook server...');
    setProgress(10);

    try {
      await startNotebook(userId!, serverName || '');

      // Poll for notebook to be ready
      const interval = setInterval(async () => {
        setProgress((prev) => Math.min(prev + 10, 90));
        await fetchNotebooks();

        const updated = notebooks.find(
          (nb) => nb.user === userId && nb.name === (serverName || 'default')
        );

        if (updated?.url) {
          clearInterval(interval);
          setProgress(100);
          setStatusMessage('Notebook is ready!');
          setTimeout(() => setLoading(false), 500);
        }
      }, 2000);

      return () => clearInterval(interval);
    } catch (error) {
      setStatusMessage('Failed to start notebook');
      setProgress(0);
      setLoading(false);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const reloadIframe = () => {
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const handleFullscreenChange = () => {
    setIsFullscreen(!!document.fullscreenElement);
  };

  useEffect(() => {
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const getJupyterUrl = () => {
    if (!notebook?.url) return '';
    // The URL might need to be adjusted for embedding
    return notebook.url;
  };

  return (
    <div
      ref={containerRef}
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: '#f0f0f0',
      }}
    >
      {/* Toolbar */}
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
            icon={<HomeOutlined />}
            href="/notebook"
            title="Back to Notebooks"
          >
            Notebooks
          </Button>
          <Text strong>
            {notebook?.name === 'default' ? 'Main Notebook' : notebook?.name}
          </Text>
          {notebook && (
            <Tag color={notebook.state === 'running' ? 'success' : 'default'}>
              {notebook.state}
            </Tag>
          )}
        </Space>

        <Space>
          {loading && (
            <Progress
              type="circle"
              percent={progress}
              width={40}
              format={(percent) => `${percent}%`}
            />
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={reloadIframe}
            title="Reload"
          >
            Reload
          </Button>
          <Button
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={toggleFullscreen}
            title="Toggle Fullscreen"
          >
            {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          </Button>
        </Space>
      </div>

      {/* Content */}
      <div style={{ flex: 1, position: 'relative' }}>
        {loading ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            <Spin size="large" />
            <Text style={{ marginTop: '16px', color: '#666' }}>
              {statusMessage}
            </Text>
            <Progress percent={progress} style={{ width: '300px', marginTop: '16px' }} />
            {progress < 30 && (
              <Alert
                message="Starting a notebook server may take 1-2 minutes. Please be patient."
                type="info"
                showIcon
                style={{ marginTop: '24px', maxWidth: '400px' }}
              />
            )}
          </div>
        ) : notebook?.url ? (
          <iframe
            ref={iframeRef}
            src={getJupyterUrl()}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
            }}
            title="Jupyter Lab"
            allow="clipboard-read; clipboard-write; accelerometer; gyroscope; microphone; camera;"
            allowFullScreen
          />
        ) : (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            <Alert
              message="Notebook Not Available"
              description="The notebook server could not be reached. Please try starting it again."
              type="error"
              showIcon
              action={
                <Button type="primary" onClick={handleStart}>
                  Start Notebook
                </Button>
              }
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default NotebookWorkspacePage;
