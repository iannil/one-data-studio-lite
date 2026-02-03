/**
 * React Hooks for Async Task Management
 *
 * Provides hooks for managing long-running operations with WebSocket support.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';
import type {
  AsyncTask,
  TaskQueryParams,
  TaskStatus,
  TaskWebSocketMessage,
} from '../types/tasks';
import {
  getMyTasks,
  cancelTask,
  retryTask,
  deleteTask,
  downloadTaskResult,
  getTaskWebSocketUrl,
} from '../api/tasks';

/**
 * Hook for async task management
 */
export function useAsyncTasks(params?: TaskQueryParams) {
  const [tasks, setTasks] = useState<AsyncTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getMyTasks(params);
      setTasks(response.tasks);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '获取任务列表失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const cancelTaskHandler = useCallback(async (taskId: string) => {
    try {
      await cancelTask(taskId);
      message.success('任务已取消');
      fetchTasks();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '取消任务失败';
      message.error(errorMsg);
    }
  }, [fetchTasks]);

  const retryTaskHandler = useCallback(async (taskId: string) => {
    try {
      await retryTask(taskId);
      message.success('任务已重新提交');
      fetchTasks();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '重试任务失败';
      message.error(errorMsg);
    }
  }, [fetchTasks]);

  const deleteTaskHandler = useCallback(async (taskId: string) => {
    try {
      await deleteTask(taskId);
      message.success('任务已删除');
      fetchTasks();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '删除任务失败';
      message.error(errorMsg);
    }
  }, [fetchTasks]);

  const downloadResult = useCallback((taskId: string) => {
    const url = downloadTaskResult(taskId);
    window.open(url, '_blank');
  }, []);

  return {
    tasks,
    loading,
    error,
    refresh: fetchTasks,
    cancelTask: cancelTaskHandler,
    retryTask: retryTaskHandler,
    deleteTask: deleteTaskHandler,
    downloadResult,
  };
}

/**
 * Hook for real-time task updates via WebSocket
 */
export function useTaskWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messageHandlersRef = useRef<Array<(message: TaskWebSocketMessage) => void>>([]);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(getTaskWebSocketUrl());

        ws.onopen = () => {
          setIsConnected(true);
          // WebSocket connected
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as TaskWebSocketMessage;
            messageHandlersRef.current.forEach((handler) => handler(message));
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          // Attempt to reconnect after 5 seconds
          setTimeout(connect, 5000);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('Failed to create WebSocket connection:', err);
        setTimeout(connect, 5000);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const subscribe = useCallback((handler: (message: TaskWebSocketMessage) => void) => {
    messageHandlersRef.current.push(handler);

    return () => {
      messageHandlersRef.current = messageHandlersRef.current.filter(h => h !== handler);
    };
  }, []);

  return {
    isConnected,
    subscribe,
  };
}

/**
 * Hook for tracking a single task with real-time updates
 */
export function useTask(taskId: string) {
  const [task, setTask] = useState<AsyncTask | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchTask = useCallback(async () => {
    setLoading(true);
    try {
      const { getTask: getTaskApi } = await import('../api/tasks');
      const taskData = await getTaskApi(taskId);
      setTask(taskData);
    } catch (err) {
      console.error('Failed to fetch task:', err);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  // Subscribe to WebSocket updates for this task
  useEffect(() => {
    let ws: WebSocket | null = null;

    const connect = () => {
      try {
        ws = new WebSocket(getTaskWebSocketUrl());

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as TaskWebSocketMessage;
            if (message.task.id === taskId) {
              setTask(message.task);
            }
          } catch {
            // Ignore parse errors
          }
        };
      } catch {
        // Ignore connection errors
      }
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [taskId]);

  return {
    task,
    loading,
    refresh: fetchTask,
  };
}

/**
 * Hook for task status summary
 */
export function useTaskSummary() {
  const [summary, setSummary] = useState<Record<TaskStatus, number>>({
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
    timeout: 0,
  });

  const updateSummary = useCallback((tasks: AsyncTask[]) => {
    const counts: Record<TaskStatus, number> = {
      pending: 0,
      running: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
      timeout: 0,
    };

    tasks.forEach((task) => {
      counts[task.status]++;
    });

    setSummary(counts);
  }, []);

  return {
    summary,
    updateSummary,
    total: Object.values(summary).reduce((a, b) => a + b, 0),
  };
}
