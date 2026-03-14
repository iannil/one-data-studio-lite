/**
 * LLM Chat Page
 *
 * Intelligent dialogue interface with context management and model selection.
 */

'use client';

import React, { useEffect, useState, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Input,
  Button,
  Select,
  Space,
  message,
  Avatar,
  Tag,
  List,
  Modal,
  Form,
  Slider,
  Switch,
  Divider,
  Tooltip,
} from 'antd';
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  ClearOutlined,
  SettingOutlined,
  UserOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import {
  useLLMStore,
  useChatSessions,
  useCurrentChatSession,
  useChatMessages,
  useLLMLoading,
  useLLMError,
  useKnowledgeBases,
} from '@/stores/llm';

const { TextArea } = Input;
const { Option } = Select;

const LLMChatPage: React.FC = () => {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [form] = Form.useForm();

  const {
    sessions,
    currentSession,
    currentMessages,
    availableModels,
    loading,
    error,
    fetchSessions,
    createSession,
    fetchSession,
    deleteSession,
    clearHistory,
    sendMessage,
    switchModel,
    updateParameters,
    fetchModels,
    clearError,
    knowledgeBases,
  } = useLLMStore();

  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [newSessionModalOpen, setNewSessionModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  useEffect(() => {
    fetchSessions();
    fetchModels();
  }, [fetchSessions, fetchModels]);

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleCreateSession = async () => {
    const values = form.getFieldsValue();
    try {
      await createSession({
        model: values.model,
        system_prompt: values.system_prompt,
        parameters: {
          temperature: values.temperature || 0.7,
          max_tokens: values.max_tokens || 2048,
          top_p: values.top_p || 0.9,
        },
      });
      setNewSessionModalOpen(false);
      form.resetFields();
    } catch (err) {
      // Error already handled by store
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    await fetchSession(sessionId);
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !currentSession || sending) return;

    const message = inputMessage;
    setInputMessage('');
    setSending(true);

    try {
      await sendMessage(currentSession.session_id, message);
    } catch (err) {
      // Error already handled
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      if (currentSession?.session_id === sessionId) {
        // Clear current session if deleted
      }
    } catch (err) {
      // Error already handled
    }
  };

  const handleClearHistory = async () => {
    if (!currentSession) return;
    try {
      await clearHistory(currentSession.session_id);
    } catch (err) {
      // Error already handled
    }
  };

  const handleSwitchKB = async (kbId: string) => {
    if (!currentSession) return;
    try {
      // Update session with knowledge base
      await updateParameters(currentSession.session_id, { knowledge_base_id: kbId });
    } catch (err) {
      // Error already handled
    }
  };

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #f0f0f0' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space>
              <h2 style={{ margin: 0 }}>
                <RobotOutlined /> AI Chat
              </h2>
              {currentSession && (
                <Tag color="blue">{currentSession.model}</Tag>
              )}
            </Space>
          </Col>
          <Col>
            <Space>
              {currentSession && (
                <>
                  <Tooltip title="Clear History">
                    <Button icon={<ClearOutlined />} onClick={handleClearHistory} />
                  </Tooltip>
                  <Tooltip title="Settings">
                    <Button icon={<SettingOutlined />} onClick={() => setSettingsModalOpen(true)} />
                  </Tooltip>
                </>
              )}
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setNewSessionModalOpen(true)}>
                New Chat
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      <Row style={{ flex: 1, overflow: 'hidden' }}>
        {/* Sidebar - Sessions */}
        <Col span={6} style={{ borderRight: '1px solid #f0f0f0', overflowY: 'auto' }}>
          <div style={{ padding: '16px' }}>
            <div style={{ marginBottom: '16px', fontWeight: 600 }}>Conversations</div>
            <List
              dataSource={sessions}
              renderItem={(session: any) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    backgroundColor: currentSession?.session_id === session.session_id ? '#f0f5ff' : 'transparent',
                    borderRadius: '4px',
                    padding: '8px',
                    marginBottom: '4px',
                  }}
                  onClick={() => handleSelectSession(session.session_id)}
                >
                  <List.Item.Meta
                    avatar={<Avatar icon={<RobotOutlined />} />}
                    title={
                      <div style={{ fontSize: '12px', fontWeight: 500 }}>
                        {session.title || 'New Chat'}
                      </div>
                    }
                    description={
                      <div style={{ fontSize: '11px', color: '#999' }}>
                        {session.model} • {new Date(session.updated_at).toLocaleDateString()}
                      </div>
                    }
                  />
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSession(session.session_id);
                    }}
                  />
                </List.Item>
              )}
            />
          </div>
        </Col>

        {/* Main Chat Area */}
        <Col span={18} style={{ display: 'flex', flexDirection: 'column' }}>
          {!currentSession ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Card style={{ textAlign: 'center', padding: '40px' }}>
                <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px', color: '#1890ff' }} />
                <h3>Welcome to AI Chat</h3>
                <p style={{ color: '#666', marginBottom: '24px' }}>
                  Start a new conversation or select an existing one
                </p>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setNewSessionModalOpen(true)}>
                  Start New Chat
                </Button>
              </Card>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
                {currentMessages.length === 0 ? (
                  <div style={{ textAlign: 'center', marginTop: '100px', color: '#999' }}>
                    <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <p>Start a conversation...</p>
                  </div>
                ) : (
                  currentMessages.map((msg) => (
                    <div
                      key={msg.id}
                      style={{
                        display: 'flex',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        marginBottom: '16px',
                      }}
                    >
                      <div style={{ maxWidth: '70%' }}>
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '4px' }}>
                          <Avatar
                            size="small"
                            icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                            style={{
                              backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a',
                            }}
                          />
                          <span style={{ fontSize: '12px', color: '#999' }}>
                            {msg.role === 'user' ? 'You' : 'AI'}
                          </span>
                        </div>
                        <Card
                          size="small"
                          style={{
                            backgroundColor: msg.role === 'user' ? '#e6f7ff' : '#f6ffed',
                            borderRadius: '8px',
                          }}
                        >
                          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        </Card>
                        {msg.error && (
                          <div style={{ color: '#ff4d4f', fontSize: '12px', marginTop: '4px' }}>
                            {msg.error}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {sending && (
                  <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '16px' }}>
                    <div style={{ maxWidth: '70%' }}>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '4px' }}>
                        <Avatar size="small" icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
                        <span style={{ fontSize: '12px', color: '#999' }}>AI</span>
                      </div>
                      <Card size="small" style={{ borderRadius: '8px' }}>
                        <div style={{ color: '#999' }}>Thinking...</div>
                      </Card>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0', backgroundColor: '#fafafa' }}>
                <Input
                  placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onPressEnter={handleKeyPress}
                  disabled={sending}
                  size="large"
                  suffix={
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      onClick={handleSendMessage}
                      disabled={sending || !inputMessage.trim()}
                      loading={sending}
                    />
                  }
                  style={{ fontSize: '14px' }}
                />
              </div>
            </>
          )}
        </Col>
      </Row>

      {/* New Session Modal */}
      <Modal
        title="New Chat Session"
        open={newSessionModalOpen}
        onOk={handleCreateSession}
        onCancel={() => {
          setNewSessionModalOpen(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="model"
            label="Model"
            rules={[{ required: true }]}
            initialValue="chatglm3-6b"
          >
            <Select>
              {availableModels.map((model) => (
                <Option key={model.id} value={model.id}>
                  {model.id}
                  {model.supports_streaming && <Tag color="green">Streaming</Tag>}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="system_prompt" label="System Prompt (Optional)">
            <TextArea rows={3} placeholder="You are a helpful assistant..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Settings Modal */}
      <Modal
        title="Chat Settings"
        open={settingsModalOpen}
        onCancel={() => setSettingsModalOpen(false)}
        footer={
          <Button onClick={() => setSettingsModalOpen(false)}>Close</Button>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item label="Knowledge Base">
            <Select placeholder="Select a knowledge base" allowClear onChange={handleSwitchKB}>
              {knowledgeBases.map((kb) => (
                <Option key={kb.id} value={kb.id}>
                  {kb.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="Temperature">
            <Slider min={0} max={2} step={0.1} marks={{ 0: 'Precise', 1: 'Balanced', 2: 'Creative' }} />
          </Form.Item>
          <Form.Item label="Max Tokens">
            <Slider min={256} max={4096} step={256} marks={{ 256: '256', 2048: '2048', 4096: '4096' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default LLMChatPage;
