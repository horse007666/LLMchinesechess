import requests

# 要上传的图片文件路径，需替换为实际的图片路径
image_path = 'qipan_match/screenshot.jpg'

# 读取图片文件为二进制数据
try:
    with open(image_path, 'rb') as file:
        image_bytes = file.read()
except FileNotFoundError:
    print(f"错误：未找到文件 {image_path}")
else:
    # 定义请求的 URL
    url = 'http://127.0.0.1:9527/post'

    # 发送 POST 请求
    response = requests.post(url, data=image_bytes)
    print(response)

    # 检查响应状态
    if response.status_code == 200:
        print(f"请求成功，状态码：{response.status_code}，响应内容：{response.text}")
    else:
        print(f"请求失败，状态码：{response.status_code}，响应内容：{response.text}")
    