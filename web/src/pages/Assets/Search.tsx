import React, { useState } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Select,
  Typography,
  Space,
  Alert,
  DatePicker,
  Checkbox,
  Badge,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  StarOutlined,
  StarFilled,
  DatabaseOutlined,
  TableOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

type AssetType = 'table' | 'view' | 'dashboard' | 'pipeline' | 'api';
type DataSource = 'mysql' | 'postgresql' | 'hive' | 'kafka' | 'elasticsearch';

interface Asset {
  id: string;
  name: string;
  type: AssetType;
  dataSource: DataSource;
  database?: string;
  schema?: string;
  description?: string;
  tags: string[];
  owner: string;
  updatedAt: string;
  isFavorite: boolean;
  row_count?: number;
}

const DEMO_ASSETS: Asset[] = [
  {
    id: '1',
    name: 'user_info',
    type: 'table',
    dataSource: 'mysql',
    database: 'user_db',
    schema: 'public',
    description: '用户基本信息表',
    tags: ['用户', '核心'],
    owner: 'admin',
    updatedAt: '2026-01-30',
    isFavorite: true,
    row_count: 1523456,
  },
  {
    id: '2',
    name: 'order_summary',
    type: 'view',
    dataSource: 'postgresql',
    database: 'analytics',
    schema: 'reporting',
    description: '订单汇总视图',
    tags: ['订单', '报表'],
    owner: 'data_team',
    updatedAt: '2026-01-29',
    isFavorite: false,
  },
  {
    id: '3',
    name: 'user_events_stream',
    type: 'table',
    dataSource: 'kafka',
    description: '用户行为事件流',
    tags: ['事件', '实时'],
    owner: 'platform',
    updatedAt: '2026-01-31',
    isFavorite: false,
  },
  {
    id: '4',
    name: 'sales_dashboard',
    type: 'dashboard',
    dataSource: 'superset',
    description: '销售数据可视化看板',
    tags: ['销售', 'BI'],
    owner: 'bi_team',
    updatedAt: '2026-01-28',
    isFavorite: true,
  },
  {
    id: '5',
    name: 'data_quality_pipeline',
    type: 'pipeline',
    dataSource: 'dolphinscheduler',
    description: '数据质量检查流程',
    tags: ['质量', 'ETL'],
    owner: 'etl_team',
    updatedAt: '2026-01-25',
    isFavorite: false,
  },
  {
    id: '6',
    name: 'user_profile_api',
    type: 'api',
    dataSource: 'data_api',
    description: '用户画像查询接口',
    tags: ['API', '用户'],
    owner: 'api_team',
    updatedAt: '2026-01-20',
    isFavorite: false,
  },
];

const ASSET_TYPE_OPTIONS = [
  { label: '数据表', value: 'table' },
  { label: '视图', value: 'view' },
  { label: '看板', value: 'dashboard' },
  { label: '流程', value: 'pipeline' },
  { label: 'API', value: 'api' },
];

const DATA_SOURCE_OPTIONS = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'Hive', value: 'hive' },
  { label: 'Kafka', value: 'kafka' },
  { label: 'Elasticsearch', value: 'elasticsearch' },
];

const POPULAR_TAGS = ['用户', '订单', '产品', '销售', '日志', '实时', '报表'];

