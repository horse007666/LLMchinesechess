using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Point = System.Drawing.Point;

using Size = System.Drawing.Size;

namespace TianTianXiangQiScreenshotApp
{

    public partial class MainForm : Form
    {
        private PictureBox screenshotPictureBox;
        private Label textBox1;
        private static readonly int Interval = 1000; // 启动python脚本识别当前局面，并且计算最佳着法的时间间隔
        private static System.Timers.Timer screenshotTimer;
        private static Timer windowsFormsTimer;
        private static bool isProcessing = false; // 新增标志位
        float scale = 1.5F;

        static string remoteUrl = "http://127.0.0.1:9527/post";

        // 启动的实时截图程序，截图并且scale到固定宽度，然后实时显示
        private int fixwidth = 600;

        //设置虚线箭头的指向方向
        private double scaleX1, scaleX2, scaleY1, scaleY2;
        

        public MainForm()
        {
            InitializeUI();
            InitializeTimer();
            InitializeTimer2();
            this.FormClosing += MainForm_FormClosing;
        }

        private void InitializeUI()
        {
            int ww = 1042;
            int hh = 652;
            this.Text = "天天象棋截图显示";
            this.Size = new Size(ww, hh + 100);

            screenshotPictureBox = new PictureBox();
            screenshotPictureBox.Size = new Size(ww, hh); // 767,85
            screenshotPictureBox.Location = new Point(0, 0);
            screenshotPictureBox.Visible = true;
            screenshotPictureBox.SizeMode = PictureBoxSizeMode.Zoom;
            this.Controls.Add(screenshotPictureBox);


            textBox1 = new Label();
            textBox1.Size = new Size(ww, 100);
            textBox1.Text = "Welcome To Yang Ma Sheng's Software!!!";
            textBox1.Location = new Point(0, hh);
            textBox1.TextAlign = ContentAlignment.MiddleCenter;
            this.Controls.Add(textBox1);
        }

        private void InitializeTimer()
        {  // 运行python脚本
            screenshotTimer = new System.Timers.Timer();
            screenshotTimer.Interval = Interval; //ms
            screenshotTimer.Elapsed += ScreenshotTimer_Tick;
            screenshotTimer.Start();
        }

        private void InitializeTimer2()
        {  // 运行截图并且显示的脚本
            // 初始化 System.Windows.Forms.Timer
            windowsFormsTimer = new System.Windows.Forms.Timer();
            windowsFormsTimer.Interval = 100; // 1秒
            windowsFormsTimer.Tick += WindowsFormsTimer_Tick;
            windowsFormsTimer.Start();
        }

        [DllImport("user32.dll")]
        private static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

        [DllImport("user32.dll")]
        private static extern bool GetWindowRect(IntPtr hWnd, out Rectangle lpRect);

        private void ScreenshotTimer_Tick(object sender, EventArgs e)
        {
            CaptureAndDisplayScreenshot();
        }

        private void WindowsFormsTimer_Tick(object sender, EventArgs e){
            CaptureAndDisplayScreenshot2();
        }




        static byte[] ImageToByteArray(Image image)
        {
            using (MemoryStream ms = new MemoryStream())
            {
                image.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
                return ms.ToArray();
            }
        }
        private string GetPostResult(byte[] data)
        {
            // 将调用python脚本改为调用post接口
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(remoteUrl);
            request.Method = "POST";
            request.ContentType = "image/png";
            request.ContentLength = data.Length;

            using (Stream requestStream = request.GetRequestStream())
            {
                requestStream.Write(data, 0, data.Length);
            }

            string result = "";
            using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
            {
                if (response.StatusCode != HttpStatusCode.OK)
                {
                    throw new WebException($"请求失败，状态码: {response.StatusCode}");
                }
                using (Stream responseStream = response.GetResponseStream())
                using (StreamReader reader = new StreamReader(responseStream))
                {
                    result=reader.ReadToEnd();
                }
            }
            return result;
        }




        private void UpdateTextBox(string message)
        {
            if (textBox1.InvokeRequired)
            {
                textBox1.Invoke(new Action(() =>
                {
                    //textBox1.Text=message + Environment.NewLine;
                    textBox1.Text = message;
                }));
            }
            else
            {
                //textBox1.Text=message + Environment.NewLine;
                textBox1.Text = message;
            }
        }

        // 把包含四个由空格分隔的浮点数的字符串转换为四个double类型数字
        static double[] ConvertStringToFourDoubles(string input)
        {
            string[] parts = input.Split(' ');
            if (parts.Length != 5)
            {
                Console.WriteLine("输入的字符串未包含四个浮点数。");
                return null;
            }

            double[] result = new double[4];
            for (int i = 0; i < 4; i++)
            {
                if (!double.TryParse(parts[i+1], out result[i]))
                {
                    Console.WriteLine($"第 {i + 1} 个部分无法转换为整数。");
                    return null;
                }
            }
            return result;
        }



