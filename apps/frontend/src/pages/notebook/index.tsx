/**
 * Notebook List Page
 *
 * Lists all notebook servers for the current user with actions to start, stop, and manage them.
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  message,
  Tooltip,
  Dropdown,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  ReloadOutlined,
  RocketOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { useNotebookStore } from '@/stores/notebook';
import { useAuthStore } from '@/stores/auth';
import type { Notebook, NotebookImage, ResourceProfile } from '@/types/notebook';

const { Text } = Typography;

const NotebookListPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const {
    notebooks,
    images,
    profiles,
    loading,
    fetchNotebooks,
    fetchImages,
    fetchProfiles,
    startNotebook,
    stopNotebook,
    deleteNotebook,
  } = useNotebookStore();

  const [createModalOpen, setCreateModalOpen] = useState(false);

  useEffect(() => {
    if (user) {
      fetchNotebooks();
      fetchImages();
      fetchProfiles();
    }
  }, [user]);

  const handleStart = async (notebook: Notebook) => {
    try {
      await startNotebook(notebook.user, notebook.name);
      message.success('Notebook started successfully');
      fetchNotebooks();
    } catch (error) {
      message.error('Failed to start notebook');
    }
  };

  const handleStop = async (notebook: Notebook) => {
    try {
      await stopNotebook(notebook.user, notebook.name);
      message.success('Notebook stopped successfully');
      fetchNotebooks();
    } catch (error) {
      message.error('Failed to stop notebook');
    }
  };

  const handleDelete = async (notebook: Notebook) => {
    Modal.confirm({
      title: 'Delete Notebook',
      content: `Are you sure you want to delete notebook "${notebook.name}"?`,
      okText: 'Delete',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteNotebook(notebook.user, notebook.name);
          message.success('Notebook deleted successfully');
          fetchNotebooks();
        } catch (error) {
          message.error('Failed to delete notebook');
        }
      },
    });
  };

  const handleOpen = (notebook: Notebook) => {
    if (notebook.url) {
      window.open(notebook.url, '_blank');
    }
  };

  const getStateTag = (state: string) => {
    const stateConfig: Record<string, { color: string; text: string }> = {
      running: { color: 'success', text: 'Running' },
      stopped: { color: 'default', text: 'Stopped' },
      pending: { color: 'processing', text: 'Starting' },
      error: { color: 'error', text: 'Error' },
    };
    const config = stateConfig[state] || stateConfig.stopped;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getImageIcon = (imageId: string) => {
    const image = images.find((img) => img.id === imageId);
    if (!image) return <CodeOutlined />;

    const icons: Record<string, React.ReactNode> = {
      pytorch: <RocketOutlined style={{ color: '#EE4C2C' }} />,
      tensorflow: <RocketOutlined style={{ color: '#FF6F00' }} />,
      sklearn: <CodeOutlined style={{ color: '#F7931E' }} />,
      nlp: <CodeOutlined style={{ color: '#76B900' }} />,
      minimal: <CodeOutlined />,
    };
    return icons[image.id] || <CodeOutlined />;
  };

  const columns: ColumnsType<Notebook> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Notebook) => (
        <Space>
          {getImageIcon(record.image)}
          <Text strong>{name === 'default' ? 'Main Notebook' : name}</Text>
        </Space>
      ),
    },
    {
      title: 'Image',
      dataIndex: 'image',
      key: 'image',
      render: (imageId: string) => {
        const image = images.find((img) => img.id === imageId);
        return image?.name || imageId;
      },
    },
    {
      title: 'Resources',
      key: 'resources',
      render: (_: unknown, record: Notebook) => (
        <Space size="small">
          <Tag>{record.cpu_limit} CPU</Tag>
          <Tag>{record.mem_limit} RAM</Tag>
          {record.gpu_limit > 0 && <Tag color="blue">{record.gpu_limit} GPU</Tag>}
        </Space>
      ),
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      render: getStateTag,
    },
    {
      title: 'Last Activity',
      dataIndex: 'last_activity',
      key: 'last_activity',
      render: (date: string) => (date ? new Date(date).toLocaleString() : 'Never'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: Notebook) => {
        const isRunning = record.state === 'running';
        const isPending = record.state === 'pending';

        return (
          <Space>
            {isRunning && (
              <Tooltip title="Open Notebook">
                <Button
                  type="primary"
                  size="small"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleOpen(record)}
                >
                  Open
                </Button>
              </Tooltip>
            )}
            {!isPending && (
              <Tooltip title={isRunning ? 'Stop' : 'Start'}>
                <Button
                  size="small"
                  danger={isRunning}
                  icon={isRunning ? <StopOutlined /> : <PlayCircleOutlined />}
                  onClick={() =>
                    isRunning ? handleStop(record) : handleStart(record)
                  }
                />
              </Tooltip>
            )}
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'delete',
                    label: 'Delete',
                    icon: <DeleteOutlined />,
                    danger: true,
                    onClick: () => handleDelete(record),
                  },
                ],
              }}
            >
              <Button size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="My Notebooks"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchNotebooks}
              loading={loading}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalOpen(true)}
            >
              New Notebook
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={notebooks}
          rowKey={(record) => `${record.user}/${record.name}`}
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: (
              <div style={{ padding: '40px', textAlign: 'center' }}>
                <RocketOutlined style={{ fontSize: '48px', color: '#ccc' }} />
                <p style={{ marginTop: '16px', color: '#999' }}>
                  No notebooks yet. Create your first notebook to get started!
                </p>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalOpen(true)}
                >
                  Create Notebook
                </Button>
              </div>
            ),
          }}
        />
      </Card>

      {createModalOpen && (
        <NotebookCreateModal
          open={createModalOpen}
          images={images}
          profiles={profiles}
          onCancel={() => setCreateModalOpen(false)}
          onSuccess={() => {
            setCreateModalOpen(false);
            fetchNotebooks();
          }}
        />
      )}
    </div>
  );
};

// Notebook Create Modal Component
interface NotebookCreateModalProps {
  open: boolean;
  images: NotebookImage[];
  profiles: ResourceProfile[];
  onCancel: () => void;
  onSuccess: () => void;
}

const NotebookCreateModal: React.FC<NotebookCreateModalProps> = ({
  open,
  images,
  profiles,
  onCancel,
  onSuccess,
}) => {
  const [selectedImage, setSelectedImage] = useState<string>('pytorch');
  const [selectedProfile, setSelectedProfile] = useState<string>('medium');
  const [serverName, setServerName] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const { createNotebook } = useNotebookStore();

  const handleCreate = async () => {
    setLoading(true);
    try {
      await createNotebook({
        image_id: selectedImage,
        profile_id: selectedProfile,
        server_name: serverName,
      });
      onSuccess();
    } catch (error) {
      // Error handled by store
    } finally {
      setLoading(false);
    }
  };

  const selectedImageData = images.find((img) => img.id === selectedImage);
  const selectedProfileData = profiles.find((p) => p.id === selectedProfile);

  return (
    <Modal
      title="Create New Notebook"
      open={open}
      onCancel={onCancel}
      onOk={handleCreate}
      confirmLoading={loading}
      width={600}
      okText="Create"
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Text strong>Notebook Name (Optional)</Text>
          <input
            type="text"
            placeholder="default"
            value={serverName}
            onChange={(e) => setServerName(e.target.value)}
            style={{
              width: '100%',
              marginTop: '8px',
              padding: '8px',
              border: '1px solid #d9d9d9',
              borderRadius: '4px',
            }}
          />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Leave empty for default notebook
          </Text>
        </div>

        <div>
          <Text strong>Image</Text>
          <div style={{ marginTop: '8px' }}>
            {images.map((image) => (
              <Card
                key={image.id}
                size="small"
                style={{
                  marginBottom: '8px',
                  cursor: 'pointer',
                  border: selectedImage === image.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                }}
                onClick={() => setSelectedImage(image.id)}
              >
                <Space>
                  {selectedImage === image.id && getImageIcon(image.id)}
                  <div>
                    <Text strong>{image.name}</Text>
                    {image.default && (
                      <Tag color="blue" style={{ marginLeft: '8px' }}>
                        Default
                      </Tag>
                    )}
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {image.description}
                      </Text>
                    </div>
                  </div>
                </Space>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <Text strong>Resource Profile</Text>
          <div style={{ marginTop: '8px' }}>
            {profiles.map((profile) => (
              <Card
                key={profile.id}
                size="small"
                style={{
                  marginBottom: '8px',
                  cursor: 'pointer',
                  border: selectedProfile === profile.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                }}
                onClick={() => setSelectedProfile(profile.id)}
              >
                <Space>
                  <div>
                    <Text strong>{profile.name}</Text>
                    {profile.default && (
                      <Tag color="blue" style={{ marginLeft: '8px' }}>
                        Default
                      </Tag>
                    )}
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {profile.description}
                      </Text>
                    </div>
                    <div>
                      <Space size="small">
                        <Tag>{profile.cpu_limit} CPU</Tag>
                        <Tag>{profile.mem_limit} RAM</Tag>
                        {profile.gpu_limit > 0 && (
                          <Tag color="blue">{profile.gpu_limit} GPU</Tag>
                        )}
                      </Space>
                    </div>
                  </div>
                </Space>
              </Card>
            ))}
          </div>
        </div>

        {selectedImageData?.gpu_recommended && selectedProfileData?.gpu_limit === 0 && (
          <div style={{ padding: '12px', background: '#fff7e6', borderRadius: '4px' }}>
            <Text type="warning">
              ⚠️ This image works best with GPU. Consider selecting a GPU-enabled
              resource profile.
            </Text>
          </div>
        )}
      </Space>
    </Modal>
  );
};

function getImageIcon(imageId: string, images: NotebookImage[] = []) {
  const image = images.find((img) => img.id === imageId);
  const icons: Record<string, React.ReactNode> = {
    pytorch: <RocketOutlined style={{ color: '#EE4C2C' }} />,
    tensorflow: <RocketOutlined style={{ color: '#FF6F00' }} />,
    sklearn: <CodeOutlined style={{ color: '#F7931E' }} />,
    nlp: <CodeOutlined style={{ color: '#76B900' }} />,
    minimal: <CodeOutlined />,
  };
  return icons[image?.id || ''] || <CodeOutlined />;
}

export default NotebookListPage;
