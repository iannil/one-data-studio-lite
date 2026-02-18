'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Upload,
  Space,
  Typography,
  message,
  Spin,
  Tag,
  Tabs,
  Descriptions,
  Table,
  Empty,
  Alert,
  Progress,
  Divider,
  Switch,
  List,
} from 'antd';
import {
  UploadOutlined,
  ScanOutlined,
  FileTextOutlined,
  TableOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { ocrApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Dragger } = Upload;

interface OCRResult {
  file_name: string;
  file_type: string;
  raw_text: string;
  structured_data?: {
    document_type?: string;
    key_values?: Record<string, string>;
    tables?: Array<{
      headers: string[];
      rows: string[][];
    }>;
    entities?: {
      names?: string[];
      dates?: string[];
      amounts?: string[];
      addresses?: string[];
    };
    summary?: string;
  };
  status: string;
  error?: string;
}

interface SupportedType {
  extension: string;
  description: string;
}

export default function OCRPage() {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<OCRResult[]>([]);
  const [supportedTypes, setSupportedTypes] = useState<SupportedType[]>([]);
  const [extractStructured, setExtractStructured] = useState(true);
  const [activeResultIndex, setActiveResultIndex] = useState(0);

  useEffect(() => {
    fetchSupportedTypes();
  }, []);

  const fetchSupportedTypes = async () => {
    try {
      const response = await ocrApi.getSupportedTypes();
      const types = Object.entries(response.data.descriptions).map(
        ([ext, desc]) => ({
          extension: ext,
          description: desc as string,
        })
      );
      setSupportedTypes(types);
    } catch (error) {
      message.error('获取支持的文件类型失败');
    }
  };

  const handleProcess = async () => {
    if (fileList.length === 0) {
      message.warning('请先上传文件');
      return;
    }

    setProcessing(true);
    setResults([]);

    try {
      const files = fileList.map((f) => f.originFileObj as File);

      if (files.length === 1) {
        const response = await ocrApi.process(files[0], extractStructured);
        setResults([response.data]);
      } else {
        const response = await ocrApi.batchProcess(files, extractStructured);
        setResults(response.data.results);
        message.success(
          `处理完成: ${response.data.successful} 成功, ${response.data.failed} 失败`
        );
      }

      setActiveResultIndex(0);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'OCR 处理失败');
    } finally {
      setProcessing(false);
    }
  };

  const uploadProps: UploadProps = {
    multiple: true,
    fileList,
    beforeUpload: (file) => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      const supported = supportedTypes.map((t) => t.extension);
      if (!supported.includes(ext)) {
        message.error(`不支持的文件类型: ${ext}`);
        return Upload.LIST_IGNORE;
      }
      return false;
    },
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList);
    },
    onRemove: (file) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
  };

  const clearAll = () => {
    setFileList([]);
    setResults([]);
    setActiveResultIndex(0);
  };

  const renderStructuredData = (data: OCRResult['structured_data']) => {
    if (!data) {
      return <Empty description="无结构化数据" />;
    }

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {data.document_type && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="文档类型">
              <Tag color="blue">{data.document_type}</Tag>
            </Descriptions.Item>
          </Descriptions>
        )}

        {data.summary && (
          <Card size="small" title="文档摘要">
            <Paragraph>{data.summary}</Paragraph>
          </Card>
        )}

        {data.key_values && Object.keys(data.key_values).length > 0 && (
          <Card size="small" title="关键字段">
            <Descriptions bordered size="small" column={2}>
              {Object.entries(data.key_values).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {value}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        )}

        {data.entities && (
          <Card size="small" title="实体识别">
            <Space wrap>
              {data.entities.names?.map((name, i) => (
                <Tag key={`name-${i}`} color="cyan">
                  人名: {name}
                </Tag>
              ))}
              {data.entities.dates?.map((date, i) => (
                <Tag key={`date-${i}`} color="green">
                  日期: {date}
                </Tag>
              ))}
              {data.entities.amounts?.map((amount, i) => (
                <Tag key={`amount-${i}`} color="gold">
                  金额: {amount}
                </Tag>
              ))}
              {data.entities.addresses?.map((addr, i) => (
                <Tag key={`addr-${i}`} color="purple">
                  地址: {addr}
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        {data.tables && data.tables.length > 0 && (
          <Card size="small" title="表格数据">
            {data.tables.map((table, tableIndex) => {
              const columns: ColumnsType<Record<string, string>> =
                table.headers.map((header, colIndex) => ({
                  title: header,
                  dataIndex: `col_${colIndex}`,
                  key: `col_${colIndex}`,
                }));

              const dataSource = table.rows.map((row, rowIndex) => {
                const rowData: Record<string, string> = { key: `row_${rowIndex}` };
                row.forEach((cell, colIndex) => {
                  rowData[`col_${colIndex}`] = cell;
                });
                return rowData;
              });

              return (
                <div key={tableIndex} style={{ marginBottom: 16 }}>
                  <Text type="secondary">表格 {tableIndex + 1}</Text>
                  <Table
                    columns={columns}
                    dataSource={dataSource}
                    size="small"
                    pagination={false}
                    scroll={{ x: true }}
                  />
                </div>
              );
            })}
          </Card>
        )}
      </Space>
    );
  };

  const renderResult = (result: OCRResult) => {
    if (result.status === 'error') {
      return (
        <Alert
          type="error"
          message="处理失败"
          description={result.error}
          showIcon
        />
      );
    }

    return (
      <Tabs defaultActiveKey="raw">
        <TabPane
          tab={
            <span>
              <FileTextOutlined />
              原始文本
            </span>
          }
          key="raw"
        >
          <Card size="small">
            <Paragraph
              copyable
              style={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                maxHeight: 500,
                overflow: 'auto',
              }}
            >
              {result.raw_text || '(无文本内容)'}
            </Paragraph>
          </Card>
        </TabPane>
        <TabPane
          tab={
            <span>
              <TableOutlined />
              结构化数据
            </span>
          }
          key="structured"
        >
          {renderStructuredData(result.structured_data)}
        </TabPane>
        <TabPane
          tab={
            <span>
              <InfoCircleOutlined />
              文件信息
            </span>
          }
          key="info"
        >
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="文件名">
              {result.file_name}
            </Descriptions.Item>
            <Descriptions.Item label="文件类型">
              <Tag>{result.file_type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="处理状态">
              {result.status === 'success' ? (
                <Tag color="success" icon={<CheckCircleOutlined />}>
                  成功
                </Tag>
              ) : (
                <Tag color="error" icon={<CloseCircleOutlined />}>
                  失败
                </Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="文本长度">
              {result.raw_text?.length || 0} 字符
            </Descriptions.Item>
          </Descriptions>
        </TabPane>
      </Tabs>
    );
  };

  return (
    <AuthGuard>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Card
          title={<Title level={4}>OCR 文档识别</Title>}
          extra={
            <Space>
              <span>AI结构化提取:</span>
              <Switch
                checked={extractStructured}
                onChange={setExtractStructured}
              />
              {(fileList.length > 0 || results.length > 0) && (
                <Button icon={<DeleteOutlined />} onClick={clearAll}>
                  清空
                </Button>
              )}
            </Space>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Dragger {...uploadProps} style={{ maxHeight: 200 }}>
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持 PDF、PNG、JPG、JPEG、TIFF、BMP 格式，可批量上传 (最多 20
                个文件)
              </p>
            </Dragger>

            <div style={{ textAlign: 'center' }}>
              <Button
                type="primary"
                size="large"
                icon={<ScanOutlined />}
                onClick={handleProcess}
                loading={processing}
                disabled={fileList.length === 0}
              >
                {processing ? '识别中...' : `开始识别 (${fileList.length} 个文件)`}
              </Button>
            </div>
          </Space>
        </Card>

        {processing && (
          <Card>
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" tip="正在进行 OCR 识别..." />
              <Progress percent={0} status="active" style={{ marginTop: 20 }} />
            </div>
          </Card>
        )}

        {results.length > 0 && !processing && (
          <Card title="识别结果">
            {results.length > 1 && (
              <>
                <List
                  grid={{ gutter: 16, column: 4 }}
                  dataSource={results}
                  renderItem={(result, index) => (
                    <List.Item>
                      <Card
                        size="small"
                        hoverable
                        onClick={() => setActiveResultIndex(index)}
                        style={{
                          borderColor:
                            index === activeResultIndex ? '#1890ff' : undefined,
                        }}
                      >
                        <Space>
                          {result.status === 'success' ? (
                            <CheckCircleOutlined style={{ color: '#52c41a' }} />
                          ) : (
                            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                          )}
                          <Text
                            ellipsis
                            style={{ maxWidth: 150 }}
                            title={result.file_name}
                          >
                            {result.file_name}
                          </Text>
                        </Space>
                      </Card>
                    </List.Item>
                  )}
                />
                <Divider />
              </>
            )}

            {results[activeResultIndex] &&
              renderResult(results[activeResultIndex])}
          </Card>
        )}

        <Card title="支持的文件类型" size="small">
          <Space wrap>
            {supportedTypes.map((type) => (
              <Tag key={type.extension} color="blue">
                {type.extension} - {type.description}
              </Tag>
            ))}
          </Space>
        </Card>
      </Space>
    </AuthGuard>
  );
}