        public void CaptureAndDisplayScreenshot()
        {   if(isProcessing)
            {
                // 如果上一个事件还在处理，重新设置定时器间隔并启动，等待下次检查
                screenshotTimer.Interval = Interval;
                screenshotTimer.Start();
                return;
            }
            isProcessing = true;

            try
            {
                IntPtr windowHandle = FindWindow(null, "天天象棋");
                if (GetWindowRect(windowHandle, out Rectangle windowRect))
                {
                    // 调整 PictureBox 的大小
                    int width = (int)((windowRect.Width - windowRect.Left) * 1.5);
                    int height = (int)((windowRect.Height - windowRect.Top) * 1.5);

                    Bitmap screenshot = new Bitmap(width, height);
                    using (Graphics g = Graphics.FromImage(screenshot))
                    {
                        g.CopyFromScreen((int)(windowRect.Left * scale), (int)(windowRect.Top * scale), 0, 0, screenshot.Size);
                    }

                    UpdateTextBox("程序正在计算中");
                    
                    byte[] image_data = ImageToByteArray(screenshot);
                    string Python_result = GetPostResult(image_data);
                    Console.WriteLine($" 服务器计算结果: {Python_result}");

                    double[] coords = ConvertStringToFourDoubles(Python_result);
                    if (coords != null)
                    {
                        scaleX1 = coords[0];
                        scaleY1 = coords[1];
                        scaleX2 = coords[2];
                        scaleY2 = coords[3];
                        Console.WriteLine($" 最佳着法的起点和终点: {scaleX1} {scaleY1} {scaleX2} {scaleY2}");
                    }
                    else {
                        scaleX1 = scaleY1 = scaleX2 = scaleY2 = 0;
                    }
                    UpdateTextBox( "Best Move: "+Python_result.Split(' ')[0]  );
                    

                    screenshot.Dispose();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"运行代码时候发生错误: {ex.Message}");
            }
            finally 
            {
                isProcessing = false;
                screenshotTimer.Interval = Interval;
                screenshotTimer.Start();
            }
            
        }


        //=======================================================================================================================
        private void CaptureAndDisplayScreenshot2()
        {
            IntPtr windowHandle = FindWindow(null, "天天象棋");
            if (windowHandle == IntPtr.Zero)
            {
                if (screenshotPictureBox.Image != null)
                {
                    screenshotPictureBox.Image.Dispose();
                    screenshotPictureBox.Image = null;
                }
                return;
            }

            if (GetWindowRect(windowHandle, out Rectangle windowRect))
            {
                try
                {
                    // 调整 PictureBox 的大小
                    int width = (int)((windowRect.Width - windowRect.Left) * 1.5);
                    int height = (int)((windowRect.Height - windowRect.Top) * 1.5);
                    int newwidth = fixwidth;
                    int newheight = (int)height * newwidth / width;

                    Bitmap screenshot = new Bitmap(width,height);
                    Bitmap resizedImage = new Bitmap( newwidth, newheight );
                    using (Graphics g = Graphics.FromImage(screenshot))
                    {
                        g.CopyFromScreen((int)(windowRect.Left * scale), (int)(windowRect.Top * scale), 0, 0, screenshot.Size);
                    }
                    using (Graphics g = Graphics.FromImage(resizedImage))
                    {   // 将截图画在scale之后的图像中
                        g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                        g.DrawImage(screenshot, 0, 0, newwidth, newheight);


                        // 创建一个虚线画笔
                        Pen dashedPen = new Pen(Color.Black, 2);
                        dashedPen.DashStyle = System.Drawing.Drawing2D.DashStyle.Dash;

                        // 定义箭头的起始点和终点
                        Point startPoint = new Point( (int)(scaleX1*newwidth), (int)(scaleY1*newheight) );
                        Point endPoint = new Point( (int)(scaleX2*newwidth), (int)(scaleY2*newheight) );

                        // 绘制虚线直线
                        g.DrawLine(dashedPen, startPoint, endPoint);

                        // 绘制箭头头部
                        const int arrowSize = 10;
                        double angle = Math.Atan2(endPoint.Y - startPoint.Y, endPoint.X - startPoint.X);

                        Point[] arrowPoints = new Point[3];
                        arrowPoints[0] = endPoint;
                        arrowPoints[1] = new Point(
                            (int)(endPoint.X - arrowSize * Math.Cos(angle - Math.PI / 6)),
                            (int)(endPoint.Y - arrowSize * Math.Sin(angle - Math.PI / 6)));
                        arrowPoints[2] = new Point(
                            (int)(endPoint.X - arrowSize * Math.Cos(angle + Math.PI / 6)),
                            (int)(endPoint.Y - arrowSize * Math.Sin(angle + Math.PI / 6)));

                        g.FillPolygon(Brushes.Black, arrowPoints);

                    }

                    if (screenshotPictureBox.Image != null)
                    {
                        screenshotPictureBox.Image.Dispose();
                    }


                    // 图像预处理
                    screenshotPictureBox.Image = resizedImage;
                    screenshot.Dispose();

                    this.Width = newwidth;
                    this.Height = newheight + 100;
                    screenshotPictureBox.Width = newwidth;
                    screenshotPictureBox.Height = newheight;

                    textBox1.Width = newwidth;
                    textBox1.Height = 100;
                    textBox1.Location = new Point(0, newheight);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"截图时发生错误: {ex.Message}");
                }
            }
        }
        //=======================================================================================================================


        private void MainForm_FormClosing(object sender, FormClosingEventArgs e)
        {
            if (screenshotTimer != null && screenshotTimer.Enabled)
            {
                screenshotTimer.Stop();
            }
            if (screenshotPictureBox.Image != null)
            {
                screenshotPictureBox.Image.Dispose();
            }
        }

        private void InitializeComponent()
        {
            this.textBox1 = new Label();
            this.SuspendLayout();
            // 
            // textBox1
            // 
            this.textBox1.Location = new Point(120, 495);
            this.textBox1.Name = "textBox1";
            this.textBox1.Size = new System.Drawing.Size(100, 28);
            this.textBox1.TabIndex = 0;
            // 

            // 
            // MainForm
            // 
            this.ClientSize = new System.Drawing.Size(969, 535);
            this.Controls.Add(this.textBox1);
            this.Name = "MainForm";
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        //=======================================================================================================================




    }
}



