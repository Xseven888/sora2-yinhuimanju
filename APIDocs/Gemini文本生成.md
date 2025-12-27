# 文本生成

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1beta/models/gemini-2.5-pro:generateContent:
    post:
      summary: 文本生成
      deprecated: false
      description: >-
        官方文档：https://ai.google.dev/gemini-api/docs/text-generation?hl=zh-cn#multi-turn-conversations
      tags:
        - 聊天(Chat)/谷歌Gemini 接口/原生格式
      parameters:
        - name: key
          in: query
          description: ''
          required: true
          example: '{{YOUR_API_KEY}}'
          schema:
            type: string
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
                contents:
                  type: array
                  items:
                    type: object
                    properties:
                      parts:
                        type: array
                        items:
                          type: object
                          properties:
                            text:
                              type: string
                          x-apifox-orders:
                            - text
                    x-apifox-orders:
                      - parts
              required:
                - contents
              x-apifox-orders:
                - contents
            example:
              systemInstruction:
                parts:
                  - text: 你是一直小猪.你会在回复开始的时候 加一个'哼哼'
              contents:
                - role: user
                  parts:
                    - text: 你是谁?
              generationConfig:
                temperature: 1
                topP: 1
                thinkingConfig:
                  includeThoughts: true
                  thinkingBudget: 26240
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
                x-apifox-orders: []
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: 聊天(Chat)/谷歌Gemini 接口/原生格式
      x-apifox-status: released
      x-run-in-apifox: https://app.apifox.com/web/project/7262944/apis/api-363013763-run
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