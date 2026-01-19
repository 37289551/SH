# 频道名称映射表
# 用于统一处理不同来源的频道名称变体

# 央视名称映射表：键为各种可能的变体，值为标准化名称
CCTV_NAME_MAPPING = {
    # CCTV-1 综合
    'CCTV1': 'CCTV-1 综合',
    'CCTV-1': 'CCTV-1 综合',
    'CCTV-1 综合': 'CCTV-1 综合',
    '央视一套': 'CCTV-1 综合',
    'cctv1': 'CCTV-1 综合',
    'cctv-1': 'CCTV-1 综合',
    'cctv-1 综合': 'CCTV-1 综合',
    '中央电视台综合频道': 'CCTV-1 综合',
    '综合频道': 'CCTV-1 综合',
    
    # CCTV-2 财经
    'CCTV2': 'CCTV-2 财经',
    'CCTV-2': 'CCTV-2 财经',
    'CCTV-2 财经': 'CCTV-2 财经',
    '央视二套': 'CCTV-2 财经',
    'cctv2': 'CCTV-2 财经',
    'cctv-2': 'CCTV-2 财经',
    'cctv-2 财经': 'CCTV-2 财经',
    '中央电视台财经频道': 'CCTV-2 财经',
    '财经频道': 'CCTV-2 财经',
    
    # CCTV-3 综艺
    'CCTV3': 'CCTV-3 综艺',
    'CCTV-3': 'CCTV-3 综艺',
    'CCTV-3 综艺': 'CCTV-3 综艺',
    '央视三套': 'CCTV-3 综艺',
    'cctv3': 'CCTV-3 综艺',
    'cctv-3': 'CCTV-3 综艺',
    'cctv-3 综艺': 'CCTV-3 综艺',
    '中央电视台综艺频道': 'CCTV-3 综艺',
    '综艺频道': 'CCTV-3 综艺',
    
    # CCTV-4 中文国际
    'CCTV4': 'CCTV-4 中文国际',
    'CCTV-4': 'CCTV-4 中文国际',
    'CCTV-4 中文国际': 'CCTV-4 中文国际',
    '央视四套': 'CCTV-4 中文国际',
    'cctv4': 'CCTV-4 中文国际',
    'cctv-4': 'CCTV-4 中文国际',
    'cctv-4 中文国际': 'CCTV-4 中文国际',
    '中央电视台中文国际频道': 'CCTV-4 中文国际',
    '中文国际频道': 'CCTV-4 中文国际',
    '国际频道': 'CCTV-4 中文国际',
    
    # CCTV-5 体育
    'CCTV5': 'CCTV-5 体育',
    'CCTV-5': 'CCTV-5 体育',
    'CCTV-5 体育': 'CCTV-5 体育',
    '央视五套': 'CCTV-5 体育',
    'cctv5': 'CCTV-5 体育',
    'cctv-5': 'CCTV-5 体育',
    'cctv-5 体育': 'CCTV-5 体育',
    '中央电视台体育频道': 'CCTV-5 体育',
    '体育频道': 'CCTV-5 体育',
    
    # CCTV-5+ 体育赛事
    'CCTV5+': 'CCTV-5+ 体育赛事',
    'CCTV-5+': 'CCTV-5+ 体育赛事',
    'CCTV-5+ 体育赛事': 'CCTV-5+ 体育赛事',
    '央视五套+': 'CCTV-5+ 体育赛事',
    'cctv5+': 'CCTV-5+ 体育赛事',
    'cctv-5+': 'CCTV-5+ 体育赛事',
    '体育赛事频道': 'CCTV-5+ 体育赛事',
    
    # CCTV-6 电影
    'CCTV6': 'CCTV-6 电影',
    'CCTV-6': 'CCTV-6 电影',
    'CCTV-6 电影': 'CCTV-6 电影',
    '央视六套': 'CCTV-6 电影',
    'cctv6': 'CCTV-6 电影',
    'cctv-6': 'CCTV-6 电影',
    'cctv-6 电影': 'CCTV-6 电影',
    '中央电视台电影频道': 'CCTV-6 电影',
    '电影频道': 'CCTV-6 电影',
    
    # CCTV-7 国防军事
    'CCTV7': 'CCTV-7 国防军事',
    'CCTV-7': 'CCTV-7 国防军事',
    'CCTV-7 国防军事': 'CCTV-7 国防军事',
    '央视七套': 'CCTV-7 国防军事',
    'cctv7': 'CCTV-7 国防军事',
    'cctv-7': 'CCTV-7 国防军事',
    'cctv-7 国防军事': 'CCTV-7 国防军事',
    '中央电视台国防军事频道': 'CCTV-7 国防军事',
    '国防军事频道': 'CCTV-7 国防军事',
    
    # CCTV-8 电视剧
    'CCTV8': 'CCTV-8 电视剧',
    'CCTV-8': 'CCTV-8 电视剧',
    'CCTV-8 电视剧': 'CCTV-8 电视剧',
    '央视八套': 'CCTV-8 电视剧',
    'cctv8': 'CCTV-8 电视剧',
    'cctv-8': 'CCTV-8 电视剧',
    'cctv-8 电视剧': 'CCTV-8 电视剧',
    '中央电视台电视剧频道': 'CCTV-8 电视剧',
    '电视剧频道': 'CCTV-8 电视剧',
    
    # CCTV-9 纪录
    'CCTV9': 'CCTV-9 纪录',
    'CCTV-9': 'CCTV-9 纪录',
    'CCTV-9 纪录': 'CCTV-9 纪录',
    '央视九套': 'CCTV-9 纪录',
    'cctv9': 'CCTV-9 纪录',
    'cctv-9': 'CCTV-9 纪录',
    'cctv-9 纪录': 'CCTV-9 纪录',
    '中央电视台纪录频道': 'CCTV-9 纪录',
    '纪录频道': 'CCTV-9 纪录',
    
    # CCTV-10 科教
    'CCTV10': 'CCTV-10 科教',
    'CCTV-10': 'CCTV-10 科教',
    'CCTV-10 科教': 'CCTV-10 科教',
    '央视十套': 'CCTV-10 科教',
    'cctv10': 'CCTV-10 科教',
    'cctv-10': 'CCTV-10 科教',
    'cctv-10 科教': 'CCTV-10 科教',
    '中央电视台科教频道': 'CCTV-10 科教',
    '科教频道': 'CCTV-10 科教',
    
    # CCTV-11 戏曲
    'CCTV11': 'CCTV-11 戏曲',
    'CCTV-11': 'CCTV-11 戏曲',
    'CCTV-11 戏曲': 'CCTV-11 戏曲',
    '央视十一套': 'CCTV-11 戏曲',
    'cctv11': 'CCTV-11 戏曲',
    'cctv-11': 'CCTV-11 戏曲',
    'cctv-11 戏曲': 'CCTV-11 戏曲',
    '中央电视台戏曲频道': 'CCTV-11 戏曲',
    '戏曲频道': 'CCTV-11 戏曲',
    
    # CCTV-12 社会与法
    'CCTV12': 'CCTV-12 社会与法',
    'CCTV-12': 'CCTV-12 社会与法',
    'CCTV-12 社会与法': 'CCTV-12 社会与法',
    '央视十二套': 'CCTV-12 社会与法',
    'cctv12': 'CCTV-12 社会与法',
    'cctv-12': 'CCTV-12 社会与法',
    'cctv-12 社会与法': 'CCTV-12 社会与法',
    '中央电视台社会与法频道': 'CCTV-12 社会与法',
    '社会与法频道': 'CCTV-12 社会与法',
    
    # CCTV-13 新闻
    'CCTV13': 'CCTV-13 新闻',
    'CCTV-13': 'CCTV-13 新闻',
    'CCTV-13 新闻': 'CCTV-13 新闻',
    '央视十三套': 'CCTV-13 新闻',
    'cctv13': 'CCTV-13 新闻',
    'cctv-13': 'CCTV-13 新闻',
    'cctv-13 新闻': 'CCTV-13 新闻',
    '中央电视台新闻频道': 'CCTV-13 新闻',
    '新闻频道': 'CCTV-13 新闻',
    
    # CCTV-14 少儿
    'CCTV14': 'CCTV-14 少儿',
    'CCTV-14': 'CCTV-14 少儿',
    'CCTV-14 少儿': 'CCTV-14 少儿',
    '央视十四套': 'CCTV-14 少儿',
    'cctv14': 'CCTV-14 少儿',
    'cctv-14': 'CCTV-14 少儿',
    'cctv-14 少儿': 'CCTV-14 少儿',
    '中央电视台少儿频道': 'CCTV-14 少儿',
    '少儿频道': 'CCTV-14 少儿',
    
    # CCTV-15 音乐
    'CCTV15': 'CCTV-15 音乐',
    'CCTV-15': 'CCTV-15 音乐',
    'CCTV-15 音乐': 'CCTV-15 音乐',
    '央视十五套': 'CCTV-15 音乐',
    'cctv15': 'CCTV-15 音乐',
    'cctv-15': 'CCTV-15 音乐',
    'cctv-15 音乐': 'CCTV-15 音乐',
    '中央电视台音乐频道': 'CCTV-15 音乐',
    '音乐频道': 'CCTV-15 音乐',
    
    # CCTV-16 奥林匹克
    'CCTV16': 'CCTV-16 奥林匹克',
    'CCTV-16': 'CCTV-16 奥林匹克',
    'CCTV-16 奥林匹克': 'CCTV-16 奥林匹克',
    '央视十六套': 'CCTV-16 奥林匹克',
    'cctv16': 'CCTV-16 奥林匹克',
    'cctv-16': 'CCTV-16 奥林匹克',
    'cctv-16 奥林匹克': 'CCTV-16 奥林匹克',
    '中央电视台奥林匹克频道': 'CCTV-16 奥林匹克',
    '奥林匹克频道': 'CCTV-16 奥林匹克',
    
    # CCTV-17 农业农村
    'CCTV17': 'CCTV-17 农业农村',
    'CCTV-17': 'CCTV-17 农业农村',
    'CCTV-17 农业农村': 'CCTV-17 农业农村',
    '央视十七套': 'CCTV-17 农业农村',
    'cctv17': 'CCTV-17 农业农村',
    'cctv-17': 'CCTV-17 农业农村',
    'cctv-17 农业农村': 'CCTV-17 农业农村',
    '中央电视台农业农村频道': 'CCTV-17 农业农村',
    '农业农村频道': 'CCTV-17 农业农村',
}

