import json

from fastapi import FastAPI, Request
import os
import requests
from pydantic_settings import BaseSettings
import pathlib


class Settings(BaseSettings):
    BOT_TOKEN: str = ''
    CUSTOM_DOMAIN: str = ''
    VERCEL_URL: str = ''
    BOT_DOMAIN: str = "api.telegram.org"
    TG_BOT_API: str = f"https://{BOT_DOMAIN}/bot"
    secret_token: str = 'alfchao'
    # .env


def json_print(obj):
    return json.dumps(obj, indent=4, ensure_ascii=False)


settings = Settings(_env_file=pathlib.Path(__file__).parent.parent / '.env')

print(settings.BOT_TOKEN)


def set_webhook():
    telegram_webhook = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/setWebhook"
    body = {
        "url": f"https://{settings.CUSTOM_DOMAIN or settings.VERCEL_URL}/",
        "secret_token": settings.secret_token
    }
    rsp = requests.post(telegram_webhook.format(os.environ.get("TELEGRAM_BOT_TOKEN")), json=body)
    print(json_print(rsp.json()))
    get_webhook()


def get_webhook():
    telegram_webhook = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/getWebhookInfo"
    rsp = requests.get(telegram_webhook)
    print(json_print(rsp.json()))


def create_app():
    set_webhook()
    app = FastAPI()

    @app.post("/")
    async def telegram_webhook(request: Request):
        # 打印请求头
        print("Headers:", json_print(dict(request.headers)))

        # 打印请求体（原始字节）
        request_body = await request.json()
        print("Raw body:", json_print(request_body))

        body = {
            "headers": dict(request.headers),
            "body": request_body
        }

        telegram_sendmsg = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/sendMessage"

        send_body = {
            "chat_id": f"{request_body.get('message').get('chat').get('id')}",
            "text": f"```json\n{json_print(body)}\n```",
            "parse_mode": "MarkdownV2",
            "reply_parameters": {
                "message_id": request_body.get('message').get('message_id'),
            }
        }

        rsp = requests.post(telegram_sendmsg, json=send_body)
        print(json_print(rsp.json()))

        # 如果收到一个文件，则再发送一个文件链接回去
        if request_body.get('message').get('document'):
            # 获取文件路径 getFile
            telegram_getfile = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/getFile"
            send_body = {
                "file_id": request_body.get('message').get('document').get('file_id')
            }
            rsp = requests.post(telegram_getfile, json=send_body)
            print(json_print(rsp.json()))
            file_path = rsp.json().get('result').get('file_path')

            send_body = {
                "chat_id": f"{request_body.get('message').get('chat').get('id')}",
                "text": f"`https://{settings.BOT_DOMAIN}/file/bot{settings.BOT_TOKEN}/{file_path}`",
                "parse_mode": "MarkdownV2",
                "reply_parameters": {
                    "message_id": request_body.get('message').get('message_id'),
                }
            }
            rsp = requests.post(telegram_sendmsg, json=send_body)
            # 保存这个文件
            # with open(f"{request_body.get('message').get('document').get('file_name')}", "wb") as f:
            #     f.write(requests.get(f"{settings.TG_BOT_API}file/bot{settings.BOT_TOKEN}/{file_path}").content)
            print(json_print(rsp.json()))

        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
