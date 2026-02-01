import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Tabs,
  Drawer,
  DatePicker,
  Descriptions,
  Row,
  Col,
  Statistic,
  Divider,
} from 'antd';
import {
  DollarOutlined,
  PlusOutlined,
  EditOutlined,
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
  ExportOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type InvoiceStatus = 'pending' | 'approved' | 'rejected' | 'processing' | 'completed' | 'cancelled';
type InvoiceType = 'vat' | 'ordinary';

interface Invoice {
  id: string;
  invoiceNo: string;
  invoiceCode: string;
  type: InvoiceType;
  amount: number;
  taxAmount: number;
  totalAmount: number;
  buyerName: string;
  buyerTaxNo: string;
  status: InvoiceStatus;
  applyTime: string;
  approver?: string;
  approveTime?: string;
  rejectReason?: string;
  remark?: string;
}

const DEMO_INVOICES: Invoice[] = [
  {
    id: '1',
    invoiceNo: '12345678',
    invoiceCode: '011001800304',
    type: 'vat',
    amount: 50000,
    taxAmount: 6500,
    totalAmount: 56500,
    buyerName: '科技发展有限公司',
    buyerTaxNo: '91110000MA01234567',
    status: 'completed',
    applyTime: '2026-01-20 10:30:00',
    approver: '财务总监',
    approveTime: '2026-01-21 14:20:00',
  },
  {
    id: '2',
    invoiceNo: '12345679',
    invoiceCode: '011001800304',
    type: 'vat',
    amount: 30000,
    taxAmount: 3900,
    totalAmount: 33900,
    buyerName: '数据智能科技有限公司',
    buyerTaxNo: '91110000MA01234568',
    status: 'processing',
    applyTime: '2026-01-25 09:15:00',
    approver: '财务主管',
    approveTime: '2026-01-25 16:30:00',
  },
  {
    id: '3',
    invoiceNo: '12345680',
    invoiceCode: '011001800304',
    type: 'ordinary',
    amount: 5000,
    taxAmount: 0,
    totalAmount: 5000,
    buyerName: '互联网创业公司',
    buyerTaxNo: '91110000MA01234569',
    status: 'approved',
    applyTime: '2026-01-28 11:00:00',
    approver: '财务主管',
    approveTime: '2026-01-28 15:45:00',
  },
  {
    id: '4',
    invoiceNo: '12345681',
    invoiceCode: '011001800304',
    type: 'vat',
    amount: 80000,
    taxAmount: 10400,
    totalAmount: 90400,
    buyerName: '贸易集团有限公司',
    buyerTaxNo: '91110000MA01234570',
    status: 'pending',
    applyTime: '2026-01-30 14:20:00',
  },
  {
    id: '5',
    invoiceNo: '12345682',
    invoiceCode: '011001800304',
    type: 'ordinary',
    amount: 2000,
    taxAmount: 0,
    totalAmount: 2000,
    buyerName: '咨询服务中心',
    buyerTaxNo: '91110000MA01234571',
    status: 'rejected',
    applyTime: '2026-01-18 10:00:00',
    rejectReason: '购买方信息不完整，请补充纳税人识别号',
  },
  {
    id: '6',
    invoiceNo: '12345683',
    invoiceCode: '011001800304',
    type: 'vat',
    amount: 15000,
    taxAmount: 1950,
    totalAmount: 16950,
    buyerName: '软件技术有限公司',
    buyerTaxNo: '91110000MA01234572',
    status: 'cancelled',
    applyTime: '2026-01-10 09:30:00',
  },
];

const TYPE_OPTIONS = [
  { label: '增值税专用发票', value: 'vat' },
  { label: '普通发票', value: 'ordinary' },
];

const Invoices: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>(DEMO_INVOICES);
  const [applyModalVisible, setApplyModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [viewingInvoice, setViewingInvoice] = useState<Invoice | null>(null);
  const [rejectingInvoice, setRejectingInvoice] = useState<Invoice | null>(null);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<InvoiceType | 'all'>('all');
  const [applyForm] = Form.useForm();
  const [rejectForm] = Form.useForm();

  const handleApply = () => {
    applyForm.resetFields();
    applyForm.setFieldsValue({ type: 'vat' });
    setApplyModalVisible(true);
  };

  const handleView = (invoice: Invoice) => {
    setViewingInvoice(invoice);
    setDetailDrawerVisible(true);
  };

  const handleApplySubmit = () => {
    applyForm.validateFields().then((values) => {
      const amount = values.amount || 0;
      const taxAmount = values.type === 'vat' ? amount * 0.13 : 0;
      const totalAmount = amount + taxAmount;

      const newInvoice: Invoice = {
        id: Date.now().toString(),
        invoiceNo: `123456${83 + invoices.length}`,
        invoiceCode: '011001800304',
        type: values.type,
        amount,
        taxAmount,
        totalAmount,
        buyerName: values.buyerName,
        buyerTaxNo: values.buyerTaxNo,
        status: 'pending',
        applyTime: new Date().toLocaleString('zh-CN'),
        remark: values.remark,
      };
      setInvoices([newInvoice, ...invoices]);
      message.success('开票申请提交成功');
      setApplyModalVisible(false);
    });
  };

  const handleApprove = (invoice: Invoice) => {
    setInvoices((prev) =>
      prev.map((i) =>
        i.id === invoice.id
          ? { ...i, status: 'approved' as const, approver: '当前用户', approveTime: new Date().toLocaleString('zh-CN') }
          : i
      )
    );
    message.success('开票申请已通过');
  };

  const handleRejectConfirm = (invoice: Invoice) => {
    setRejectingInvoice(invoice);
    rejectForm.resetFields();
    setRejectModalVisible(true);
  };

  const handleRejectSubmit = () => {
    rejectForm.validateFields().then((values) => {
      if (rejectingInvoice) {
        setInvoices((prev) =>
          prev.map((i) =>
            i.id === rejectingInvoice.id
              ? { ...i, status: 'rejected' as const, rejectReason: values.reason }
              : i
          )
        );
        message.success('开票申请已拒绝');
        setRejectModalVisible(false);
        setRejectingInvoice(null);
      }
    });
  };

  const handleStartProcess = (invoice: Invoice) => {
    setInvoices((prev) =>
      prev.map((i) =>
        i.id === invoice.id ? { ...i, status: 'processing' as const } : i
      )
    );
    message.success('开始开票');
  };

  const handleComplete = (invoice: Invoice) => {
    setInvoices((prev) =>
      prev.map((i) =>
        i.id === invoice.id ? { ...i, status: 'completed' as const } : i
      )
    );
    message.success('开票完成');
  };

  const handleCancel = (id: string) => {
    setInvoices((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, status: 'cancelled' as const } : i
      )
    );
    message.success('发票已取消');
  };

  const handleExport = () => {
    message.success('发票数据导出成功');
  };

  const getStatusTag = (status: InvoiceStatus) => {
    const config = {
      pending: { color: 'default', text: '待审核' },
      approved: { color: 'blue', text: '已通过' },
      rejected: { color: 'error', text: '已拒绝' },
      processing: { color: 'processing', text: '开票中' },
      completed: { color: 'success', text: '已完成' },
      cancelled: { color: 'default', text: '已取消' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const getTypeTag = (type: InvoiceType) => {
    const config = {
      vat: { color: 'red', text: '专票' },
      ordinary: { color: 'blue', text: '普票' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const filteredInvoices = invoices.filter((invoice) => {
    const matchSearch =
      !searchText ||
      invoice.invoiceNo.toLowerCase().includes(searchText.toLowerCase()) ||
      invoice.buyerName.toLowerCase().includes(searchText.toLowerCase()) ||
      invoice.buyerTaxNo.toLowerCase().includes(searchText.toLowerCase());
    const matchStatus = statusFilter === 'all' || invoice.status === statusFilter;
    const matchType = typeFilter === 'all' || invoice.type === typeFilter;
    return matchSearch && matchStatus && matchType;
  });

  const totalAmount = invoices.reduce((sum, i) => sum + i.totalAmount, 0);
  const pendingCount = invoices.filter((i) => i.status === 'pending').length;
  const completedCount = invoices.filter((i) => i.status === 'completed').length;

  const columns = [
    { title: '发票号码', dataIndex: 'invoiceNo', key: 'invoiceNo', width: 120 },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (type: InvoiceType) => getTypeTag(type),
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      render: (amount: number) => `¥${amount.toLocaleString()}`,
    },
    {
      title: '税额',
      dataIndex: 'taxAmount',
      key: 'taxAmount',
      width: 100,
      render: (tax: number) => (tax > 0 ? `¥${tax.toLocaleString()}` : '-'),
    },
    {
      title: '价税合计',
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      width: 120,
      render: (amount: number) => <Text strong>¥{amount.toLocaleString()}</Text>,
    },
    { title: '购买方', dataIndex: 'buyerName', key: 'buyerName', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: InvoiceStatus) => getStatusTag(status),
    },
    { title: '申请时间', dataIndex: 'applyTime', key: 'applyTime', width: 160 },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, record: Invoice) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          {record.status === 'pending' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
              >
                通过
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleRejectConfirm(record)}
              >
                拒绝
              </Button>
            </>
          )}
          {record.status === 'approved' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleStartProcess(record)}
            >
              开票
            </Button>
          )}
          {record.status === 'processing' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleComplete(record)}
            >
              完成
            </Button>
          )}
          {['pending', 'rejected'].includes(record.status) && (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => handleCancel(record.id)}
            >
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'list',
      label: `发票列表 (${invoices.length})`,
      children: (
        <Card
          size="small"
          title="发票列表"
          extra={
            <Space>
              <Button icon={<ExportOutlined />} onClick={handleExport}>
                导出
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleApply}>
                开票申请
              </Button>
            </Space>
          }
        >
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="搜索发票号/购买方/税号..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 280 }}
              prefix={<SearchOutlined />}
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="pending">待审核</Select.Option>
              <Select.Option value="approved">已通过</Select.Option>
              <Select.Option value="rejected">已拒绝</Select.Option>
              <Select.Option value="processing">开票中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="cancelled">已取消</Select.Option>
            </Select>
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部类型</Select.Option>
              <Select.Option value="vat">专票</Select.Option>
              <Select.Option value="ordinary">普票</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Space>
          <Table
            columns={columns}
            dataSource={filteredInvoices.map((i) => ({ ...i, key: i.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1400 }}
          />
        </Card>
      ),
    },
    {
      key: 'apply',
      label: '开票申请',
      children: (
        <Card
          size="small"
          title="提交开票申请"
          extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleApply}>新建申请</Button>}
        >
          <Alert
            message="开票申请说明"
            description="提交开票申请后，需要财务审核。审核通过后，系统将自动开票。请确保购买方信息准确无误。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="待审核申请"
                  value={pendingCount}
                  suffix="条"
                  valueStyle={{ color: pendingCount > 0 ? '#faad14' : undefined }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="本月已完成"
                  value={completedCount}
                  suffix="张"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="本月开票金额"
                  value={totalAmount}
                  suffix="元"
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
          </Row>
          <Card size="small" title="申请流程" style={{ marginTop: 16 }}>
            <Space>
              <Tag color="default">1. 提交申请</Tag>
              <span>→</span>
              <Tag color="blue">2. 财务审核</Tag>
              <span>→</span>
              <Tag color="processing">3. 开票处理</Tag>
              <span>→</span>
              <Tag color="success">4. 开票完成</Tag>
            </Space>
          </Card>
        </Card>
      ),
    },
    {
      key: 'review',
      label: `审核管理 (${pendingCount})`,
      children: (
        <Card size="small" title="待审核发票">
          <Alert
            message="审核说明"
            description="审核开票申请的购买方信息和金额。通过后发票将进入开票流程，拒绝后申请人需重新提交。"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            columns={columns.filter((col) => col.key !== 'actions')}
            dataSource={invoices
              .filter((i) => i.status === 'pending')
              .map((i) => ({ ...i, key: i.id }))}
            pagination={false}
            size="small"
            scroll={{ x: 1200 }}
          />
          {pendingCount === 0 && (
            <Alert
              message="暂无待审核发票"
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <DollarOutlined /> 财务开票信息
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="开票管理说明"
          description="管理发票申请、审核和开票流程。支持增值税专用发票和普通发票，支持发票导出功能。"
          type="info"
          showIcon
        />
        <Tabs items={tabItems} />
      </Space>

      {/* 开票申请弹窗 */}
      <Modal
        title="开票申请"
        open={applyModalVisible}
        onCancel={() => setApplyModalVisible(false)}
        onOk={handleApplySubmit}
        width={700}
        destroyOnClose
      >
        <Form form={applyForm} layout="vertical" preserve={false}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="projectName"
                label="项目名称"
                rules={[{ required: true, message: '请输入项目名称' }]}
              >
                <Input placeholder="如：数据中心建设一期" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="contractNo" label="合同编号">
                <Input placeholder="如：HT-2024-001" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="type"
                label="发票类型"
                rules={[{ required: true, message: '请选择发票类型' }]}
              >
                <Select options={TYPE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="amount"
                label="开票金额（元）"
                rules={[{ required: true, message: '请输入开票金额' }]}
              >
                <InputNumber
                  min={0}
                  precision={2}
                  style={{ width: '100%' }}
                  placeholder="请输入金额"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.type !== curr.type}>
            {() => {
              const type = applyForm.getFieldValue('type');
              const amount = applyForm.getFieldValue('amount') || 0;
              const taxAmount = type === 'vat' ? amount * 0.13 : 0;
              return (
                <Alert
                  message="税额计算"
                  description={
                    type === 'vat'
                      ? `增值税专用发票，税率13%，税额：¥${taxAmount.toFixed(2)}，价税合计：¥${(amount + taxAmount).toFixed(2)}`
                      : '普通发票，无税额'
                  }
                  type="info"
                  showIcon
                />
              );
            }}
          </Form.Item>

          <Divider orientationMargin={0}>购买方信息</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="buyerName"
                label="购买方名称"
                rules={[{ required: true, message: '请输入购买方名称' }]}
              >
                <Input placeholder="如：科技有限公司" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="buyerTaxNo"
                label="纳税人识别号"
                rules={[{ required: true, message: '请输入纳税人识别号' }]}
              >
                <Input placeholder="如：91110000MA01234567" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="buyerAddress" label="地址电话">
                <Input placeholder="地址、电话" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="buyerBank" label="开户行及账号">
                <Input placeholder="开户行、账号" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="remark" label="备注">
            <TextArea rows={3} placeholder="备注信息（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 拒绝理由弹窗 */}
      <Modal
        title="拒绝开票申请"
        open={rejectModalVisible}
        onCancel={() => setRejectModalVisible(false)}
        onOk={handleRejectSubmit}
        destroyOnClose
      >
        <Form form={rejectForm} layout="vertical" preserve={false}>
          <Form.Item
            name="reason"
            label="拒绝理由"
            rules={[{ required: true, message: '请输入拒绝理由' }]}
          >
            <TextArea rows={4} placeholder="请输入拒绝理由..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 发票详情抽屉 */}
      <Drawer
        title="发票详情"
        placement="right"
        width={600}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {viewingInvoice && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title="基本信息">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="发票号码">
                  <Text code copyable>
                    {viewingInvoice.invoiceNo}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="发票代码">
                  <Text code copyable>
                    {viewingInvoice.invoiceCode}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="发票类型">
                  {getTypeTag(viewingInvoice.type)}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  {getStatusTag(viewingInvoice.status)}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="金额信息">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="金额">
                  <Text style={{ fontSize: 16 }}>¥{viewingInvoice.amount.toLocaleString()}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="税额">
                  <Text type={viewingInvoice.taxAmount > 0 ? 'danger' : 'secondary'}>
                    {viewingInvoice.taxAmount > 0 ? `¥${viewingInvoice.taxAmount.toLocaleString()}` : '无'}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="价税合计">
                  <Text strong style={{ fontSize: 18, color: '#1890ff' }}>
                    ¥{viewingInvoice.totalAmount.toLocaleString()}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="购买方信息">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="购买方名称">
                  {viewingInvoice.buyerName}
                </Descriptions.Item>
                <Descriptions.Item label="纳税人识别号">
                  <Text code copyable>
                    {viewingInvoice.buyerTaxNo}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="流程信息">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="申请时间">
                  {viewingInvoice.applyTime}
                </Descriptions.Item>
                <Descriptions.Item label="审核人">
                  {viewingInvoice.approver || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="审核时间">
                  {viewingInvoice.approveTime || '-'}
                </Descriptions.Item>
                {viewingInvoice.rejectReason && (
                  <Descriptions.Item label="拒绝理由">
                    <Text type="danger">{viewingInvoice.rejectReason}</Text>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </Card>

            {viewingInvoice.status === 'pending' && (
              <Card size="small">
                <Space>
                  <Button
                    type="primary"
                    icon={<CheckOutlined />}
                    onClick={() => {
                      setDetailDrawerVisible(false);
                      handleApprove(viewingInvoice);
                    }}
                  >
                    审核通过
                  </Button>
                  <Button
                    danger
                    icon={<CloseOutlined />}
                    onClick={() => {
                      setDetailDrawerVisible(false);
                      handleRejectConfirm(viewingInvoice);
                    }}
                  >
                    审核拒绝
                  </Button>
                </Space>
              </Card>
            )}
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default Invoices;
