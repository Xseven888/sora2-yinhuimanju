# 创建视频 （带 Character）

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
      summary: 创建视频 （带 Character）
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
                model:
                  type: string
                orientation:
                  type: string
                  enum:
                    - portrait
                    - landscape
                  x-apifox-enum:
                    - value: portrait
                      name: ''
                      description: 竖屏
                    - value: landscape
                      name: ''
                      description: 横屏
                prompt:
                  type: string
                duration:
                  type: integer
                  description: 时长
                  enum:
                    - 10
                    - 15
                    - 25
                  x-apifox-enum:
                    - value: 10
                      name: ''
                      description: sora-2,sora-2-pro 可用
                    - value: 15
                      name: ''
                      description: sora-2,sora-2-pro 可用
                    - value: 25
                      name: ''
                      description: sora-2-pro可用
                character_url:
                  type: string
                  description: 创建角色需要的视频链接，注意视频中一定不能出现真人，否则会失败
                character_timestamps:
                  type: string
                  description: 视频角色出现的秒数范围，格式 `{start},{end}`, 注意 end-start 的范围 1-3秒
                size:
                  type: string
                  enum:
                    - large
                    - small
                  x-apifox-enum:
                    - value: large
                      name: 高清
                      description: ''
                    - value: small
                      name: 一般
                      description: ''
              required:
                - model
                - prompt
                - size
              x-apifox-orders:
                - images
                - model
                - orientation
                - prompt
                - duration
                - character_url
                - character_timestamps
                - size
            example:
              images: []
              model: sora-2
              orientation: portrait
              prompt: make animate
              duration: 15
              character_url: >-
                https://filesystem.site/cdn/20251030/javYrU4etHVFDqg8by7mViTWHlMOZy.mp4
              character_timestamps: 1,3
              size: large
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
                x-apifox-orders: []
              example:
                id: sora-2:task_01k900ag82ecgbewj2xa3758z0
                status: pending
                status_update_time: 1762010677921
          headers: {}
          x-apifox-name: 成功
      security:
        - bearer: []
      x-apifox-folder: 视频模型/sora 视频生成/统一视频格式
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/7262944/apis/api-385698788-run
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