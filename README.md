# EPG 电子节目单生成工具

## 项目简介

EPG（Electronic Program Guide）电子节目单生成工具，用于从多个数据源抓取电视节目单，并生成统一格式的XMLTV文件，供各种IPTV播放器使用。

## 功能特性

- 支持从多个数据源抓取节目单
- 自动合并和去重节目数据
- 支持频道名称标准化和映射
- 生成标准XMLTV格式输出
- 支持配置文件自定义
- 支持GZIP压缩输出
- 支持日志记录
- 支持模糊匹配频道
- 支持成功率阈值配置

## 支持的数据源

央视节目单
卫视频道节目单
部分地方台节目单

## 环境变量配置

项目需要以下环境变量（在GitHub Actions中设置为Secrets）：
- `CCTV_API_URL`
- `CCTV_GENERATOR_URL`
- `TM_CCTV`
- `TM_SATELLITE`
- `B_PROGRAM`
- `B_WS`

## 部署说明

1. 克隆仓库到本地
2. 安装依赖：`pip install -r requirements.txt`
3. 在GitHub仓库中设置Secrets
4. 启用GitHub Actions工作流
5. 工作流会自动定时运行，生成并更新EPG数据

## 扫码支持

如果您觉得这个项目对您有帮助，欢迎扫码支持：

<img src="appreciate.png" width="200" alt="扫码支持"/>

## 许可证

本项目采用MIT许可证，详情请查看LICENSE文件。
