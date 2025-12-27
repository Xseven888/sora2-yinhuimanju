# 创建角色

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /sora/v1/characters:
    post:
      summary: 创建角色
      deprecated: false
      description: ''
      tags:
        - 视频模型/sora 视频生成
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                url:
                  type: string
                  description: |
                    视频中包含需要创建的角色
                timestamps:
                  type: string
                  description: |
                    单位秒，例如 ‘1,2’ 是指视频的1～2秒中出现的角色，注意范围差值最大 3 秒最小 1 秒
              required:
                - url
                - timestamps
              x-apifox-orders:
                - url
                - timestamps
            example:
              url: >-
                https://filesystem.site/cdn/20251030/javYrU4etHVFDqg8by7mViTWHlMOZy.mp4
              timestamps: 1,3
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
                    description: 角色id
                  username:
                    type: string
                    description: 角色名称，用于放在提示词中 @{username}
                  permalink:
                    type: string
                    description: 角色主页，跳转到 openai 角色主页
                  profile_picture_url:
                    type: string
                    description: 角色头像
                required:
                  - id
                  - username
                  - permalink
                  - profile_picture_url
                x-apifox-orders:
                  - id
                  - username
                  - permalink
                  - profile_picture_url
              example:
                id: ch_6918d62178e48191a0b1ae49be428a13
                username: hfspncadz.mooflapand
                permalink: https://sora.chatgpt.com/profile/hfspncadz.mooflapand
                profile_picture_url: >-
                  https://videos.openai.com/az/files/00000000-b788-71f7-9de5-96555ff29024%2Fraw?se=2025-11-20T00%3A00%3A00Z&sp=r&sv=2024-08-04&sr=b&skoid=1af02b11-169c-463d-b441-d2ccfc9f02c8&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-11-15T01%3A48%3A34Z&ske=2025-11-22T01%3A53%3A34Z&sks=b&skv=2024-08-04&sig=3/KGVtkEsZWBTmErhzUEU5pWrnL8JxRKH0wVCQvh6Fo%3D&ac=oaisdmntprsouthcentralus
          headers: {}
          x-apifox-name: 成功
      security:
        - bearer: []
      x-apifox-folder: 视频模型/sora 视频生成
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/7262944/apis/api-377851077-run
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