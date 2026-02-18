'use client';

import { useMemo, useState } from 'react';
import { Card, Segmented, Empty, Spin, Typography } from 'antd';
import {
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  DotChartOutlined,
  TableOutlined,
} from '@ant-design/icons';
import { Column, Line, Pie, Scatter, Area } from '@ant-design/charts';

const { Text } = Typography;

export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'table';

export interface VisualizationSuggestion {
  chart_type: ChartType;
  x_axis?: string;
  y_axis?: string;
  group_by?: string;
}

export interface ChartRendererProps {
  data: Record<string, unknown>[];
  columns: string[];
  suggestion?: VisualizationSuggestion;
  loading?: boolean;
  height?: number;
  showTypeSelector?: boolean;
  title?: string;
}

interface ChartConfig {
  data: Record<string, unknown>[];
  xField: string;
  yField: string;
  colorField?: string;
  height: number;
}

const CHART_TYPE_OPTIONS = [
  { value: 'bar', icon: <BarChartOutlined />, label: '柱状图' },
  { value: 'line', icon: <LineChartOutlined />, label: '折线图' },
  { value: 'pie', icon: <PieChartOutlined />, label: '饼图' },
  { value: 'scatter', icon: <DotChartOutlined />, label: '散点图' },
  { value: 'area', icon: <LineChartOutlined />, label: '面积图' },
  { value: 'table', icon: <TableOutlined />, label: '表格' },
];

const inferNumericColumn = (data: Record<string, unknown>[], columns: string[]): string | null => {
  if (data.length === 0) return null;
  const sample = data[0];
  return columns.find((col) => typeof sample[col] === 'number') ?? null;
};

const inferCategoryColumn = (data: Record<string, unknown>[], columns: string[]): string | null => {
  if (data.length === 0) return null;
  const sample = data[0];
  return columns.find((col) => typeof sample[col] === 'string') ?? columns[0] ?? null;
};

const transformDataForPie = (
  data: Record<string, unknown>[],
  categoryField: string,
  valueField: string
): Array<{ category: string; value: number }> => {
  const aggregated = new Map<string, number>();
  data.forEach((row) => {
    const category = String(row[categoryField] ?? 'Unknown');
    const value = Number(row[valueField]) || 0;
    aggregated.set(category, (aggregated.get(category) ?? 0) + value);
  });
  return Array.from(aggregated.entries()).map(([category, value]) => ({
    category,
    value,
  }));
};

export default function ChartRenderer({
  data,
  columns,
  suggestion,
  loading = false,
  height = 400,
  showTypeSelector = true,
  title,
}: ChartRendererProps) {
  const initialType = suggestion?.chart_type ?? 'bar';
  const [chartType, setChartType] = useState<ChartType>(initialType);

  const chartConfig = useMemo((): ChartConfig | null => {
    if (!data || data.length === 0 || columns.length === 0) {
      return null;
    }

    const xField = suggestion?.x_axis ?? inferCategoryColumn(data, columns) ?? columns[0];
    const yField = suggestion?.y_axis ?? inferNumericColumn(data, columns) ?? columns[1] ?? columns[0];
    const colorField = suggestion?.group_by;

    return {
      data,
      xField,
      yField,
      colorField,
      height,
    };
  }, [data, columns, suggestion, height]);

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            Loading chart...
          </Text>
        </div>
      </Card>
    );
  }

  if (!chartConfig) {
    return (
      <Card title={title}>
        <Empty description="No data available for visualization" />
      </Card>
    );
  }

  const renderChart = () => {
    const { xField, yField, colorField, height: chartHeight } = chartConfig;
    const chartData = chartConfig.data;

    switch (chartType) {
      case 'bar':
        return (
          <Column
            data={chartData}
            xField={xField}
            yField={yField}
            colorField={colorField}
            height={chartHeight}
            label={{
              position: 'middle',
            }}
            xAxis={{
              label: {
                autoRotate: true,
                autoHide: true,
              },
            }}
          />
        );

      case 'line':
        return (
          <Line
            data={chartData}
            xField={xField}
            yField={yField}
            seriesField={colorField}
            height={chartHeight}
            smooth
            point={{
              size: 3,
              shape: 'circle',
            }}
          />
        );

      case 'area':
        return (
          <Area
            data={chartData}
            xField={xField}
            yField={yField}
            seriesField={colorField}
            height={chartHeight}
          />
        );

      case 'pie': {
        const pieData = transformDataForPie(chartData, xField, yField);
        return (
          <Pie
            data={pieData}
            angleField="value"
            colorField="category"
            height={chartHeight}
            radius={0.8}
            innerRadius={0.5}
            label={{
              type: 'spider',
              content: '{name}: {percentage}',
            }}
            interactions={[{ type: 'element-active' }]}
          />
        );
      }

      case 'scatter':
        return (
          <Scatter
            data={chartData}
            xField={xField}
            yField={yField}
            colorField={colorField}
            height={chartHeight}
            size={5}
            shape="circle"
          />
        );

      case 'table':
      default:
        return null;
    }
  };

  return (
    <Card
      title={title}
      extra={
        showTypeSelector && (
          <Segmented
            value={chartType}
            onChange={(value) => setChartType(value as ChartType)}
            options={CHART_TYPE_OPTIONS.map((opt) => ({
              value: opt.value,
              icon: opt.icon,
              title: opt.label,
            }))}
            size="small"
          />
        )
      }
    >
      {chartType === 'table' ? (
        <Empty description="Table view - use the Table component" />
      ) : (
        renderChart()
      )}
    </Card>
  );
}
