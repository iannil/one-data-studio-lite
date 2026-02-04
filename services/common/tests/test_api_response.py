"""Tests for API response utilities

Tests unified API response format including:
- Success responses
- Error responses
- Paginated responses
- Error code mappings
- HTTP status code mappings
"""

import time

from services.common.api_response import (
    ERROR_MESSAGES,
    HTTP_STATUS_MAP,
    ApiResponse,
    ErrorCode,
    PageData,
    PaginatedResponse,
    error,
    get_error_message,
    get_http_status,
    paginated,
    success,
)


class TestErrorCode:
    """Tests for ErrorCode enum"""

    def test_success_codes(self):
        """Should have success-related error codes"""
        assert ErrorCode.SUCCESS == 20000
        assert ErrorCode.CREATED == 20001
        assert ErrorCode.ACCEPTED == 20002
        assert ErrorCode.NO_CONTENT == 20003

    def test_parameter_error_codes(self):
        """Should have parameter error codes"""
        assert ErrorCode.INVALID_PARAMS == 40001
        assert ErrorCode.MISSING_PARAM == 40002
        assert ErrorCode.INVALID_FORMAT == 40003
        assert ErrorCode.VALIDATION_FAILED == 40004

    def test_auth_error_codes(self):
        """Should have authentication/authorization error codes"""
        assert ErrorCode.UNAUTHORIZED == 40100
        assert ErrorCode.TOKEN_EXPIRED == 40101
        assert ErrorCode.TOKEN_INVALID == 40102
        assert ErrorCode.PERMISSION_DENIED == 40300

    def test_not_found_codes(self):
        """Should have resource not found error codes"""
        assert ErrorCode.NOT_FOUND == 40400
        assert ErrorCode.RESOURCE_NOT_FOUND == 40401
        assert ErrorCode.USER_NOT_FOUND == 40402
        assert ErrorCode.CONFIG_NOT_FOUND == 40403

    def test_business_rule_codes(self):
        """Should have business rule error codes"""
        assert ErrorCode.DUPLICATE_RESOURCE == 41001
        assert ErrorCode.OPERATION_NOT_ALLOWED == 41002
        assert ErrorCode.INVALID_STATE == 41003
        assert ErrorCode.QUOTA_EXCEEDED == 41004

    def test_external_service_codes(self):
        """Should have external service error codes"""
        assert ErrorCode.EXTERNAL_SERVICE_ERROR == 42000
        assert ErrorCode.DATABASE_ERROR == 42001
        assert ErrorCode.CACHE_ERROR == 42002
        assert ErrorCode.SEATUNNEL_ERROR == 42100
        assert ErrorCode.OPENMETADATA_ERROR == 42101
        assert ErrorCode.DOLPHINSCHEDULER_ERROR == 42102
        assert ErrorCode.SUPERSET_ERROR == 42103
        assert ErrorCode.HOP_ERROR == 42104
        assert ErrorCode.CUBE_STUDIO_ERROR == 42105

    def test_system_error_codes(self):
        """Should have system error codes"""
        assert ErrorCode.INTERNAL_ERROR == 50000
        assert ErrorCode.SERVICE_UNAVAILABLE == 50300
        assert ErrorCode.GATEWAY_TIMEOUT == 50400


class TestApiResponse:
    """Tests for ApiResponse model"""

    def test_default_values(self):
        """Should use default values when not provided"""
        response = ApiResponse()
        assert response.code == ErrorCode.SUCCESS
        assert response.message == "success"
        assert response.data is None
        assert isinstance(response.timestamp, int)
        assert response.timestamp > 0

    def test_custom_values(self):
        """Should use provided values"""
        response = ApiResponse(
            code=ErrorCode.CREATED,
            message="Created successfully",
            data={"id": 1},
        )
        assert response.code == ErrorCode.CREATED
        assert response.message == "Created successfully"
        assert response.data == {"id": 1}

    def test_timestamp_is_current(self):
        """Should generate current timestamp"""
        before = int(time.time())
        response = ApiResponse()
        after = int(time.time())
        assert before <= response.timestamp <= after

    def test_generic_type_with_dict(self):
        """Should work with dict type"""
        response = ApiResponse[dict[str, int]](data={"count": 42})
        assert response.data == {"count": 42}

    def test_serialization(self):
        """Should be serializable to JSON"""
        response = ApiResponse(
            code=ErrorCode.SUCCESS,
            message="OK",
            data={"key": "value"},
        )
        serialized = response.model_dump()
        assert serialized["code"] == ErrorCode.SUCCESS
        assert serialized["message"] == "OK"
        assert serialized["data"] == {"key": "value"}
        assert "timestamp" in serialized


