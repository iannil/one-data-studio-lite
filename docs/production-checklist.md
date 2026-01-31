# 生产环境部署检查清单

> 部署日期: ___________
> 执行人: ___________
> 版本: ___________

## 前置条件

- [ ] 服务器满足最低配置要求（CPU: 4核+, RAM: 16GB+, 磁盘: 100GB+）
- [ ] Docker 和 Docker Compose 已安装
- [ ] 网络配置正确（端口、防火墙）
- [ ] DNS 解析已配置（如使用域名）

## 安全配置

### 密钥与凭据
- [ ] 所有默认密码已修改
- [ ] JWT_SECRET 已设置为强随机字符串（32+ 字符）
- [ ] SERVICE_SECRET 已设置
- [ ] INTERNAL_TOKEN 已设置
- [ ] 数据库密码已修改（非默认值）
- [ ] CONFIG_ENCRYPTION_KEY 已配置

### HTTPS/TLS
- [ ] SSL/TLS 证书已配置
- [ ] HTTPS 访问正常（无浏览器警告）
- [ ] HTTP 自动重定向到 HTTPS
- [ ] HSTS 头已启用

### Token 黑名单
- [ ] Redis 已部署并可访问
- [ ] REDIS_URL 已正确配置
- [ ] Token 撤销功能已测试

## 服务部署

### 基础设施
- [ ] MySQL 已部署并可访问
- [ ] etcd 已部署并可访问
- [ ] Redis 已部署并可访问

### 外部组件
- [ ] DataHub 已部署
- [ ] Superset 已部署
- [ ] DolphinScheduler 已部署
- [ ] SeaTunnel 已部署
- [ ] Apache Hop 已部署
- [ ] Cube-Studio 已部署

### 内部服务
- [ ] Portal 服务 (8010) - 健康检查通过
- [ ] NL2SQL 服务 (8011) - 健康检查通过
- [ ] AI Cleaning 服务 (8012) - 健康检查通过
- [ ] Metadata Sync 服务 (8013) - 健康检查通过
- [ ] Data API 服务 (8014) - 健康检查通过
- [ ] Sensitive Detect 服务 (8015) - 健康检查通过
- [ ] Audit Log 服务 (8016) - 健康检查通过

### 反向代理
- [ ] Nginx 已部署
- [ ] 80 端口可访问
- [ ] 443 端口可访问

## 功能验证

### 认证授权
- [ ] 用户登录功能正常
- [ ] Token 刷新功能正常
- [ ] Token 撤销功能正常（登出后 Token 失效）
- [ ] 权限控制正常（管理员/普通用户）
- [ ] 用户权限变更后 Token 失效

### API 功能
- [ ] 各子系统代理正常
- [ ] NL2SQL 查询正常
- [ ] 元数据同步正常
- [ ] 数据 API 访问正常
- [ ] 敏感数据检测正常

### 前端访问
- [ ] 前端页面可访问
- [ ] API 调用正常
- [ ] 静态资源加载正常

## 监控告警

- [ ] Loki 日志聚合正常
- [ ] Grafana 面板可访问
- [ ] Prometheus 指标采集正常
- [ ] 告警规则已配置
- [ ] 告警通知已配置（钉钉/企业微信/邮件）

## 备份恢复

- [ ] etcd 备份已配置
- [ ] 数据库备份已配置
- [ ] 备份脚本已加入 crontab
- [ ] 恢复流程已测试
- [ ] 备份文件存储正常

## 性能测试

- [ ] API 响应时间测试（P95 < 500ms）
- [ ] 并发压力测试（100+ 并发）
- [ ] 数据库性能测试
- [ ] Redis 连接池测试

## 文档

- [ ] 部署文档已更新
- [ ] 运维手册已更新
- [ ] 应急预案已准备
- [ ] 系统架构图已更新

## 验收签字

- [ ] 技术负责人: ___________ 日期: _______
- [ ] 运维负责人: ___________ 日期: _______
- [ ] 安全负责人: ___________ 日期: _______

---

## 附录

### 常用检查命令

```bash
# 检查所有容器状态
docker ps

# 检查服务健康状态
curl http://localhost:8010/health/all

# 检查安全配置
curl http://localhost:8010/security/check

# 检查 Redis 连接
docker exec ods-redis redis-cli ping

# 检查 etcd 连接
docker exec ods-etcd etcdctl endpoint health

# 检查数据库连接
docker exec ods-mysql mysqladmin ping -h localhost -u root -p
```

### 回滚步骤

如遇问题需要回滚：

1. 停止所有服务：`make stop`
2. 恢复数据库备份：`bash scripts/restore-database.sh`
3. 恢复配置：`cp -r backup/previous/* deploy/`
4. 重启服务：`make services-up`
