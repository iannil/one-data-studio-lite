import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/Layout/MainLayout';
import Login from './pages/Login';

// Dashboard
import Cockpit from './pages/Dashboard/Cockpit';
import Workspace from './pages/Dashboard/Workspace';
import Notifications from './pages/Dashboard/Notifications';
import Profile from './pages/Dashboard/Profile';

// Planning (数据规划)
import DataSources from './pages/Planning/DataSources';
import MetadataBrowser from './pages/Planning/MetadataBrowser';
import Tags from './pages/Planning/Tags';
import Lineage from './pages/Planning/Lineage';
import Standards from './pages/Planning/Standards';

// Collection (数据汇聚)
import SyncJobs from './pages/Collection/SyncJobs';
import ScheduleManage from './pages/Collection/ScheduleManage';
import TaskMonitor from './pages/Collection/TaskMonitor';
import EtlFlows from './pages/Collection/EtlFlows';

// Development (数据开发)
import CleaningRules from './pages/Development/CleaningRules';
import QualityCheck from './pages/Development/QualityCheck';
import TransformConfig from './pages/Development/TransformConfig';
import FieldMapping from './pages/Development/FieldMapping';
import OcrProcessing from './pages/Development/OcrProcessing';
import DataFusion from './pages/Development/DataFusion';
import FillMissing from './pages/Development/FillMissing';

// Analysis (数据分析)
import Bi from './pages/Analysis/Bi';
import Charts from './pages/Analysis/Charts';
import Pipelines from './pages/Analysis/Pipelines';
import NL2SQL from './pages/Analysis/NL2SQL';
import Alerts from './pages/Analysis/Alerts';
import EtlLink from './pages/Analysis/EtlLink';

// Assets (数据资产)
import Catalog from './pages/Assets/Catalog';
import DataApiManage from './pages/Assets/DataApiManage';
import MetadataSync from './pages/Assets/MetadataSync';
import AssetDetail from './pages/Assets/AssetDetail';
import Search from './pages/Assets/Search';

// Security (安全与权限)
import Sensitive from './pages/Security/Sensitive';
import Permissions from './pages/Security/Permissions';
import Sso from './pages/Security/Sso';

// Support (统一支撑)
import Announcements from './pages/Support/Announcements';
import Invoices from './pages/Support/Invoices';
import Content from './pages/Support/Content';

// Operations (系统运维)
import AuditLog from './pages/Operations/AuditLog';
import Users from './pages/Operations/Users';
import ApiGateway from './pages/Operations/ApiGateway';
import Monitor from './pages/Operations/Monitor';
import Tenants from './pages/Operations/Tenants';

import { useAuthStore } from './store/authStore';

// 路由守卫组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          {/* 公开路由 */}
          <Route path="/login" element={<Login />} />

          {/* 需要认证的路由 */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard/cockpit" replace />} />

            {/* 工作台 */}
            <Route path="dashboard/workspace" element={<Workspace />} />
            <Route path="dashboard/notifications" element={<Notifications />} />
            <Route path="dashboard/profile" element={<Profile />} />
            <Route path="dashboard/cockpit" element={<Cockpit />} />

            {/* 数据规划 */}
            <Route path="planning/datasources" element={<DataSources />} />
            <Route path="planning/metadata" element={<MetadataBrowser />} />
            <Route path="planning/tags" element={<Tags />} />
            <Route path="planning/standards" element={<Standards />} />
            <Route path="planning/lineage" element={<Lineage />} />

            {/* 数据汇聚 */}
            <Route path="collection/sync-jobs" element={<SyncJobs />} />
            <Route path="collection/schedules" element={<ScheduleManage />} />
            <Route path="collection/task-monitor" element={<TaskMonitor />} />
            <Route path="collection/etl-flows" element={<EtlFlows />} />

            {/* 数据开发 */}
            <Route path="development/cleaning" element={<CleaningRules />} />
            <Route path="development/field-mapping" element={<FieldMapping />} />
            <Route path="development/ocr" element={<OcrProcessing />} />
            <Route path="development/fusion" element={<DataFusion />} />
            <Route path="development/fill-missing" element={<FillMissing />} />
            <Route path="development/quality" element={<QualityCheck />} />
            <Route path="development/transform" element={<TransformConfig />} />

            {/* 数据分析 */}
            <Route path="analysis/bi" element={<Bi />} />
            <Route path="analysis/alerts" element={<Alerts />} />
            <Route path="analysis/etl-link" element={<EtlLink />} />
            <Route path="analysis/charts" element={<Charts />} />
            <Route path="analysis/nl2sql" element={<NL2SQL />} />
            <Route path="analysis/pipelines" element={<Pipelines />} />

            {/* 数据资产 */}
            <Route path="assets/catalog" element={<Catalog />} />
            <Route path="assets/search" element={<Search />} />
            <Route path="assets/data-api" element={<DataApiManage />} />
            <Route path="assets/sync" element={<MetadataSync />} />
            <Route path="assets/detail/:id" element={<AssetDetail />} />

            {/* 安全与权限 */}
            <Route path="security/permissions" element={<Permissions />} />
            <Route path="security/sso" element={<Sso />} />
            <Route path="security/sensitive" element={<Sensitive />} />

            {/* 统一支撑 */}
            <Route path="support/announcements" element={<Announcements />} />
            <Route path="support/invoices" element={<Invoices />} />
            <Route path="support/content" element={<Content />} />

            {/* 系统运维 */}
            <Route path="operations/users" element={<Users />} />
            <Route path="operations/audit" element={<AuditLog />} />
            <Route path="operations/api-gateway" element={<ApiGateway />} />
            <Route path="operations/monitor" element={<Monitor />} />
            <Route path="operations/tenants" element={<Tenants />} />

            {/* 旧路由兼容重定向 */}
            <Route path="dashboard" element={<Navigate to="/dashboard/cockpit" replace />} />
            <Route path="metadata/*" element={<Navigate to="/planning/datasources" replace />} />
            <Route path="ingestion/*" element={<Navigate to="/collection/sync-jobs" replace />} />
            <Route path="processing/*" element={<Navigate to="/development/cleaning" replace />} />
            <Route path="nl2sql" element={<Navigate to="/analysis/nl2sql" replace />} />
            <Route path="sensitive" element={<Navigate to="/security/sensitive" replace />} />
            <Route path="audit" element={<Navigate to="/operations/audit" replace />} />
            <Route path="analysis/dashboards" element={<Navigate to="/analysis/bi" replace />} />
            <Route path="security/audit" element={<Navigate to="/operations/audit" replace />} />
          </Route>

          {/* 404 重定向 */}
          <Route path="*" element={<Navigate to="/dashboard/cockpit" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
