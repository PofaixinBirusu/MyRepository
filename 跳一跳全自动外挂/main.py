import os,re,json,time,subprocess,random
from PIL import Image


def getConfig():
    # 获取屏幕分辨率
    size_str = os.popen('adb shell wm size').read()
    print(size_str)
    res = re.compile(r'(\d+)x(\d+)').findall(size_str)
    screen_size = "%sx%s" % (res[0][1], res[0][0])
    config_path = 'config/%s/config.json' % screen_size
    print(config_path)
    if not os.path.exists(config_path):
        config_path = 'config/default.json'
    with open(config_path, 'r') as f:
        print("config file:", config_path)
        return json.load(f)

def getImage():#获取手机截图
    process = subprocess.Popen('adb shell screencap -p', shell=True, stdout=subprocess.PIPE)
    screenshot = process.stdout.read()
    binary_screenshot = screenshot.replace(b'\r\r\n', b'\n')
    with open('autojump.png', 'wb') as f:
        f.write(binary_screenshot)


def getPoint(img, con):
    w, h = img.size
    # 棋子的底边界
    piece_y_max = 0
    scan_x_side = int(w / 8)  # 扫描棋子的左右边界减少开销
    scan_start_y = 0  # 扫描起始y坐标
    img_pixel = img.load() #像素矩阵
    for i in range(h // 3, h * 2 // 3, 50):
        first_pixel = img_pixel[0, i]
        for j in range(1, w):
            # 如果不是纯色，说明碰到了新的棋盘，跳出
            pixel = img_pixel[j, i]
            if abs(pixel[0] - first_pixel[0]) + abs(pixel[1] - first_pixel[1]) + abs(pixel[2] - first_pixel[2]) > 10:
                scan_start_y = i - 50
                break
        if scan_start_y:
            break
    # 已找到感兴趣区域，开始精确扫描
    left, right = 0, 0
    for i in range(scan_start_y, h * 2 // 3):
        flag = True
        for j in range(scan_x_side, w - scan_x_side):
            pixel = img_pixel[j, i]
            # 根据棋子的最低行的颜色判断，找最后一行那些点的平均值
            if (50 < pixel[0] < 60) and (53 < pixel[1] < 63) and (95 < pixel[2] < 110):
                if flag:
                    left, flag = j, False
                right, piece_y_max = j, i
    piece_x = (left + right) // 2
    piece_y = piece_y_max - con['piece_base_height_1_2']  # 上调高度，根据分辨率自行 调节

    # 缩小搜索范围
    if piece_x < w / 2:  # 棋子在左边，那目标盒子就在右边
        board_x_start = piece_x + con["piece_body_width"] // 2
        board_x_end = w
    else:                # 棋子在右边，那目标盒子一定在左边
        board_x_start = 0
        board_x_end = piece_x - con["piece_body_width"] // 2

    # 精确扫描
    left, right, num = 0, 0, 0
    for i in range(h // 3, h * 2 // 3):
        flag = True
        first_pixel = img_pixel[0, i]
        for j in range(board_x_start, board_x_end):
            pixel = img_pixel[j, i]
            #找到第一个不同色的，也就是最高点
            if abs(pixel[0] - first_pixel[0]) + abs(pixel[1] - first_pixel[1]) + abs(pixel[2] - first_pixel[2]) > 10:
                if flag:
                    left, flag = j, False
                right, num = j, num + 1
                # print(left, right)
        if not flag:break
    board_x = (left + right) // 2
    top_point = img_pixel[board_x, i+1] #最高点的像素

    #用最高点的y增加一个估计值，然后从下往上找   274这个值有待调节
    for k in range(i + 274, i, -1):
        pixel = img_pixel[board_x, k]
        # print(pixel)
        if abs(pixel[0]-top_point[0])+abs(pixel[1]-top_point[1])+abs(pixel[2]-top_point[2]) < 10:
            break
    board_y = (i + k) // 2
    if num < 5 and k - i <30:
        # 去除有些颜色比较多的误差
        print('杂色')
        board_y += (k - i)
        if piece_x < w / 2:#棋子在左边
            board_x -= (k - i)
        else:
            board_x += (k - i)
    # 药瓶是特殊的
    if top_point[:-1] == (255, 255, 255):
        print('药瓶')
        board_y = (i + board_y) // 2

    return piece_x, piece_y, board_x, board_y


def jump(distance, point, ratio):
    press_time = distance * ratio
    press_time = int(max(press_time, 200))  # 最小按压时间
    cmd = 'adb shell input swipe %d %d %d %d %d' % (point[0],point[1],point[0],point[1],press_time)
    print(cmd)
    os.system(cmd)
    return press_time

if __name__ == '__main__':
    config = getConfig()
    while True:
        getImage()
        img = Image.open('autojump.png')
        piece_x, piece_y, board_x, board_y = getPoint(img, config)
        print(piece_x, piece_y, '------->', board_x, board_y)
        distance = ((board_x - piece_x) ** 2 + (board_y - piece_y) ** 2) ** 0.5
        # 生成一个随机按压点，防止被微信发现
        press_point = (random.randint(100,500),random.randint(100,500))
        jump(distance, press_point, config['press_ratio'])
        time.sleep(random.randrange(1, 2))