# 卫视频道名称映射表
SATELLITE_NAME_MAPPING = {
    # 北京卫视
    '北京卫视': '北京卫视',
    'BTV': '北京卫视',
    'BTV-1': '北京卫视',
    '北京电视台': '北京卫视',
    
    # 东方卫视
    '东方卫视': '东方卫视',
    'DragonTV': '东方卫视',
    'SMG': '东方卫视',
    '上海东方卫视': '东方卫视',
    
    # 湖南卫视
    '湖南卫视': '湖南卫视',
    'HunanTV': '湖南卫视',
    '湖南电视台': '湖南卫视',
    
    # 江苏卫视
    '江苏卫视': '江苏卫视',
    'JiangsuTV': '江苏卫视',
    'JSTV': '江苏卫视',
    
    # 浙江卫视
    '浙江卫视': '浙江卫视',
    'ZhejiangTV': '浙江卫视',
    'ZJTV': '浙江卫视',
    
    # 广东卫视
    '广东卫视': '广东卫视',
    'GuangdongTV': '广东卫视',
    'GDTV': '广东卫视',
    
    # 山东卫视
    '山东卫视': '山东卫视',
    'ShandongTV': '山东卫视',
    'SDTV': '山东卫视',
    
    # 安徽卫视
    '安徽卫视': '安徽卫视',
    'AnhuiTV': '安徽卫视',
    'AHTV': '安徽卫视',
    
    # 河南卫视
    '河南卫视': '河南卫视',
    'HenanTV': '河南卫视',
    'HNTV': '河南卫视',
    
    # 湖北卫视
    '湖北卫视': '湖北卫视',
    'HubeiTV': '湖北卫视',
    'HBTV': '湖北卫视',
}