const Search: React.FC = () => {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [filteredAssets, setFilteredAssets] = useState<Asset[]>(DEMO_ASSETS);
  const [selectedTypes, setSelectedTypes] = useState<AssetType[]>([]);
  const [selectedSources, setSelectedSources] = useState<DataSource[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [filterVisible, setFilterVisible] = useState(false);
  const [favorites, setFavorites] = useState<Set<string>>(new Set(['1', '4']));

  const handleSearch = (value: string) => {
    setSearchText(value);
    applyFilters(value, selectedTypes, selectedSources, selectedTags);
  };

  const applyFilters = (
    search: string,
    types: AssetType[],
    sources: DataSource[],
    tags: string[]
  ) => {
    let result = DEMO_ASSETS;

    if (search) {
      const lowerSearch = search.toLowerCase();
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(lowerSearch) ||
          a.description?.toLowerCase().includes(lowerSearch)
      );
    }

    if (types.length > 0) {
      result = result.filter((a) => types.includes(a.type));
    }

    if (sources.length > 0) {
      result = result.filter((a) => sources.includes(a.dataSource));
    }

    if (tags.length > 0) {
      result = result.filter((a) => tags.some((t) => a.tags.includes(t)));
    }

    setFilteredAssets(result);
  };

  const handleTypeChange = (types: AssetType[]) => {
    setSelectedTypes(types);
    applyFilters(searchText, types, selectedSources, selectedTags);
  };

  const handleSourceChange = (sources: DataSource[]) => {
    setSelectedSources(sources);
    applyFilters(searchText, selectedTypes, sources, selectedTags);
  };

  const handleTagClick = (tag: string) => {
    const newTags = selectedTags.includes(tag)
      ? selectedTags.filter((t) => t !== tag)
      : [...selectedTags, tag];
    setSelectedTags(newTags);
    applyFilters(searchText, selectedTypes, selectedSources, newTags);
  };

  const toggleFavorite = (id: string) => {
    setFavorites((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const getTypeIcon = (type: AssetType) => {
    const icons: Record<AssetType, React.ReactNode> = {
      table: <DatabaseOutlined />,
      view: <DatabaseOutlined />,
      dashboard: <TableOutlined />,
      pipeline: <FileTextOutlined />,
      api: <FileTextOutlined />,
    };
    return icons[type];
  };

  const getTypeTag = (type: AssetType) => {
    const config: Record<AssetType, { color: string; text: string }> = {
      table: { color: 'blue', text: '数据表' },
      view: { color: 'cyan', text: '视图' },
      dashboard: { color: 'purple', text: '看板' },
      pipeline: { color: 'green', text: '流程' },
      api: { color: 'orange', text: 'API' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const getSourceTag = (source: DataSource) => {
    const opt = DATA_SOURCE_OPTIONS.find((o) => o.value === source);
    return <Tag>{opt?.label || source}</Tag>;
  };

  const columns = [
    {
      title: '资产名称',
      key: 'name',
      render: (_: unknown, record: Asset) => (
        <Space>
          {getTypeIcon(record.type)}
          <span>
            {record.name}
            {record.database && <Text type="secondary"> ({record.database})</Text>}
          </span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: AssetType) => getTypeTag(type),
    },
    {
      title: '数据源',
      dataIndex: 'dataSource',
      key: 'dataSource',
      width: 120,
      render: (source: DataSource) => getSourceTag(source),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <>
          {tags.slice(0, 2).map((t) => (
            <Tag key={t} color="geekblue">
              {t}
            </Tag>
          ))}
          {tags.length > 2 && <Tag>+{tags.length - 2}</Tag>}
        </>
      ),
    },
    {
      title: '所有者',
      dataIndex: 'owner',
      key: 'owner',
      width: 120,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 120,
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: Asset) => (
        <Button
          type="text"
          size="small"
          icon={favorites.has(record.id) ? <StarFilled /> : <StarOutlined />}
          onClick={() => toggleFavorite(record.id)}
          style={{ color: favorites.has(record.id) ? '#faad14' : undefined }}
        />
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SearchOutlined /> 资产检索
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="全文搜索"
          description="支持按资产名称、描述、标签、数据源类型进行检索。点击星标可收藏常用资产。"
          type="info"
          showIcon
        />

        {/* 搜索输入区 */}
        <Card size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.Search
              placeholder="搜索资产名称、描述、标签..."
              value={searchText}
              onChange={(e) => handleSearch(e.target.value)}
              onSearch={handleSearch}
              size="large"
              allowClear
              enterButton={<Button icon={<SearchOutlined />}>搜索</Button>}
            />

            {/* 高级筛选 */}
            <Space wrap>
              <Button
                icon={<FilterOutlined />}
                onClick={() => setFilterVisible(!filterVisible)}
              >
                高级筛选 {filterVisible ? '收起' : '展开'}
              </Button>

              {filterVisible && (
                <>
                  <Select
                    mode="multiple"
                    placeholder="资产类型"
                    value={selectedTypes}
                    onChange={handleTypeChange}
                    options={ASSET_TYPE_OPTIONS}
                    style={{ width: 200 }}
                    allowClear
                  />
                  <Select
                    mode="multiple"
                    placeholder="数据源"
                    value={selectedSources}
                    onChange={handleSourceChange}
                    options={DATA_SOURCE_OPTIONS}
                    style={{ width: 200 }}
                    allowClear
                  />
                  <RangePicker placeholder={['开始时间', '结束时间']} />
                </>
              )}
            </Space>

            {/* 热门标签 */}
            <Space wrap>
              <Text type="secondary">热门标签：</Text>
              {POPULAR_TAGS.map((tag) => (
                <CheckableTag
                  key={tag}
                  checked={selectedTags.includes(tag)}
                  onChange={(checked) => {
                    if (checked) {
                      handleTagClick(tag);
                    }
                  }}
                >
                  {tag}
                </CheckableTag>
              ))}
            </Space>

            {/* 已选筛选条件 */}
            {(selectedTypes.length > 0 || selectedSources.length > 0 || selectedTags.length > 0) && (
              <Space wrap>
                <Text type="secondary">已选：</Text>
                {selectedTypes.map((t) => {
                  const opt = ASSET_TYPE_OPTIONS.find((o) => o.value === t);
                  return (
                    <Tag
                      key={t}
                      closable
                      onClose={() => handleTypeChange(selectedTypes.filter((x) => x !== t))}
                    >
                      {opt?.label}
                    </Tag>
                  );
                })}
                {selectedSources.map((s) => {
                  const opt = DATA_SOURCE_OPTIONS.find((o) => o.value === s);
                  return (
                    <Tag
                      key={s}
                      closable
                      onClose={() => handleSourceChange(selectedSources.filter((x) => x !== s))}
                    >
                      {opt?.label}
                    </Tag>
                  );
                })}
                {selectedTags.map((t) => (
                  <Tag
                    key={t}
                    closable
                    onClose={() => {
                      const newTags = selectedTags.filter((x) => x !== t);
                      setSelectedTags(newTags);
                      applyFilters(searchText, selectedTypes, selectedSources, newTags);
                    }}
                  >
                    {t}
                  </Tag>
                ))}
              </Space>
            )}
          </Space>
        </Card>

        {/* 搜索结果 */}
        <Card
          size="small"
          title={`搜索结果 (${filteredAssets.length})`}
        >
          <Table
            columns={columns}
            dataSource={filteredAssets.map((a) => ({ ...a, key: a.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            onRow={(record) => ({
              onDoubleClick: () => {
                navigate(`/assets/detail/${record.id}`);
              },
            })}
          />
        </Card>
      </Space>
    </div>
  );
};

const CheckableTag: React.FC<{
  children: React.ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
}> = ({ children, checked, onChange }) => {
  return (
    <Tag
      checkable
      checked={checked}
      onChange={onChange}
      style={{ cursor: 'pointer' }}
    >
      {children}
    </Tag>
  );
};

export default Search;
