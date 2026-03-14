/**
 * DAG Export/Import Component
 *
 * Provides UI for exporting and importing DAG configurations.
 */

import React, { useRef } from 'react';
import { Button, Dropdown, Modal, Input, message } from 'antd';
import {
  DownloadOutlined,
  UploadOutlined,
  CopyOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { DAGNode, DAGEdge } from '@/types/workflow';

interface DAGExportImportProps {
  dagId?: string;
  dagName?: string;
  nodes: DAGNode[];
  edges: DAGEdge[];
  onImport?: (data: any) => void;
  onClone?: (newName: string) => void;
}

export const DAGExportImport: React.FC<DAGExportImportProps> = ({
  dagId,
  dagName,
  nodes,
  edges,
  onImport,
  onClone,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [cloneModalOpen, setCloneModalOpen] = React.useState(false);
  const [cloneName, setCloneName] = React.useState('');

  // Export DAG to JSON file
  const handleExport = () => {
    const exportData = {
      version: '1.0',
      exported_at: new Date().toISOString(),
      dag: {
        dag_id: dagId || 'untitled',
        name: dagName || 'Untitled Workflow',
        tasks: nodes.map((node) => ({
          task_id: node.id,
          task_type: node.task_type,
          name: node.name,
          description: node.config?.description,
          depends_on: node.config?.depends_on || [],
          retry_count: node.config?.retry_count || 0,
          retry_delay_seconds: node.config?.retry_delay_seconds || 300,
          timeout_seconds: node.config?.timeout_seconds,
          parameters: node.config?.parameters || {},
          position: node.position,
        })),
        edges: edges,
      },
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${dagName || 'workflow'}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    message.success('DAG exported successfully');
  };

  // Copy DAG to clipboard
  const handleCopyToClipboard = () => {
    const exportData = {
      version: '1.0',
      exported_at: new Date().toISOString(),
      dag: {
        dag_id: dagId || 'untitled',
        name: dagName || 'Untitled Workflow',
        tasks: nodes.map((node) => ({
          task_id: node.id,
          task_type: node.task_type,
          name: node.name,
          description: node.config?.description,
          depends_on: node.config?.depends_on || [],
          retry_count: node.config?.retry_count || 0,
          retry_delay_seconds: node.config?.retry_delay_seconds || 300,
          timeout_seconds: node.config?.timeout_seconds,
          parameters: node.config?.parameters || {},
          position: node.position,
        })),
        edges: edges,
      },
    };

    navigator.clipboard.writeText(JSON.stringify(exportData, null, 2));
    message.success('DAG copied to clipboard');
  };

  // Trigger file input click
  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  // Handle file import
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);

      if (!data.dag) {
        message.error('Invalid import file: missing dag data');
        return;
      }

      onImport?.(data);
      message.success('DAG imported successfully');
    } catch (error) {
      message.error('Failed to import DAG: Invalid JSON file');
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle clone modal confirm
  const handleCloneConfirm = () => {
    if (!cloneName.trim()) {
      message.warning('Please enter a name for the cloned DAG');
      return;
    }
    onClone?.(cloneName);
    setCloneModalOpen(false);
    setCloneName('');
  };

  const exportMenuItems = [
    {
      key: 'file',
      label: 'Download as JSON',
      icon: <DownloadOutlined />,
      onClick: handleExport,
    },
    {
      key: 'clipboard',
      label: 'Copy to Clipboard',
      icon: <FileTextOutlined />,
      onClick: handleCopyToClipboard,
    },
  ];

  return (
    <>
      <Dropdown menu={{ items: exportMenuItems }} trigger={['click']}>
        <Button icon={<DownloadOutlined />}>Export</Button>
      </Dropdown>

      <Button icon={<UploadOutlined />} onClick={handleImportClick}>
        Import
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {dagId && (
        <Button icon={<CopyOutlined />} onClick={() => setCloneModalOpen(true)}>
          Clone
        </Button>
      )}

      <Modal
        title="Clone DAG"
        open={cloneModalOpen}
        onOk={handleCloneConfirm}
        onCancel={() => {
          setCloneModalOpen(false);
          setCloneName('');
        }}
      >
        <Input
          placeholder={`Copy of ${dagName}`}
          value={cloneName}
          onChange={(e) => setCloneName(e.target.value)}
          prefix="Name:"
        />
      </Modal>
    </>
  );
};

export default DAGExportImport;
