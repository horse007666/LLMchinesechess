#-*- coding=utf-8 -*-
import os,sys
import numpy as np
import cv2
import glob
import time
import subprocess
from flask import Flask, request, jsonify

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

from scipy.interpolate import interp1d

# class id to the text
text_dict={
    1: "+车",
    2: "+马",
    3: "+像",
    4: "+士",
    5: "+帅",
    6: "+炮",
    7: "+兵",
    8: "-车",
    9: "-马",
    10: "-像",
    11: "-士",
    12: "-帅",
    13: "-炮",
    14: "-兵",
}

# FEN dict
fen_dict={
    1: "R",
    2: "N",
    3: "B",
    4: "A",
    5: "K",
    6: "C",
    7: "P",
    8: "r",
    9: "n",
    10: "b",
    11: "a",
    12: "k",
    13: "c",
    14: "p",
}


#----------------------------------------------------------------------------------------------------------
# 传入图片时，将图片的长scale到1400, 同时保持高宽比不变
fix_imw = 1400

def get_scaled_img(image):
    h,w,c = image.shape
    if w!=fix_imw:
        imh = int( fix_imw*(h/w) )
        image = cv2.resize(image, ( fix_imw, imh ))
    return image
#----------------------------------------------------------------------------------------------------------


def match_chessboard( image ):
    h,w,c = image.shape
    # vars： 窗口右下的坐标，棋盘左上坐标，棋盘右下坐标
    vars = [
        [(738,480),(231,108),(512,422)],
        [(906,576),(282,117),(630,506)],
        [(1329,813),(413,141),(921,710)],
        [(1872,1119),(582,174),(1296,972)],
        [(2331,1377),(722,198),(1614,1194)]
    ]
    vars=np.array(vars)
    vars=vars.reshape((-1,6))

    # 创建4个插值函数，分别代表左上xy坐标，右下xy坐标
    results=[]
    for i in range(4):
        f = interp1d(  vars[:,0], vars[:,i+2] , kind='linear', fill_value='extrapolate'  )
        results.append( f(w).item() )

    return results




def detect_round_pieces(image_path):
    """
    给定一个棋盘图片，识别棋子的位置，返回board编码格式的棋子位置，同时识别矩形棋盘的范围
    """
    if isinstance(image_path,str):
        # 读取图像，转为 opencv numpy.ndarray
        image = cv2.imread(image_path)
        if image is None:
            print("无法读取图像，请检查路径。")
            return
    elif isinstance(image_path, np.ndarray):
        image=image_path

    image = get_scaled_img(image)
    image0=image.copy()
    x1,y1,x2,y2  = match_chessboard(image)
    ww_l, hh_l = (x2-x1)/8, (y2-y1)/9
    
    # 转换为灰度图像
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 进行高斯模糊以减少噪声
    blurred = cv2.GaussianBlur(gray, (3, 3), 2)

    # 使用 Hough 圆变换检测圆形
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1,
                               minDist=50, param1=50, param2=30, minRadius=22, maxRadius=28)

    board = [ [ ' ' for j in range(9) ] for i in range(10) ]
    if circles is not None:
        circles_v = np.round(circles[0, :]).astype("int")
        for idx,(x, y, r) in enumerate( circles_v ):
            cropped_img = image0[y - r:y + r, x - r:x + r]
            label_text = recognize_image(  cropped_img  )
            n1, n2 = (x-x1)/ww_l+0.5, (y-y1)/hh_l+0.5  
            n1, n2=int(n1),int(n2)
            if not ( 0<=n1<=8 and  0<=n2<=9 ):
                continue
            board[n2][n1]=label_text

    return board, x1,y1,x2,y2


def fen_to_board(fen):
    parts = fen.split(' ')
    board_str = parts[0]
    board = [[' ' for _ in range(9)] for _ in range(10)]
    row = 0
    col = 0
    for char in board_str:
        if char.isdigit():
            col += int(char)
        elif char == '/':
            row += 1
            col = 0
        else:
            board[row][col] = char
            col += 1
    return board

def board_to_fen(board):
    """
    给定棋盘局面，计算fen编码，用于送入到pikafish中计算下一步的最佳着法
    如果我这边是黑色老将，想办法变号
    """
    fen = ""
    for row in board:
        count = 0
        for piece in row:
            if piece == ' ':
                count += 1
            else:
                if count > 0:
                    fen += str(count)
                    count = 0
                fen += piece
        if count > 0:
            fen += str(count)
        fen += "/"
    fen = fen[:-1]  # 去掉最后一个斜杠

    # 判断我方老将是红色还是黑色
    is_me_red = True
    for i in range(10):
        for j in range(9):
            if board[i][j]=='K':
                if i<5:
                    is_me_red = False
    if not is_me_red:
        fen=fen.swapcase()

    fen += f" w - - 0 1"
    return fen

