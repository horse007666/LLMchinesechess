2560*1440的屏幕
(0,0)-->(2559,1439)




def match_chessboard0(image_path, template_path):
    # 读取图片和模板
    if isinstance( image_path, str ):
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        image = get_scaled_img(image)
    else:
        image = image_path
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)

    # 获取模板的高度和宽度
    h, w = template.shape[:2]

    # 使用模板匹配方法
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 找到匹配位置
    top_left = max_loc
    # 在图片上绘制矩形框
    cv2.rectangle(image, (top_left[0],top_left[1]), (top_left[0]+w,top_left[1]+h), (0, 255, 0), 2)
    cv2.imwrite( f"matched-image/{int(time.time())}.jpg", image  )
    return top_left[0],top_left[1],top_left[0]+w,top_left[1]+h



#-----------------------------------------------------------------------------------------------------------
tmp_images, labels = [], []
def recognize_image(  src_img, idx  ):
    if isinstance(src_img, str):
        big_image = cv2.imread( src_img , cv2.IMREAD_COLOR)
    else: 
        big_image = src_img

    # 读取包含32个象棋棋子的图片
    global tmp_images, labels
    if len(tmp_images)==0:
        for idx in range(1,15):
            dir_name = f"C:/Users/86188/source/repos/WindowsFormsApp1/diku-images/class{idx:02d}"
            for imgname in glob.glob(  f"{dir_name}/*.jpg"  ):
                tmp_images.append(   cv2.imread(  imgname  , cv2.IMREAD_COLOR)    )
                labels.append( idx )

    max_match_txt, result_conf = "xx", 9999
    #print_str = ""
    for template,label in zip(tmp_images,labels):
        # 使用模板匹配方法，这里使用TM_CCOEFF_NORMED（归一化相关系数匹配）
        #result = cv2.matchTemplate(big_image, template, cv2.TM_CCOEFF_NORMED)
        result = cv2.matchTemplate(big_image, template, cv2.TM_SQDIFF_NORMED)

        # 找到匹配结果中的最大值及其位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        #if min_val<0.05 or idx==27:
            #print_str+=f"{fen_dict[label]} {min_val:.4f}  "
        if min_val < result_conf:
            max_match_txt,result_conf = fen_dict[label], min_val
    #print_str= f" {max_match_txt} {result_conf:.4f}  {idx}---- "+print_str
    #print(print_str)
    return max_match_txt







    





