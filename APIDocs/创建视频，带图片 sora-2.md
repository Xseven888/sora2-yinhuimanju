# 创建视频，带图片  sora-2

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/video/create:
    post:
      summary: 创建视频，带图片  sora-2
      deprecated: false
      description: ''
      tags:
        - 视频模型/sora 视频生成/统一视频格式
      parameters:
        - name: Content-Type
          in: header
          description: ''
          required: true
          example: application/json
          schema:
            type: string
        - name: Accept
          in: header
          description: ''
          required: true
          example: application/json
          schema:
            type: string
        - name: Authorization
          in: header
          description: ''
          required: false
          example: Bearer {{YOUR_API_KEY}}
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                images:
                  type: array
                  items:
                    type: string
                  description: 图片链接
                model:
                  type: string
                  description: 模型名字
                orientation:
                  type: string
                  description: |
                    portrait 竖屏
                    landscape 横屏
                prompt:
                  type: string
                  description: 提示词
                size:
                  type: string
                  description: ' small 一般720p'
                duration:
                  type: integer
                  description: '枚举值: 10'
                watermark:
                  type: string
                  description: |
                    默认为： true  会优先无水印，如果出错，会兜底到有水印
                    传递 false 的话 会强制让视频无水印，遇到去水印错误的会一直自动重试
              required:
                - images
                - model
                - orientation
                - prompt
                - size
                - duration
                - watermark
              x-apifox-orders:
                - images
                - model
                - orientation
                - prompt
                - size
                - duration
                - watermark
            example:
              images:
                - >-
                  https://filesystem.site/cdn/20250612/998IGmUiM2koBGZM3UnZeImbPBNIUL.png
              model: sora-2
              orientation: portrait
              prompt: make animate
              size: large
              duration: 15
              watermark: false
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                  status:
                    type: string
                  status_update_time:
                    type: integer
                required:
                  - id
                  - status
                  - status_update_time
                x-apifox-orders:
                  - id
                  - status
                  - status_update_time
              example:
                id: sora-2:task_01k6x15vhrff09dkkqjrzwhm60
                status: pending
                status_update_time: 1759763427208
          headers: {}
          x-apifox-name: 成功
      security:
        - bearer: []
      x-apifox-folder: 视频模型/sora 视频生成/统一视频格式
      x-apifox-status: released
      x-run-in-apifox: https://app.apifox.com/web/project/7262944/apis/api-363013860-run
components:
  schemas: {}
  securitySchemes:
    bearer:
      type: http
      scheme: bearer
servers:
  - url: https://api.sora2.email
    description: 正式环境
security:
  - bearer: []

```