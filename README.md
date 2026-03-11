# 借助大模型AI Coding实现象棋AI辅助

点击查看哔哩哔哩视频：
[![视频封面图](http://i2.hdslb.com/bfs/archive/6fc7d45035a5849d77ddde9f4c6bdc9f5c8c219d.jpg)](https://www.bilibili.com/video/BV11dMjztERU/?share_source=copy_web&vd_source=6a0d095ae268c7e99cd330b4b78e80c6)


### 象棋AI代码关键步骤

1.读取“天天象棋”窗口截屏内容，读取为图片类型，在另外一个窗口显示，送入程序的下一步。

2.视觉算法检测并且识别出棋子，确定出当前棋局的局面（检测+分类）
    2.1 先截图将一个个其中crop出来，保存为小图
    2.2 构建一个卷积神经网络，用于分类，能够识别棋子的小图
    2.3 确定棋盘位置，给定棋盘，检测并且识别所有棋子，把每个棋子及其位置确定出来
    2.4 将棋盘盘面（所有棋子及其位置）用FEN编码成为string字符串

3.将当前局面送给AI运算，得到当前局面下的最佳着法。

4.可视化当前局面的最佳着法，方便使用者使用。

5.进一步优化代码，只在局面变化时才计算当前着法并可视化显示。



### 安装、编译、运行流程

#### 1.clone 代码
```
git clone https://github.com/horse007666/LLMchinesechess.git
```
打开windows Visual Studio 2019 或者其他版本的Visual Studio。用Visual Studio打开Clone的代码的sln文件

#### 2.运行flask后端服务
打开windows CMD，进入到clone下来的代码目录，运行后端程序run.py, 最好使用3.7以上的python版本
```
python run.py
```
#### 3.运行天天象棋小程序
可以在windows上安装微信，打开微信打开小程序，运行天天象棋，进入到AI对战界面，点击开始对战

#### 4.编译运行代码
切换到第一步的Visual Studio界面，点击编译并且运行，将天天象棋小程序的界面和本程序的窗口界面分开显示。后面就可以愉快的接受大模型的指导了

显示结果如下：
<img src=".\src\运行截图.png">




### 致谢
谢谢豆包、谢谢皮卡鱼、谢谢大模型深度学习技术



