import React, { useState } from 'react';
import {
  Card,
  Upload,
  Button,
  Table,
  Tag,
  Input,
  Select,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Progress,
  Image,
} from 'antd';
import {
  FileImageOutlined,
  UploadOutlined,
  EyeOutlined,
  DeleteOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface OcrTask {
  id: string;
  fileName: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  language: string;
  createdAt: string;
  result?: {
    text: string;
    confidence: number;
    pageCount: number;
  };
  error?: string;
}

const LANGUAGE_OPTIONS = [
  { label: '中文简体', value: 'ch' },
  { label: '中文繁体', value: 'cht' },
  { label: '英文', value: 'en' },
  { label: '中英混合', value: 'ch_en' },
  { label: '日文', value: 'japan' },
  { label: '韩文', value: 'korean' },
];

const DEMO_TASKS: OcrTask[] = [
  {
    id: '1',
    fileName: 'invoice_001.png',
    status: 'completed',
    progress: 100,
    language: 'ch_en',
    createdAt: '2026-01-30 14:23:15',
    result: {
      text: '增值税专用发票\n发票代码: 1234567890\n发票号码: 00123456\n开票日期: 2026年01月30日\n...',
      confidence: 0.96,
      pageCount: 1,
    },
  },
  {
    id: '2',
    fileName: 'contract_scan.jpg',
    status: 'processing',
    progress: 65,
    language: 'ch',
    createdAt: '2026-01-30 15:10:22',
  },
  {
    id: '3',
    fileName: 'form_document.pdf',
    status: 'pending',
    progress: 0,
    language: 'ch_en',
    createdAt: '2026-01-30 15:30:45',
  },
];

const OcrProcessing: React.FC = () => {
  const [tasks, setTasks] = useState<OcrTask[]>(DEMO_TASKS);
  const [selectedLanguage, setSelectedLanguage] = useState('ch_en');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewTask, setPreviewTask] = useState<OcrTask | null>(null);
  const [configVisible, setConfigVisible] = useState(false);

  const uploadProps: UploadProps = {
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: (file) => {
      const isImage = file.type.startsWith('image/') || file.type === 'application/pdf';
      if (!isImage) {
        message.error('只能上传图片或 PDF 文件');
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB');
        return false;
      }

      // Create new task
      const newTask: OcrTask = {
        id: Date.now().toString(),
        fileName: file.name,
        status: 'pending',
        progress: 0,
        language: selectedLanguage,
        createdAt: new Date().toLocaleString('zh-CN'),
      };

      setTasks([newTask, ...tasks]);
      setFileList([...fileList, file]);

      // Simulate processing
      setTimeout(() => simulateProcessing(newTask.id), 1000);

      return false; // Prevent auto upload
    },
    fileList,
    listType: 'picture-card',
  };

  const simulateProcessing = (taskId: string) => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        setTasks((prev) =>
          prev.map((t) =>
            t.id === taskId
              ? {
                  ...t,
                  status: 'completed',
                  progress: 100,
                  result: {
                    text: `[演示] 识别结果：\n这是从 ${t.fileName} 中识别出的文本内容。\n\nPaddleOCR 服务尚未配置，当前为演示模式。\n实际使用时需要配置 PaddleOCR 服务。`,
                    confidence: 0.85 + Math.random() * 0.14,
                    pageCount: 1,
                  },
                }
              : t
          )
        );
        message.success(`文件 ${tasks.find((t) => t.id === taskId)?.fileName} 识别完成`);
      } else {
        setTasks((prev) =>
          prev.map((t) =>
            t.id === taskId
              ? { ...t, status: 'processing' as const, progress: Math.min(100, progress) }
              : t
          )
        );
      }
    }, 500);
  };

  const handlePreview = (task: OcrTask) => {
    setPreviewTask(task);
    setPreviewVisible(true);
  };

  const handleDelete = (taskId: string) => {
    setTasks(tasks.filter((t) => t.id !== taskId));
    message.success('任务已删除');
  };

  const handleReprocess = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, status: 'pending' as const, progress: 0 } : t
      )
    );
    setTimeout(() => simulateProcessing(taskId), 500);
  };

  const getStatusTag = (status: OcrTask['status']) => {
    const config = {
      pending: { color: 'default', text: '等待中' },
      processing: { color: 'blue', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'fileName',
      key: 'fileName',
      width: 200,
      render: (name: string) => (
        <Space>
          <FileImageOutlined />
          <Text ellipsis style={{ maxWidth: 150 }}>{name}</Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: OcrTask['status'], record: OcrTask) => (
        <Space>
          {getStatusTag(status)}
          {status === 'processing' && (
            <Progress percent={Math.round(record.progress)} size="small" style={{ width: 60 }} />
          )}
        </Space>
      ),
    },
    {
      title: '识别语言',
      dataIndex: 'language',
      key: 'language',
      width: 120,
      render: (lang: string) => {
        const opt = LANGUAGE_OPTIONS.find((o) => o.value === lang);
        return <Tag>{opt?.label || lang}</Tag>;
      },
    },
    {
      title: '置信度',
      key: 'confidence',
      width: 100,
      render: (_: unknown, record: OcrTask) =>
        record.result ? (
          <Tag color="green">{(record.result.confidence * 100).toFixed(0)}%</Tag>
        ) : (
          '-'
        ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 160,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, record: OcrTask) => (
        <Space size="small">
          {record.status === 'completed' && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record)}
            >
              查看结果
            </Button>
          )}
          {record.status === 'failed' && (
            <Button type="link" size="small" onClick={() => handleReprocess(record.id)}>
              重试
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <FileImageOutlined /> OCR 文档处理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="OCR 功能说明"
          description={
            <>
              <Text>
                OCR 功能基于 PaddleOCR 实现，支持图片和 PDF 文档的文字识别。
              </Text>
              <br />
              <Text type="secondary">
                当前为演示模式，实际使用需要配置 PaddleOCR 服务（ai_cleaning:8012）。
              </Text>
            </>
          }
          type="info"
          showIcon
          action={
            <Button size="small" icon={<SettingOutlined />} onClick={() => setConfigVisible(true)}>
              配置服务
            </Button>
          }
        />

        <Card size="small" title="上传文档">
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Text>识别语言：</Text>
              <Select
                value={selectedLanguage}
                onChange={setSelectedLanguage}
                options={LANGUAGE_OPTIONS}
                style={{ width: 150 }}
              />
            </Space>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>上传文件</Button>
            </Upload>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            支持格式：PNG, JPG, PDF（最大 10MB）
          </Text>
        </Card>

        <Card size="small" title="识别任务">
          <Table
            columns={columns}
            dataSource={tasks.map((t) => ({ ...t, key: t.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 900 }}
          />
        </Card>
      </Space>

      {/* 结果预览弹窗 */}
      <Modal
        title="识别结果"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
          <Button key="copy" type="primary" onClick={() => {
            navigator.clipboard.writeText(previewTask?.result?.text || '');
            message.success('已复制到剪贴板');
          }}>
            复制文本
          </Button>,
        ]}
        width={700}
      >
        {previewTask && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Text strong>文件：</Text>
              <Text>{previewTask.fileName}</Text>
            </Space>
            <Space>
              <Text strong>置信度：</Text>
              <Tag color="green">
                {(previewTask.result?.confidence
                  ? previewTask.result.confidence * 100
                  : 0
                ).toFixed(1)}%
              </Tag>
            </Space>
            <Card size="small" title="识别文本">
              <TextArea
                value={previewTask.result?.text || '暂无结果'}
                readOnly
                rows={10}
                style={{ fontFamily: 'monospace' }}
              />
            </Card>
          </Space>
        )}
      </Modal>

      {/* 配置服务弹窗 */}
      <Modal
        title="配置 OCR 服务"
        open={configVisible}
        onCancel={() => setConfigVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setConfigVisible(false)}>
            取消
          </Button>,
          <Button key="save" type="primary" onClick={() => {
            setConfigVisible(false);
            message.success('配置已保存（演示模式）');
          }}>
            保存配置
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            message="服务配置"
            description="请配置 PaddleOCR 服务地址以启用实际识别功能"
            type="info"
          />
          <Input
            placeholder="OCR 服务地址"
            defaultValue="http://localhost:8012"
            addonBefore="服务地址"
          />
          <Input
            placeholder="检测模型"
            defaultValue="ch_PP-OCRv4_det"
            addonBefore="检测模型"
          />
          <Input
            placeholder="识别模型"
            defaultValue="ch_PP-OCRv4_rec"
            addonBefore="识别模型"
          />
        </Space>
      </Modal>
    </div>
  );
};

export default OcrProcessing;
