from version import __version__ as APP_VERSION

# 项目名称
PROJECT_NAME = "我的项目"

# 域名
API_HOST = "api.sora2.email"
API_BASE_URL = "https://api.sora2.email"
# 微信号
WECHAT_ID = "Xseven888"
# gitee仓库地址
GITEE_REPO_URL = "https://gitee.com/seven798/yh-comic-drama"
# gitee仓库最新release api    只需要修改shuke/sora2    这个在仓库地址里面直接复制替换就行
GITEE_LATEST_RELEASE_API = "https://gitee.com/api/v5/repos/seven798/yh-comic-drama/releases/latest"

API_CHAT_COMPLETIONS_URL = f"{API_BASE_URL.rstrip('/')}/v1/chat/completions"
FILES_ENDPOINT = f"{API_BASE_URL.rstrip('/')}/v1/files"
DISPLAY_API_PROXY_URL = API_BASE_URL
GITEE_RELEASES_URL = f"{GITEE_REPO_URL}/releases"