class TestPageData:
    """Tests for PageData model"""

    def test_default_values(self):
        """Should use default values"""
        page_data = PageData()
        assert page_data.items == []
        assert page_data.total == 0
        assert page_data.page == 1
        assert page_data.page_size == 10
        assert page_data.pages == 0

    def test_generic_type(self):
        """Should work with generic type"""
        page_data = PageData[int](
            items=[1, 2, 3],
            total=3,
            page=1,
            page_size=10,
        )
        assert page_data.items == [1, 2, 3]

    def test_pages_field_exists(self):
        """Should have pages field"""
        page_data = PageData()
        assert hasattr(page_data, 'pages')


class TestPaginatedResponse:
    """Tests for PaginatedResponse model"""

    def test_default_values(self):
        """Should use default values"""
        response = PaginatedResponse()
        assert response.code == ErrorCode.SUCCESS
        assert response.message == "success"
        assert response.data is None
        assert isinstance(response.timestamp, int)

    def test_with_page_data(self):
        """Should include page data"""
        page_data = PageData(
            items=[{"id": 1}, {"id": 2}],
            total=2,
            page=1,
            page_size=10,
        )
        response = PaginatedResponse(data=page_data)
        assert response.data.items == [{"id": 1}, {"id": 2}]
        assert response.data.total == 2


class TestSuccessFunction:
    """Tests for success function"""

    def test_default_success_response(self):
        """Should create default success response"""
        response = success()
        assert response.code == ErrorCode.SUCCESS
        assert response.message == "success"
        assert response.data is None

    def test_success_with_data(self):
        """Should create success response with data"""
        data = {"id": 1, "name": "Test"}
        response = success(data=data)
        assert response.code == ErrorCode.SUCCESS
        assert response.data == data

    def test_success_with_custom_message(self):
        """Should create success response with custom message"""
        response = success(message="操作成功")
        assert response.message == "操作成功"

    def test_success_with_custom_code(self):
        """Should create success response with custom code"""
        response = success(code=ErrorCode.CREATED)
        assert response.code == ErrorCode.CREATED

    def test_success_with_all_parameters(self):
        """Should create success response with all parameters"""
        data = {"id": 1}
        response = success(data=data, message="Created", code=ErrorCode.CREATED)
        assert response.code == ErrorCode.CREATED
        assert response.message == "Created"
        assert response.data == data


class TestErrorFunction:
    """Tests for error function"""

    def test_default_error_response(self):
        """Should create default error response"""
        response = error("Something went wrong")
        assert response.code == ErrorCode.INTERNAL_ERROR
        assert response.message == "Something went wrong"
        assert response.data is None

    def test_error_with_custom_code(self):
        """Should create error response with custom code"""
        response = error("Not found", code=ErrorCode.NOT_FOUND)
        assert response.code == ErrorCode.NOT_FOUND
        assert response.message == "Not found"

    def test_error_with_data(self):
        """Should create error response with additional data"""
        details = {"field": "email", "reason": "already exists"}
        response = error("Validation failed", code=ErrorCode.VALIDATION_FAILED, data=details)
        assert response.data == details

    def test_error_with_validation_code(self):
        """Should create validation error response"""
        response = error("Invalid input", code=ErrorCode.INVALID_PARAMS)
        assert response.code == ErrorCode.INVALID_PARAMS

    def test_error_with_auth_code(self):
        """Should create authentication error response"""
        response = error("Unauthorized", code=ErrorCode.UNAUTHORIZED)
        assert response.code == ErrorCode.UNAUTHORIZED