def apply_move(board, move):
    """
    给定棋盘局面和着法，计算按照着法走完以后的局面
    """
    from_square = move[:2]
    to_square = move[2:]
    from_row = 9 - int(from_square[1])
    from_col = ord(from_square[0]) - ord('a')
    to_row = 9 - int(to_square[1])
    to_col = ord(to_square[0]) - ord('a')

    piece = board[from_row][from_col]
    board[from_row][from_col] = ' '
    board[to_row][to_col] = piece

    return board




def process_image( imgname ):
    """
    使用FEN编码来表示棋盘的局面

    """
    if isinstance(imgname, bytes):
        # 将二进制数据转换为 NumPy 的 uint8 类型数组
        np_arr = np.frombuffer(imgname, np.uint8)
        # 解码为 OpenCV 图像
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    elif isinstance(imgname, str):
        img=cv2.imread(imgname)

    img=get_scaled_img(img)
    img_height, img_width, _ = img.shape

    board,X0,Y0,X1,Y1 = detect_round_pieces(img)
    return board, X0,Y0,X1,Y1, img_width, img_height


#==========================使用深度学习来识别棋子=======================================================================
# 定义 10 层卷积神经网络
class ChineseChessCNN(nn.Module):
    def __init__(self, num_classes=14):
        super(ChineseChessCNN, self).__init__()
        self.conv_layers = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU()
        )
        self.fc_layers = nn.Sequential(
            nn.Linear(256 * 3 * 3, 512),
            nn.ReLU(),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.conv_layers(x)
        x = x.view(-1, 256 * 3 * 3)
        x = self.fc_layers(x)
        return x


model, transform, device = None, None,None
def recognize_image(  src_img  ):
    if isinstance(src_img, str):
        image = cv2.imread( src_img , cv2.IMREAD_COLOR)
    else: 
        image = src_img

    global model, transform,device

    if model is None:
        model = ChineseChessCNN()
        model.load_state_dict(torch.load('chinese_chess_model.pth', map_location=device))
        model.eval()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        transform = transforms.Compose([
            transforms.Resize((54, 54)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    cv2_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # 将OpenCV的numpy数组转换为PIL图像
    pil_image = Image.fromarray(cv2_image)
    image = transform(pil_image).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(image)
        _, predicted_label = torch.max(output.data, 1)
    
    return fen_dict[predicted_label.item()+1]
#===============================================================================================================================




#-----------------------  保存棋盘中棋子的底图，用于棋子的识别  ---------------------------------------------------
def save_pieces_diku(image_path):
    if isinstance(image_path,str):
        # 读取图像，转为 opencv numpy.ndarray
        image = cv2.imread(image_path)
        if image is None:
            print("无法读取图像，请检查路径。")
            return
    elif isinstance(image_path, np.ndarray):
        image=image_path

    image = get_scaled_img(image)
    image0=image.copy()
    
    # 转换为灰度图像
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 进行高斯模糊以减少噪声
    blurred = cv2.GaussianBlur(gray, (3, 3), 2)

    # 使用 Hough 圆变换检测圆形
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1,
                               minDist=50, param1=50, param2=30, minRadius=22, maxRadius=28)

    piece_locations = []

    if circles is not None:
        circles_v = np.round(circles[0, :]).astype("int")
        for idx,(x, y, r) in enumerate( circles_v ):
            cropped_img = image0[y - r:y + r, x - r:x + r]
            cv2.imwrite( f"C:/Users/86188/source/repos/WindowsFormsApp1/results-images/crop-{idx}.jpg", cropped_img )


#----------------------- 使用pikafish计算如何走棋，输出结果---------------------------------------------------------
class PikafishEngine:
    def __init__(self, engine_path):   
        self.engine_path = engine_path 
        self.engine = None

    def _send_command(self, command):
        self.engine.stdin.write(f"{command}\n")
        self.engine.stdin.flush()

    def _wait_response(self, keyword, timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            line = self.engine.stdout.readline().strip()
            if keyword in line:
                return True
        return False

    def get_best_move(self, fen, depth=10):  ## 18 step
        self.engine = subprocess.Popen(
            self.engine_path,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=1
        )

        # 设置引擎参数
        self._send_command("uci")
        self._send_command("setoption name Threads value 8")
        self._send_command("setoption name Hash value 1024")
        self._send_command("go movetime 5000")  # 按时间搜索
        self._wait_response("uciok")

        self._send_command(f"position fen {fen}")
        self._send_command(f"go depth {depth}")
        if self._wait_response("bestmove"):
            for line in self.engine.stdout:
                line = line.strip()
                if line.startswith("bestmove"):
                    best_move = line.split()[1]
                    self.close()
                    return best_move
        self.close()
        return None

    def close(self):
        self._send_command("quit")
        self.engine.terminate()



engine=None
last_fen=None
def get_best_move( initial_fen ):
    """
    给定fen编码表示的棋盘局面，使用pikafish引擎计算最佳着法
    """
    global engine
    if engine is None:
        engine = PikafishEngine(r'C:\XQBase\Pikafish\pikafish-sse41-popcnt.exe')  # 修改为实际路径    
    # 获取最佳着法
    best_move = engine.get_best_move(initial_fen)
    return best_move

def bestmove2coords( best_move, X0, Y0, X1, Y1, img_width, img_height ):
    """
    提供 string 返回给C#程序代码
    给定最佳走法(例如 a0a9)，给定拟合的棋盘左上角坐标和右下坐标，计算给定走法的起点坐标和终点坐标

    会进行判断，如果局面已经计算过了，
    """
    if best_move is None:
        return "GameOver 0 0 0 0"
    if best_move=="no move":
        return "Game-State-Not-Changed 0 0 0 0"
    nx1, ny1, nx2, ny2 = ord(best_move[0])-ord('a'), ord(best_move[1])-ord('0'), ord(best_move[2])-ord('a'), ord(best_move[3])-ord('0')
    step_x, step_y = (X1-X0)/8.0, (Y1-Y0)/9.0
    startX, endX = X0+step_x*nx1, X0+step_x*nx2
    startY ,  endY = Y0+step_y*(9-ny1),Y0+step_y*(9-ny2)
    # 转换为相对坐标值
    startX, startY, endX, endY = startX/img_width, startY/img_height, endX/img_width, endY/img_height
    result = f"{best_move} {startX:.4f} {startY:.4f} {endX:.4f} {endY:.4f}"
    return result




last_board=None
last_board_after_move=None
last_output_XYXY=None

def run_prog( image_bytes ):
    """
    输入byte类型的图片数据， 输出需要返回给windows编码代码的string数据
    遇到以下情况返回： "No-Move X0 Y0 X1 Y1"
    1.棋盘盘面和上一次完全一模一样

    遇到以下情况返回： "Rival-Move 0 0 0 0"
    2.棋盘盘面和上次按最佳走法走完以后完全一模一样
    """
    global last_board,last_board_after_move,last_output_XYXY
    board, X0,Y0,X1,Y1, img_width, img_height  = process_image( image_bytes )
    initial_fen = board_to_fen(board)

    if board is None or 'k' not in initial_fen or 'K' not in initial_fen:
        last_board=None
        last_board_after_move=None
        last_output_XYXY=None
        return "None 0 0 0 0"

    if last_board is not None and initial_fen==last_board:
        return "No-Move "+last_output_XYXY
    if last_board_after_move is not None and initial_fen==last_board_after_move:
        return "Rival-Move 0 0 0 0" 

    # "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    best_move = get_best_move(initial_fen)
    final_res = bestmove2coords( best_move, X0, Y0, X1, Y1, img_width, img_height )

    last_board = board_to_fen(board)
    last_board_after_move = board_to_fen( apply_move(board, best_move) ) 
    last_output_XYXY  =  " ".join( final_res.split(" ")[1:]    )

    return final_res




def test():
    image_path = 'qipan_match/screenshot.jpg'
    with open(image_path, 'rb') as file:
        image_bytes = file.read()

    res1=run_prog( image_bytes )
    print(res1)
    res2=run_prog( image_bytes )
    print(res1)
    res3=run_prog( image_bytes )
    print(res1)
    res4=run_prog( image_bytes )
    print(res1)



app = Flask(__name__)

@app.route('/post', methods=['POST'])
def upload_image():
    try:
        # 获取请求中的二进制数据
        image_bytes = request.get_data()
        return run_prog( image_bytes )
    except Exception as e:
        return "error"




    



if __name__ == '__main__':
    app.run(debug=True, port=9527)
    #test()

    #for w in range(800,2500,100):
    #    image=np.ones((w,w,3),dtype=np.uint8)
    #    print( match_chessboard2(image) )




