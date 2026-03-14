/**
 * Terminal Panel Component
 *
 * Provides an interactive terminal session in the IDE
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Button,
  Space,
  Input,
  Select,
  Tooltip,
  Typography,
  message,
  Badge,
  Modal,
  Alert,
  Divider,
  Tag,
} from 'antd';
import {
  PlusOutlined,
  CloseOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CopyOutlined,
  ClearOutlined,
  TerminalOutlined,
} from '@ant-design/icons';
import { useIDEStore } from '@/stores/ide';
import { TerminalSession, TerminalMessage } from '@/types/ide';
import styles from './TerminalPanel.module.scss';

const { Text } = Typography;

interface TerminalPanelProps {
  notebookId: number;
}

interface TerminalInstance {
  session: TerminalSession;
  messages: TerminalMessage[];
  input: string;
  isVisible: boolean;
}

const TerminalPanel: React.FC<TerminalPanelProps> = ({ notebookId }) => {
  const {
    terminalSessions,
    fetchTerminalSessions,
    createTerminalSession,
    sendTerminalInput,
    getTerminalOutput,
    terminateTerminalSession,
    deleteTerminalSession,
  } = useIDEStore();

  const [terminals, setTerminals] = useState<Map<string, TerminalInstance>>(new Map());
  const [activeTerminalId, setActiveTerminalId] = useState<string | null>(null);
  const [pollingIntervals, setPollingIntervals] = useState<Map<string, NodeJS.Timeout>>(new Map());
  const inputRefs = useRef<Map<string, HTMLInputElement>>(new Map());
  const outputRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Initialize - fetch existing sessions
  useEffect(() => {
    fetchTerminalSessions(notebookId);
  }, [notebookId, fetchTerminalSessions]);

  // Setup terminal instances from fetched sessions
  useEffect(() => {
    if (terminalSessions.length > 0) {
      const newTerminals = new Map(terminals);

      for (const session of terminalSessions) {
        if (!newTerminals.has(session.id)) {
          newTerminals.set(session.id, {
            session,
            messages: [],
            input: '',
            isVisible: true,
          });
          // Start polling for new sessions
          startPolling(session.id);
        }
      }

      setTerminals(newTerminals);

      // Set first terminal as active if none selected
      if (!activeTerminalId && terminalSessions.length > 0) {
        setActiveTerminalId(terminalSessions[0].id);
      }
    }
  }, [terminalSessions]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      pollingIntervals.forEach((interval) => clearInterval(interval));
    };
  }, [pollingIntervals]);

  const startPolling = (sessionId: string) => {
    if (pollingIntervals.has(sessionId)) return;

    const interval = setInterval(async () => {
      try {
        const instance = terminals.get(sessionId);
        if (!instance) return;

        const lastMessageId = instance.messages.length > 0
          ? instance.messages[instance.messages.length - 1].id
          : undefined;

        const newMessages = await getTerminalOutput(sessionId, lastMessageId);

        if (newMessages.length > 0) {
          setTerminals((prev) => {
            const updated = new Map(prev);
            const current = updated.get(sessionId);
            if (current) {
              updated.set(sessionId, {
                ...current,
                messages: [...current.messages, ...newMessages],
              });
            }
            return updated;
          });

          // Auto-scroll to bottom
          setTimeout(() => {
            const outputDiv = outputRefs.current.get(sessionId);
            if (outputDiv) {
              outputDiv.scrollTop = outputDiv.scrollHeight;
            }
          }, 0);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 500);

    setPollingIntervals((prev) => new Map(prev).set(sessionId, interval));
  };

  const handleCreateTerminal = async () => {
    try {
      const session = await createTerminalSession(notebookId);
      setTerminals((prev) => {
        const updated = new Map(prev);
        updated.set(session.id, {
          session,
          messages: [],
          input: '',
          isVisible: true,
        });
        return updated;
      });
      setActiveTerminalId(session.id);
      startPolling(session.id);
    } catch (error: any) {
      message.error(error.message || 'Failed to create terminal');
    }
  };

  const handleSendInput = async (sessionId: string) => {
    const instance = terminals.get(sessionId);
    if (!instance) return;

    if (!instance.input.trim()) return;

    try {
      await sendTerminalInput(sessionId, instance.input);

      // Clear input after sending
      setTerminals((prev) => {
        const updated = new Map(prev);
        const current = updated.get(sessionId);
        if (current) {
          updated.set(sessionId, { ...current, input: '' });
        }
        return updated;
      });

      // Focus input again
      setTimeout(() => {
        const input = inputRefs.current.get(sessionId);
        if (input) input.focus();
      }, 0);
    } catch (error: any) {
      message.error(error.message || 'Failed to send input');
    }
  };

  const handleTerminateTerminal = async (sessionId: string) => {
    try {
      await terminateTerminalSession(sessionId);
      removeTerminal(sessionId);
    } catch (error: any) {
      message.error(error.message || 'Failed to terminate terminal');
    }
  };

  const handleDeleteTerminal = async (sessionId: string) => {
    try {
      await deleteTerminalSession(sessionId);
      removeTerminal(sessionId);
    } catch (error: any) {
      message.error(error.message || 'Failed to delete terminal');
    }
  };

  const removeTerminal = (sessionId: string) => {
    // Stop polling
    const interval = pollingIntervals.get(sessionId);
    if (interval) {
      clearInterval(interval);
      setPollingIntervals((prev) => {
        const updated = new Map(prev);
        updated.delete(sessionId);
        return updated;
      });
    }

    // Remove from state
    setTerminals((prev) => {
      const updated = new Map(prev);
      updated.delete(sessionId);
      return updated;
    });

    // Set new active terminal if this was active
    if (activeTerminalId === sessionId) {
      const remaining = Array.from(terminals.values()).filter((t) => t.session.id !== sessionId);
      setActiveTerminalId(remaining.length > 0 ? remaining[0].session.id : null);
    }
  };

  const handleClearOutput = (sessionId: string) => {
    setTerminals((prev) => {
      const updated = new Map(prev);
      const current = updated.get(sessionId);
      if (current) {
        updated.set(sessionId, { ...current, messages: [] });
      }
      return updated;
    });
  };

  const handleCopyOutput = (sessionId: string) => {
    const instance = terminals.get(sessionId);
    if (!instance) return;

    const output = instance.messages.map((m) => m.data).join('');
    navigator.clipboard.writeText(output);
    message.success('Output copied to clipboard');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'terminated':
        return <ExclamationCircleOutlined style={{ color: '#8c8c8c' }} />;
      default:
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  const activeTerminal = activeTerminalId ? terminals.get(activeTerminalId) : null;

  return (
    <div className={styles.terminalPanel}>
      {/* Terminal Tabs */}
      <div className={styles.terminalTabs}>
        <Space split={<Divider type="vertical" />}>
          {Array.from(terminals.values()).map((instance) => (
            <div
              key={instance.session.id}
              className={`${styles.terminalTab} ${
                activeTerminalId === instance.session.id ? styles.activeTab : ''
              }`}
              onClick={() => setActiveTerminalId(instance.session.id)}
            >
              <Space size={4}>
                {getStatusIcon(instance.session.status)}
                <TerminalOutlined />
                <span>Terminal {instance.session.id.slice(-4)}</span>
                {instance.session.status === 'terminated' && (
                  <Tag color="default">Closed</Tag>
                )}
                <Tooltip title="Close Terminal">
                  <CloseOutlined
                    className={styles.closeIcon}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTerminateTerminal(instance.session.id);
                    }}
                  />
                </Tooltip>
              </Space>
            </div>
          ))}
          <Button
            type="text"
            size="small"
            icon={<PlusOutlined />}
            onClick={handleCreateTerminal}
          >
            New Terminal
          </Button>
        </Space>
      </div>

      {/* Terminal Output */}
      <div className={styles.terminalContent}>
        {activeTerminal ? (
          <>
            <div
              ref={(el) => el && outputRefs.current.set(activeTerminalId, el)}
              className={styles.terminalOutput}
            >
              {activeTerminal.messages.map((msg) => (
                <span
                  key={msg.id}
                  className={`${styles.terminalLine} ${
                    msg.type === 'input' ? styles.inputLine : ''
                  }`}
                >
                  {msg.data}
                </span>
              ))}
              {activeTerminal.messages.length === 0 && (
                <div className={styles.welcomeMessage}>
                  <TerminalOutlined /> Terminal ready. Type a command to start.
                </div>
              )}
            </div>

            {/* Terminal Input */}
            {activeTerminal.session.status === 'running' && (
              <div className={styles.terminalInputContainer}>
                <span className={styles.prompt}>$ </span>
                <Input
                  ref={(el) => el && inputRefs.current.set(activeTerminalId, el)}
                  className={styles.terminalInput}
                  value={activeTerminal.input}
                  onChange={(e) => {
                    setTerminals((prev) => {
                      const updated = new Map(prev);
                      const current = updated.get(activeTerminalId!);
                      if (current) {
                        updated.set(activeTerminalId!, {
                          ...current,
                          input: e.target.value,
                        });
                      }
                      return updated;
                    });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSendInput(activeTerminalId!);
                    }
                  }}
                  placeholder="Enter command..."
                  bordered={false}
                />
              </div>
            )}

            {/* Terminal Actions */}
            <div className={styles.terminalActions}>
              <Space>
                <Tooltip title="Clear Output">
                  <Button
                    type="text"
                    size="small"
                    icon={<ClearOutlined />}
                    onClick={() => handleClearOutput(activeTerminalId!)}
                  >
                    Clear
                  </Button>
                </Tooltip>
                <Tooltip title="Copy Output">
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => handleCopyOutput(activeTerminalId!)}
                  >
                    Copy
                  </Button>
                </Tooltip>
              </Space>
              <Text type="secondary" className={styles.cwd}>
                {activeTerminal.session.cwd}
              </Text>
            </div>
          </>
        ) : (
          <div className={styles.noTerminal}>
            <TerminalOutlined className={styles.noTerminalIcon} />
            <Text type="secondary">No terminal selected</Text>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateTerminal}
            >
              Create Terminal
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TerminalPanel;