class TestPaginatedFunction:
    """Tests for paginated function"""

    def test_paginated_response(self):
        """Should create paginated response"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = paginated(items=items, total=3, page=1, page_size=10)
        assert response.code == ErrorCode.SUCCESS
        assert response.data.items == items
        assert response.data.total == 3
        assert response.data.page == 1
        assert response.data.page_size == 10
        assert response.data.pages == 1

    def test_paginated_calculates_pages(self):
        """Should calculate total pages"""
        items = list(range(10))
        response = paginated(items=items, total=25, page=1, page_size=10)
        assert response.data.pages == 3

    def test_paginated_custom_message(self):
        """Should create paginated response with custom message"""
        response = paginated(
            items=[1, 2],
            total=2,
            page=1,
            page_size=10,
            message="Users retrieved",
        )
        assert response.message == "Users retrieved"

    def test_paginated_empty_list(self):
        """Should handle empty list"""
        response = paginated(items=[], total=0, page=1, page_size=10)
        assert response.data.items == []
        assert response.data.total == 0
        assert response.data.pages == 0

    def test_paginated_large_total(self):
        """Should handle large totals"""
        items = list(range(10))
        response = paginated(items=items, total=1000, page=1, page_size=10)
        assert response.data.pages == 100

    def test_paginated_last_page(self):
        """Should handle last page correctly"""
        items = [1, 2, 3]
        response = paginated(items=items, total=23, page=3, page_size=10)
        assert response.data.pages == 3
        assert response.data.page == 3


class TestGetHttpStatus:
    """Tests for get_http_status function"""

    def test_success_status(self):
        """Should map success codes to HTTP 200"""
        assert get_http_status(ErrorCode.SUCCESS) == 200
        assert get_http_status(ErrorCode.CREATED) == 201
        assert get_http_status(ErrorCode.ACCEPTED) == 202
        assert get_http_status(ErrorCode.NO_CONTENT) == 204

    def test_client_error_status(self):
        """Should map client error codes"""
        assert get_http_status(ErrorCode.INVALID_PARAMS) == 400
        assert get_http_status(ErrorCode.UNAUTHORIZED) == 401
        assert get_http_status(ErrorCode.PERMISSION_DENIED) == 403
        assert get_http_status(ErrorCode.NOT_FOUND) == 404

    def test_server_error_status(self):
        """Should map server error codes"""
        assert get_http_status(ErrorCode.INTERNAL_ERROR) == 500
        assert get_http_status(ErrorCode.SERVICE_UNAVAILABLE) == 503
        assert get_http_status(ErrorCode.GATEWAY_TIMEOUT) == 504

    def test_unknown_code_defaults_to_200(self):
        """Should default to 200 for unknown codes"""
        # Unknown codes return 200 because that's the default in the dict.get()
        assert get_http_status(99999) == 200

    def test_validation_error_status(self):
        """Should return 200 for validation errors (not in map)"""
        # VALIDATION_FAILED is not in HTTP_STATUS_MAP, so it defaults to 200
        assert get_http_status(ErrorCode.VALIDATION_FAILED) == 200

    def test_http_status_map_completeness(self):
        """HTTP_STATUS_MAP should have entries for key error codes"""
        assert ErrorCode.SUCCESS in HTTP_STATUS_MAP
        assert ErrorCode.CREATED in HTTP_STATUS_MAP
        assert ErrorCode.UNAUTHORIZED in HTTP_STATUS_MAP
        assert ErrorCode.NOT_FOUND in HTTP_STATUS_MAP
        assert ErrorCode.INTERNAL_ERROR in HTTP_STATUS_MAP


class TestGetErrorMessage:
    """Tests for get_error_message function"""

    def test_success_messages(self):
        """Should return success messages"""
        assert get_error_message(ErrorCode.SUCCESS) == "操作成功"
        assert get_error_message(ErrorCode.CREATED) == "创建成功"
        assert get_error_message(ErrorCode.ACCEPTED) == "请求已接受"
        assert get_error_message(ErrorCode.NO_CONTENT) == "无数据"

    def test_parameter_error_messages(self):
        """Should return parameter error messages"""
        assert get_error_message(ErrorCode.INVALID_PARAMS) == "参数错误"
        assert get_error_message(ErrorCode.MISSING_PARAM) == "缺少必要参数"
        assert get_error_message(ErrorCode.INVALID_FORMAT) == "格式错误"
        assert get_error_message(ErrorCode.VALIDATION_FAILED) == "参数校验失败"

    def test_auth_error_messages(self):
        """Should return auth error messages"""
        assert get_error_message(ErrorCode.UNAUTHORIZED) == "未授权"
        assert get_error_message(ErrorCode.TOKEN_EXPIRED) == "Token 已过期"
        assert get_error_message(ErrorCode.TOKEN_INVALID) == "Token 无效"
        assert get_error_message(ErrorCode.PERMISSION_DENIED) == "权限不足"

    def test_not_found_messages(self):
        """Should return not found messages"""
        assert get_error_message(ErrorCode.NOT_FOUND) == "资源不存在"
        assert get_error_message(ErrorCode.USER_NOT_FOUND) == "用户不存在"
        assert get_error_message(ErrorCode.CONFIG_NOT_FOUND) == "配置不存在"

    def test_business_rule_messages(self):
        """Should return business rule messages"""
        assert get_error_message(ErrorCode.DUPLICATE_RESOURCE) == "资源已存在"
        assert get_error_message(ErrorCode.OPERATION_NOT_ALLOWED) == "操作不允许"
        assert get_error_message(ErrorCode.INVALID_STATE) == "状态无效"
        assert get_error_message(ErrorCode.QUOTA_EXCEEDED) == "超出配额"

    def test_external_service_messages(self):
        """Should return external service messages"""
        assert get_error_message(ErrorCode.EXTERNAL_SERVICE_ERROR) == "外部服务错误"
        assert get_error_message(ErrorCode.DATABASE_ERROR) == "数据库错误"
        assert get_error_message(ErrorCode.CACHE_ERROR) == "缓存错误"
        assert get_error_message(ErrorCode.SEATUNNEL_ERROR) == "SeaTunnel 服务错误"
        assert get_error_message(ErrorCode.OPENMETADATA_ERROR) == "元数据服务错误"
        assert get_error_message(ErrorCode.DOLPHINSCHEDULER_ERROR) == "DolphinScheduler 服务错误"
        assert get_error_message(ErrorCode.SUPERSET_ERROR) == "Superset 服务错误"
        assert get_error_message(ErrorCode.HOP_ERROR) == "Hop 服务错误"
        assert get_error_message(ErrorCode.CUBE_STUDIO_ERROR) == "Cube-Studio 服务错误"

    def test_system_error_messages(self):
        """Should return system error messages"""
        assert get_error_message(ErrorCode.INTERNAL_ERROR) == "内部服务错误"
        assert get_error_message(ErrorCode.SERVICE_UNAVAILABLE) == "服务不可用"
        assert get_error_message(ErrorCode.GATEWAY_TIMEOUT) == "网关超时"

    def test_unknown_code_defaults(self):
        """Should return default message for unknown codes"""
        assert get_error_message(99999) == "未知错误"

    def test_error_message_completeness(self):
        """ERROR_MESSAGES should have entries for all error codes"""
        error_codes = [
            ErrorCode.SUCCESS,
            ErrorCode.CREATED,
            ErrorCode.INVALID_PARAMS,
            ErrorCode.UNAUTHORIZED,
            ErrorCode.PERMISSION_DENIED,
            ErrorCode.NOT_FOUND,
            ErrorCode.DUPLICATE_RESOURCE,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            ErrorCode.INTERNAL_ERROR,
        ]
        for code in error_codes:
            assert code in ERROR_MESSAGES


class TestApiResponseIntegration:
    """Integration tests for API response utilities"""

    def test_create_user_success_response(self):
        """Should create a proper user creation success response"""
        user_data = {"id": 123, "name": "John Doe", "email": "john@example.com"}
        response = success(data=user_data, message="User created successfully", code=ErrorCode.CREATED)
        assert response.code == ErrorCode.CREATED
        assert response.data == user_data
        assert get_http_status(response.code) == 201

    def test_validation_error_response(self):
        """Should create a proper validation error response"""
        validation_errors = {"email": "Invalid email format", "age": "Must be positive"}
        response = error(
            message="Validation failed",
            code=ErrorCode.VALIDATION_FAILED,
            data=validation_errors,
        )
        assert response.code == ErrorCode.VALIDATION_FAILED
        assert response.data == validation_errors
        # VALIDATION_FAILED is not in HTTP_STATUS_MAP, so defaults to 200
        assert get_http_status(response.code) == 200

    def test_list_users_paginated_response(self):
        """Should create a proper paginated users list response"""
        users = [
            {"id": 1, "name": "User 1"},
            {"id": 2, "name": "User 2"},
            {"id": 3, "name": "User 3"},
        ]
        response = paginated(items=users, total=100, page=1, page_size=10, message="Users retrieved")
        assert response.code == ErrorCode.SUCCESS
        assert len(response.data.items) == 3
        assert response.data.total == 100
        assert response.data.pages == 10

    def test_not_found_error_response(self):
        """Should create a proper not found error response"""
        response = error("User not found", code=ErrorCode.USER_NOT_FOUND)
        assert response.code == ErrorCode.USER_NOT_FOUND
        assert get_error_message(response.code) == "用户不存在"
        # USER_NOT_FOUND is not in HTTP_STATUS_MAP, defaults to 200
        assert get_http_status(response.code) == 200