# 合并所有映射表
CHANNEL_NAME_MAPPING = {}
CHANNEL_NAME_MAPPING.update(CCTV_NAME_MAPPING)
CHANNEL_NAME_MAPPING.update(SATELLITE_NAME_MAPPING)

def get_standard_channel_name(channel_name):
    """
    获取标准化的频道名称
    
    Args:
        channel_name (str): 原始频道名称
        
    Returns:
        str: 标准化的频道名称，如果没有匹配到则返回原始名称
    """
    if not channel_name:
        return channel_name
    
    # 去除首尾空格，转换为小写进行匹配
    normalized = channel_name.strip().lower()
    
    # 先尝试直接匹配
    if channel_name in CHANNEL_NAME_MAPPING:
        return CHANNEL_NAME_MAPPING[channel_name]
    
    # 尝试小写匹配
    for key, value in CHANNEL_NAME_MAPPING.items():
        if key.lower() == normalized:
            return value
    
    # 尝试部分匹配（针对带地区或其他后缀的情况）
    for key, value in CHANNEL_NAME_MAPPING.items():
        if normalized in key.lower() or key.lower() in normalized:
            return value
    
    # 如果都没有匹配到，返回原始名称
    return channel_name

def normalize_channel_name(channel_name):
    """
    标准化频道名称的别名函数，与get_standard_channel_name功能相同
    """
    return get_standard_channel_name(channel_name)

# 使用示例
if __name__ == "__main__":
    # 测试央视名称映射
    test_cctv_names = ['CCTV1', 'CCTV-1', 'cctv-1 综合', '央视一套', 'cctv1']
    print("央视名称映射测试：")
    for name in test_cctv_names:
        standard_name = get_standard_channel_name(name)
        print(f"  {name} -> {standard_name}")
    
    # 测试卫视频道映射
    test_satellite_names = ['北京卫视', 'BTV', '东方卫视', 'DragonTV', '湖南卫视']
    print("\n卫视频道映射测试：")
    for name in test_satellite_names:
        standard_name = get_standard_channel_name(name)
        print(f"  {name} -> {standard_name}")
    
    # 测试未匹配的情况
    test_unknown_names = ['未知频道', '测试频道']
    print("\n未匹配名称测试：")
    for name in test_unknown_names:
        standard_name = get_standard_channel_name(name)
        print(f"  {name} -> {standard_name}")
