# 查询任务 

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/video/query:
    get:
      summary: '查询任务 '
      deprecated: false
      description: |+
        给定一个提示，该模型将返回一个或多个预测的完成，并且还可以返回每个位置的替代标记的概率。

        为提供的提示和参数创建完成

      tags:
        - 视频模型/sora 视频生成/统一视频格式
      parameters:
        - name: id
          in: query
          description: |
            任务ID
          required: true
          example: sora-2:task_01k74ynm13exf9ha36zz7820hv
          schema:
            type: string
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
        - name: X-Forwarded-Host
          in: header
          description: ''
          required: false
          example: localhost:5173
          schema:
            type: string
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties: {}
            examples: {}
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
                  video_url:
                    type: 'null'
                  enhanced_prompt:
                    type: string
                  status_update_time:
                    type: integer
                required:
                  - id
                  - status
                  - video_url
                  - enhanced_prompt
                  - status_update_time
                x-apifox-orders:
                  - id
                  - status
                  - video_url
                  - enhanced_prompt
                  - status_update_time
              examples:
                '1':
                  summary: pending
                  value:
                    id: sora-2:task_01k6x15vhrff09dkkqjrzwhm60
                    detail:
                      id: task_01k6x15vhrff09dkkqjrzwhm60
                      input:
                        size: small
                        model: sy_ore
                        images:
                          - >-
                            https://filesystem.site/cdn/20250612/VfgB5ubjInVt8sG6rzMppxnu7gEfde.png
                          - >-
                            https://filesystem.site/cdn/20250612/998IGmUiM2koBGZM3UnZeImbPBNIUL.png
                        prompt: make animate
                        orientation: portrait
                      status: pending
                      pending_info:
                        id: task_01k6x15vhrff09dkkqjrzwhm60
                        seed: null
                        type: video_gen
                        user: user-a1sGDUIOXV32hNITe59LEkHa
                        model: sy_8
                        title: New Video
                        width: 352
                        height: 640
                        prompt: make animate
                        sdedit: null
                        status: processing
                        actions: null
                        guidance: null
                        n_frames: 450
                        priority: 2
                        operation: simple_compose
                        preset_id: null
                        created_at: '2025-10-06T15:10:26.875729Z'
                        n_variants: 1
                        project_id: null
                        request_id: null
                        generations: []
                        tracking_id: null
                        progress_pct: 0.9302178175176704
                        remix_config: null
                        inpaint_items:
                          - type: image
                            preset_id: null
                            crop_bounds: null
                            frame_index: 0
                            cameo_file_id: null
                            generation_id: null
                            upload_media_id: media_01k6x15tnzezbst05sth2qgd8r
                            source_end_frame: 0
                            uploaded_file_id: null
                            source_start_frame: 0
                          - type: image
                            preset_id: null
                            crop_bounds: null
                            frame_index: 0
                            cameo_file_id: null
                            generation_id: null
                            upload_media_id: media_01k6x15tzafwztz74t018v3enw
                            source_end_frame: 0
                            uploaded_file_id: null
                            source_start_frame: 0
                        interpolation: null
                        is_storyboard: null
                        failure_reason: null
                        organization_id: null
                        moderation_result:
                          code: null
                          type: passed
                          task_id: task_01k6x15vhrff09dkkqjrzwhm60
                          is_output_rejection: false
                          results_by_frame_index: {}
                        needs_user_review: false
                        queue_status_message: null
                        progress_pos_in_queue: null
                        num_unsafe_generations: 0
                        estimated_queue_wait_time: null
                    status: pending
                    status_update_time: 1759763621142
                '2':
                  summary: completed
                  value:
                    id: sora-2:task_01k6x15vhrff09dkkqjrzwhm60
                    width: 352
                    detail:
                      id: task_01k6x15vhrff09dkkqjrzwhm60
                      url: >-
                        https://filesystem.site/gptimage/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fsrc.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=log0LI%2Bwadi1bnm9MOw4UAptQC9Bi%2F8fPcpSVeRBq7I%3D&az=oaivgprodscus
                      input:
                        size: small
                        model: sy_ore
                        images:
                          - >-
                            https://filesystem.site/cdn/20250612/VfgB5ubjInVt8sG6rzMppxnu7gEfde.png
                          - >-
                            https://filesystem.site/cdn/20250612/998IGmUiM2koBGZM3UnZeImbPBNIUL.png
                        prompt: make animate
                        orientation: portrait
                      status: completed
                      gif_url: >-
                        https://filesystem.site/gptimage/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fpreview.gif?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=EoeGtZEdRHRRF6Y6KghYOngvj9NaocLD5Jh23OAeZXc%3D&az=oaivgprodscus
                      draft_info:
                        id: gen_01k6x1bffaf3dr786harh8maqt
                        url: >-
                          https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fsrc.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=log0LI%2Bwadi1bnm9MOw4UAptQC9Bi%2F8fPcpSVeRBq7I%3D&az=oaivgprodscus
                        kind: sora_draft
                        tags: []
                        title: null
                        width: 352
                        height: 640
                        prompt: make animate
                        task_id: task_01k6x15vhrff09dkkqjrzwhm60
                        encodings:
                          md:
                            path: >-
                              https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fmd.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=sk0XqtY55jqLECnAx9L9O%2BP4fpFmKisIGwQ2rFGJVLU%3D&az=oaivgprodscus
                          gif:
                            path: >-
                              https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fpreview.gif?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=EoeGtZEdRHRRF6Y6KghYOngvj9NaocLD5Jh23OAeZXc%3D&az=oaivgprodscus
                          source:
                            path: >-
                              https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fsrc.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=log0LI%2Bwadi1bnm9MOw4UAptQC9Bi%2F8fPcpSVeRBq7I%3D&az=oaivgprodscus
                          unfurl: null
                          source_wm:
                            path: >-
                              https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fsrc.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=log0LI%2Bwadi1bnm9MOw4UAptQC9Bi%2F8fPcpSVeRBq7I%3D&az=oaivgprodscus
                          thumbnail:
                            path: >-
                              https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fthumbnail.webp?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=ovYpytJMOZjyqD4vIf%2B66V5YqGGopu7AQM9n5ef421I%3D&az=oaivgprodscus
                        created_at: 1759763631.222531
                        generation_id: gen_01k6x1bffaf3dr786harh8maqt
                        draft_reviewed: false
                        creation_config:
                          prompt: make animate
                          task_id: null
                          n_frames: null
                          style_id: null
                          orientation: null
                          inpaint_image: null
                          cameo_profiles: null
                          remix_target_post: null
                        generation_type: ''
                        downloadable_url: >-
                          https://videos.openai.com/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fsrc.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=log0LI%2Bwadi1bnm9MOw4UAptQC9Bi%2F8fPcpSVeRBq7I%3D&az=oaivgprodscus
                      thumbnail_url: >-
                        https://filesystem.site/gptimage/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fthumbnail.webp?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=ovYpytJMOZjyqD4vIf%2B66V5YqGGopu7AQM9n5ef421I%3D&az=oaivgprodscus
                    height: 640
                    status: completed
                    video_url: >-
                      https://filesystem.site/gptimage/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fsrc.mp4?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=log0LI%2Bwadi1bnm9MOw4UAptQC9Bi%2F8fPcpSVeRBq7I%3D&az=oaivgprodscus
                    thumbnail_url: >-
                      https://filesystem.site/gptimage/vg-assets/assets%2Ftask_01k6x15vhrff09dkkqjrzwhm60%2Ftask_01k6x15vhrff09dkkqjrzwhm60_genid_6d46f487-b05f-4854-9c0f-4f2169caab0d_25_10_06_15_13_166244%2Fvideos%2F00000_wm%2Fthumbnail.webp?st=2025-10-06T14%3A04%3A21Z&se=2025-10-12T15%3A04%3A21Z&sks=b&skt=2025-10-06T14%3A04%3A21Z&ske=2025-10-12T15%3A04%3A21Z&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skoid=8ebb0df1-a278-4e2e-9c20-f2d373479b3a&skv=2019-02-02&sv=2018-11-09&sr=b&sp=r&spr=https%2Chttp&sig=ovYpytJMOZjyqD4vIf%2B66V5YqGGopu7AQM9n5ef421I%3D&az=oaivgprodscus
                    status_update_time: 1759763651908
          headers: {}
          x-apifox-name: 成功
      security:
        - bearer: []
      x-apifox-folder: 视频模型/sora 视频生成/统一视频格式
      x-apifox-status: released
      x-run-in-apifox: https://app.apifox.com/web/project/7262944/apis/api-385698787-run
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