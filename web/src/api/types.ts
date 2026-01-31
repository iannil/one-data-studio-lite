/**
 * 统一 API 响应类型定义
 *
 * 与后端 services/common/api_response.py 保持一致
 */

/** 统一 API 响应格式 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data?: T;
  timestamp: number;
}

/** 分页数据结构 */
export interface PageData<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** 分页响应 */
export interface PaginatedResponse<T = unknown> extends ApiResponse {
  data?: PageData<T>;
}

/** 错误响应 */
export interface ErrorResponse extends ApiResponse {
  code: number;
  message: string;
  data: null;
  timestamp: number;
  detail?: unknown;
}

/** 业务状态码 */
export enum ErrorCode {
  // 成功类 (2xxxx)
  SUCCESS = 20000,
  CREATED = 20001,
  ACCEPTED = 20002,
  NO_CONTENT = 20003,

  // 参数错误 (4xxxx)
  INVALID_PARAMS = 40001,
  MISSING_PARAM = 40002,
  INVALID_FORMAT = 40003,
  VALIDATION_FAILED = 40004,

  // 认证/授权 (401xx)
  UNAUTHORIZED = 40100,
  TOKEN_EXPIRED = 40101,
  TOKEN_INVALID = 40102,
  PERMISSION_DENIED = 40300,

  // 资源错误 (404xx)
  NOT_FOUND = 40400,
  RESOURCE_NOT_FOUND = 40401,
  USER_NOT_FOUND = 40402,
  CONFIG_NOT_FOUND = 40403,

  // 业务规则 (410xx)
  DUPLICATE_RESOURCE = 41001,
  OPERATION_NOT_ALLOWED = 41002,
  INVALID_STATE = 41003,
  QUOTA_EXCEEDED = 41004,

  // 外部服务错误 (42xxx)
  EXTERNAL_SERVICE_ERROR = 42000,
  DATABASE_ERROR = 42001,
  CACHE_ERROR = 42002,
  MESSAGE_QUEUE_ERROR = 42003,

  // 上游子系统错误
  SEATUNNEL_ERROR = 42100,
  DATAHUB_ERROR = 42101,
  DOLPHINSCHEDULER_ERROR = 42102,
  SUPERSET_ERROR = 42103,
  SHARDINGSPHERE_ERROR = 42104,
  HOP_ERROR = 42105,
  CUBE_STUDIO_ERROR = 42106,

  // 系统错误 (5xxxx)
  INTERNAL_ERROR = 50000,
  SERVICE_UNAVAILABLE = 50300,
  GATEWAY_TIMEOUT = 50400,
}

/** 错误信息映射 */
const ERROR_MESSAGES: Record<number, string> = {
  [ErrorCode.SUCCESS]: "操作成功",
  [ErrorCode.CREATED]: "创建成功",
  [ErrorCode.ACCEPTED]: "请求已接受",
  [ErrorCode.NO_CONTENT]: "无数据",
  [ErrorCode.INVALID_PARAMS]: "参数错误",
  [ErrorCode.MISSING_PARAM]: "缺少必要参数",
  [ErrorCode.INVALID_FORMAT]: "格式错误",
  [ErrorCode.VALIDATION_FAILED]: "参数校验失败",
  [ErrorCode.UNAUTHORIZED]: "未授权",
  [ErrorCode.TOKEN_EXPIRED]: "Token 已过期",
  [ErrorCode.TOKEN_INVALID]: "Token 无效",
  [ErrorCode.PERMISSION_DENIED]: "权限不足",
  [ErrorCode.NOT_FOUND]: "资源不存在",
  [ErrorCode.RESOURCE_NOT_FOUND]: "资源不存在",
  [ErrorCode.USER_NOT_FOUND]: "用户不存在",
  [ErrorCode.CONFIG_NOT_FOUND]: "配置不存在",
  [ErrorCode.DUPLICATE_RESOURCE]: "资源已存在",
  [ErrorCode.OPERATION_NOT_ALLOWED]: "操作不允许",
  [ErrorCode.INVALID_STATE]: "状态无效",
  [ErrorCode.QUOTA_EXCEEDED]: "超出配额",
  [ErrorCode.EXTERNAL_SERVICE_ERROR]: "外部服务错误",
  [ErrorCode.DATABASE_ERROR]: "数据库错误",
  [ErrorCode.CACHE_ERROR]: "缓存错误",
  [ErrorCode.MESSAGE_QUEUE_ERROR]: "消息队列错误",
  [ErrorCode.SEATUNNEL_ERROR]: "SeaTunnel 服务错误",
  [ErrorCode.DATAHUB_ERROR]: "DataHub 服务错误",
  [ErrorCode.DOLPHINSCHEDULER_ERROR]: "DolphinScheduler 服务错误",
  [ErrorCode.SUPERSET_ERROR]: "Superset 服务错误",
  [ErrorCode.SHARDINGSPHERE_ERROR]: "ShardingSphere 服务错误",
  [ErrorCode.HOP_ERROR]: "Hop 服务错误",
  [ErrorCode.CUBE_STUDIO_ERROR]: "Cube-Studio 服务错误",
  [ErrorCode.INTERNAL_ERROR]: "内部服务错误",
  [ErrorCode.SERVICE_UNAVAILABLE]: "服务不可用",
  [ErrorCode.GATEWAY_TIMEOUT]: "网关超时",
};

/** 获取错误信息 */
export function getErrorMessage(code: number): string {
  return ERROR_MESSAGES[code] || "未知错误";
}

/** 判断响应是否成功 */
export function isSuccessResponse<T>(response: ApiResponse<T>): response is ApiResponse<T> & { data: T } {
  return response.code === ErrorCode.SUCCESS;
}

/** 判断响应是否为特定错误 */
export function isErrorCode<T>(response: ApiResponse<T>, errorCode: ErrorCode): boolean {
  return response.code === errorCode;
}

/** 创建成功响应 */
export function createSuccessResponse<T>(data: T, message: string = "success"): ApiResponse<T> {
  return {
    code: ErrorCode.SUCCESS,
    message,
    data,
    timestamp: Math.floor(Date.now() / 1000),
  };
}

/** 创建错误响应 */
export function createErrorResponse(
  code: number,
  message?: string,
  detail?: unknown,
): ErrorResponse {
  return {
    code,
    message: message || getErrorMessage(code),
    data: null,
    timestamp: Math.floor(Date.now() / 1000),
    detail,
  };
}

/** 创建分页响应 */
export function createPaginatedResponse<T>(
  items: T[],
  total: number,
  page: number = 1,
  pageSize: number = 10,
  message: string = "success",
): PaginatedResponse<T> {
  const pages = pageSize > 0 ? Math.ceil(total / pageSize) : 0;

  return {
    code: ErrorCode.SUCCESS,
    message,
    data: {
      items,
      total,
      page,
      page_size: pageSize,
      pages,
    },
    timestamp: Math.floor(Date.now() / 1000),
  };
}
